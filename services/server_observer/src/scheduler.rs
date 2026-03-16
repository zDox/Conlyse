use crate::observation_session::ObservationSession;
use std::collections::{BTreeMap, HashSet, VecDeque};
use std::sync::atomic::{AtomicBool, AtomicI32, Ordering};
use std::sync::Mutex;
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use tokio::time::sleep;

pub struct Scheduler {
    max_parallel_updates: AtomicI32,
    max_parallel_first_updates: AtomicI32,
    update_interval: Mutex<Duration>,
    update_queue: Mutex<BTreeMap<SystemTime, VecDeque<i32>>>,
    pending_priority_sessions: Mutex<VecDeque<(i32, i32)>>,
    pending_normal_sessions: Mutex<VecDeque<(i32, i32)>>,
    queued_priority: Mutex<HashSet<i32>>,
    queued_normal: Mutex<HashSet<i32>>,
    first_update_sessions: Mutex<HashSet<i32>>,
    running_first_updates: Mutex<HashSet<i32>>,
    active_coroutines: AtomicI32,
    stop_flag: AtomicBool,
}

impl Scheduler {
    pub fn new(
        max_parallel_updates: i32,
        max_parallel_first_updates: i32,
        update_interval: f64,
    ) -> Self {
        Self {
            max_parallel_updates: AtomicI32::new(max_parallel_updates.max(1)),
            max_parallel_first_updates: AtomicI32::new(max_parallel_first_updates.max(1)),
            update_interval: Mutex::new(Duration::from_secs_f64(update_interval.max(0.1))),
            update_queue: Mutex::new(BTreeMap::new()),
            pending_priority_sessions: Mutex::new(VecDeque::new()),
            pending_normal_sessions: Mutex::new(VecDeque::new()),
            queued_priority: Mutex::new(HashSet::new()),
            queued_normal: Mutex::new(HashSet::new()),
            first_update_sessions: Mutex::new(HashSet::new()),
            running_first_updates: Mutex::new(HashSet::new()),
            active_coroutines: AtomicI32::new(0),
            stop_flag: AtomicBool::new(false),
        }
    }

    pub fn stop(&self) {
        self.stop_flag.store(true, Ordering::SeqCst);
    }

    pub fn schedule_update(&self, session: &ObservationSession) {
        let mut queue = self.update_queue.lock().expect("scheduler queue mutex poisoned");
        queue
            .entry(session.next_update_at)
            .or_default()
            .push_back(session.game_id);
    }

    pub fn schedule_immediate_update(&self, session: &mut ObservationSession) {
        session.next_update_at = SystemTime::now();
        self.schedule_update(session);
    }

    pub fn schedule_next_update(&self, session: &mut ObservationSession, missed_update: bool) {
        let interval_ms = self.update_interval_ms();
        let offset_ms = self.calculate_offset_ms(session.game_id);
        let now = current_time_ms();

        if missed_update {
            session.update_sequence_number = self.calculate_next_k(now, offset_ms);
        } else {
            session.update_sequence_number += 1;
        }

        let due_ms = session.update_sequence_number * interval_ms + offset_ms;
        session.next_update_at = time_from_millis(due_ms);
        self.schedule_update(session);
    }

    pub fn initialize_session_schedule(&self, session: &mut ObservationSession) {
        let interval_ms = self.update_interval_ms();
        let offset_ms = self.calculate_offset_ms(session.game_id);
        let now_ms = current_time_ms();
        session.update_sequence_number = self.calculate_next_k(now_ms, offset_ms);
        let due_ms = session.update_sequence_number * interval_ms + offset_ms;
        session.next_update_at = time_from_millis(due_ms);
    }

    pub fn mark_first_update(&self, game_id: i32) {
        self.first_update_sessions
            .lock()
            .expect("scheduler first-update mutex poisoned")
            .insert(game_id);
    }

    pub fn cleanup_first_update_tracking(&self, game_id: i32) {
        self.first_update_sessions
            .lock()
            .expect("scheduler first-update mutex poisoned")
            .remove(&game_id);
        self.running_first_updates
            .lock()
            .expect("scheduler running-first-update mutex poisoned")
            .remove(&game_id);
    }

    pub fn queue_new_session(&self, game_id: i32, scenario_id: i32, is_priority: bool) {
        if is_priority {
            // If already queued priority, nothing to do.
            if self
                .queued_priority
                .lock()
                .expect("scheduler queued-priority mutex poisoned")
                .contains(&game_id)
            {
                return;
            }

            // If it was queued as normal, promote: remove from normal queue + sets.
            {
                let mut queued_normal = self
                    .queued_normal
                    .lock()
                    .expect("scheduler queued-normal mutex poisoned");
                if queued_normal.remove(&game_id) {
                    let mut normal_q = self
                        .pending_normal_sessions
                        .lock()
                        .expect("scheduler pending-normal mutex poisoned");
                    let mut new_q = VecDeque::with_capacity(normal_q.len());
                    while let Some(item) = normal_q.pop_front() {
                        if item.0 != game_id {
                            new_q.push_back(item);
                        }
                    }
                    *normal_q = new_q;
                }
            }

            self.pending_priority_sessions
                .lock()
                .expect("scheduler pending-priority mutex poisoned")
                .push_back((game_id, scenario_id));
            self.queued_priority
                .lock()
                .expect("scheduler queued-priority mutex poisoned")
                .insert(game_id);
        } else {
            // Don't queue if already queued (either queue).
            if self
                .queued_priority
                .lock()
                .expect("scheduler queued-priority mutex poisoned")
                .contains(&game_id)
            {
                return;
            }
            if self
                .queued_normal
                .lock()
                .expect("scheduler queued-normal mutex poisoned")
                .contains(&game_id)
            {
                return;
            }

            self.pending_normal_sessions
                .lock()
                .expect("scheduler pending-normal mutex poisoned")
                .push_back((game_id, scenario_id));
            self.queued_normal
                .lock()
                .expect("scheduler queued-normal mutex poisoned")
                .insert(game_id);
        }
    }

    pub fn get_pending_new_sessions_with_limits(
        &self,
        max_total: usize,
        max_normal: usize,
    ) -> Vec<(i32, i32, bool)> {
        if max_total == 0 {
            return Vec::new();
        }

        let mut out = Vec::new();
        out.reserve(max_total);

        {
            let mut q = self
                .pending_priority_sessions
                .lock()
                .expect("scheduler pending-priority mutex poisoned");
            while out.len() < max_total {
                let Some((game_id, scenario_id)) = q.pop_front() else {
                    break;
                };
                self.queued_priority
                    .lock()
                    .expect("scheduler queued-priority mutex poisoned")
                    .remove(&game_id);
                out.push((game_id, scenario_id, true));
            }
        }

        if out.len() >= max_total || max_normal == 0 {
            return out;
        }

        let mut normals_started = 0usize;
        let mut q = self
            .pending_normal_sessions
            .lock()
            .expect("scheduler pending-normal mutex poisoned");
        while out.len() < max_total && normals_started < max_normal {
            let Some((game_id, scenario_id)) = q.pop_front() else {
                break;
            };
            self.queued_normal
                .lock()
                .expect("scheduler queued-normal mutex poisoned")
                .remove(&game_id);
            out.push((game_id, scenario_id, false));
            normals_started += 1;
        }

        out
    }

    pub fn get_due_updates(&self) -> Vec<i32> {
        let now = SystemTime::now();
        let max_parallel = self.max_parallel_updates.load(Ordering::SeqCst);
        let mut ready = Vec::new();
        let mut queue = self.update_queue.lock().expect("scheduler queue mutex poisoned");

        loop {
            let in_flight = self.active_coroutines.load(Ordering::SeqCst) + ready.len() as i32;
            if in_flight >= max_parallel {
                break;
            }

            let Some((&next_due, _)) = queue.iter().next() else {
                break;
            };
            if next_due > now {
                break;
            }

            let game_id = pop_earliest(&mut queue).expect("earliest queue entry must exist");
            if !self.can_start_update(game_id) {
                queue.entry(next_due).or_default().push_back(game_id);
                break;
            }

            if self
                .first_update_sessions
                .lock()
                .expect("scheduler first-update mutex poisoned")
                .contains(&game_id)
            {
                self.running_first_updates
                    .lock()
                    .expect("scheduler running-first-update mutex poisoned")
                    .insert(game_id);
            }

            ready.push(game_id);
        }

        ready
    }

    pub async fn process_due_updates(&self) {
        if self.stop_flag.load(Ordering::SeqCst) {
            return;
        }

        let queue_state = {
            let queue = self.update_queue.lock().expect("scheduler queue mutex poisoned");
            queue.iter().next().map(|(k, _)| *k)
        };

        if queue_state.is_none() {
            sleep(Duration::from_millis(100)).await;
            return;
        }

        if self.active_coroutines.load(Ordering::SeqCst)
            >= self.max_parallel_updates.load(Ordering::SeqCst)
        {
            sleep(Duration::from_millis(100)).await;
            return;
        }

        let next_due = queue_state.expect("checked Some above");
        let now = SystemTime::now();
        if next_due > now {
            let wait = next_due.duration_since(now).unwrap_or(Duration::from_millis(0));
            let cap = *self
                .update_interval
                .lock()
                .expect("scheduler interval mutex poisoned");
            let actual_wait = wait.min(cap);
            if actual_wait > Duration::from_millis(0) {
                sleep(actual_wait).await;
            }
        }
    }

    pub fn increment_active_coroutines(&self) {
        self.active_coroutines.fetch_add(1, Ordering::SeqCst);
    }

    pub fn decrement_active_coroutines(&self) {
        self.active_coroutines.fetch_sub(1, Ordering::SeqCst);
    }

    pub fn set_update_interval(&self, interval_seconds: f64) {
        if interval_seconds > 0.0 {
            *self
                .update_interval
                .lock()
                .expect("scheduler interval mutex poisoned") =
                Duration::from_secs_f64(interval_seconds);
        }
    }

    pub fn set_max_parallel_updates(&self, max_updates: i32) {
        if max_updates >= 1 {
            self.max_parallel_updates
                .store(max_updates, Ordering::SeqCst);
        }
    }

    pub fn set_max_parallel_first_updates(&self, max_first_updates: i32) {
        if max_first_updates >= 1 {
            self.max_parallel_first_updates
                .store(max_first_updates, Ordering::SeqCst);
        }
    }

    fn update_interval_ms(&self) -> i64 {
        self.update_interval
            .lock()
            .expect("scheduler interval mutex poisoned")
            .as_millis()
            .max(1) as i64
    }

    fn calculate_offset_ms(&self, game_id: i32) -> i64 {
        game_id as i64 % self.update_interval_ms()
    }

    fn calculate_next_k(&self, current_time_ms: i64, offset_ms: i64) -> i64 {
        let interval = self.update_interval_ms();
        if interval <= 0 {
            return 1;
        }
        if current_time_ms < offset_ms {
            return 0;
        }
        (current_time_ms - offset_ms) / interval + 1
    }

    fn can_start_update(&self, game_id: i32) -> bool {
        let first = self
            .first_update_sessions
            .lock()
            .expect("scheduler first-update mutex poisoned");
        if !first.contains(&game_id) {
            return true;
        }
        drop(first);

        let running = self
            .running_first_updates
            .lock()
            .expect("scheduler running-first-update mutex poisoned");
        let max_first = self.max_parallel_first_updates.load(Ordering::SeqCst);
        (running.len() as i32) < max_first
    }
}

fn pop_earliest(queue: &mut BTreeMap<SystemTime, VecDeque<i32>>) -> Option<i32> {
    let key = *queue.keys().next()?;
    let ids = queue.get_mut(&key)?;
    let id = ids.pop_front();
    if ids.is_empty() {
        queue.remove(&key);
    }
    id
}

fn current_time_ms() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as i64)
        .unwrap_or_default()
}

fn time_from_millis(ms: i64) -> SystemTime {
    if ms <= 0 {
        return UNIX_EPOCH;
    }
    UNIX_EPOCH + Duration::from_millis(ms as u64)
}
