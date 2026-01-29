# Game Statistics Metrics for Conflict of Nations

This document provides a comprehensive list of metrics to analyze 1000+ recorded Conflict of Nations games.

**Goal:** later display *only* the data shown in **Step 2: Cross-Game Aggregate Analysis**.
To do that efficiently and consistently, **Step 1 is defined as the exact per-game primitives you must compute and persist** so that every Step 2 panel can be derived without re-reading full replays.

These primitives are intentionally mostly **sums / counts / durations / bucketed snapshots** (rather than precomputed averages), because cross-game aggregates can then compute means/medians/rates consistently.

## Table of Contents
- [Step 1: Per-Game Primitives (inputs to Step 2)](#step-1-per-game-primitives-inputs-to-step-2)
  - [1.1 Game Meta (identity + normalization)](#11-game-meta-identity--normalization)
  - [1.2 Game Event Totals (counts/sums)](#12-game-event-totals-countssums)
  - [1.3 Game Time Buckets (per game day + per completion %)](#13-game-time-buckets-per-game-day--per-completion-)
  - [1.4 Per Country Per Game (primitives)](#14-per-country-per-game-primitives)
  - [1.5 Per Province Per Game (primitives)](#15-per-province-per-game-primitives)
- [Step 2: Cross-Game Aggregate Analysis (displayed)](#step-2-cross-game-aggregate-analysis-displayed)
  - [2.1 Global Aggregates (all games)](#21-global-aggregates-all-games)
  - [2.2 Per Country Aggregates (across games)](#22-per-country-aggregates-across-games)
  - [2.3 Per Province Aggregates (across games)](#23-per-province-aggregates-across-games)
  - [2.4 Per Game Day Aggregates (across games)](#24-per-game-day-aggregates-across-games)
  - [2.5 Per Completion % Aggregates (across games)](#25-per-completion--aggregates-across-games)
- [Glossary](#glossary)

---

## Step 1: Per-Game Primitives (inputs to Step 2)

### 1.1 Game Meta (identity + normalization)

Required to join data across games and compare apples-to-apples.

- **game_id**
- **scenario_id / map_id** (important normalization key)
- **server/region** (optional, if available)

#### Timeline
- **start_timestamp**
- **end_timestamp**
- **duration_seconds**
- **num_updates**
- **average_time_between_updates_seconds** (derived) = `duration_seconds / max(1, num_updates - 1)`

#### Map / scale
- **num_provinces_total**

#### Victory & outcome
- **victory_type** (Solo / Coalition / Unknown)
- **winner_country_ids** (list)
- **winner_player_ids** (list, if available)
- **winning_coalition_id** (nullable)

#### Participation baseline
- **num_players_total**
- **num_human_start**, **num_human_end**
- **num_ai_start**, **num_ai_end**
- **player_dropout_rate** (derived) = `(num_human_start - num_human_end) / max(1, num_human_start)`

---

### 1.2 Game Event Totals (counts/sums)

#### Diplomacy event totals
- **alliances_formed_count**
- **alliances_dissolved_count**
- **wars_declared_count**
- **peace_treaties_count**
- **right_of_way_signed_count**

#### Territory churn totals
- **province_owner_change_events_count** (total ownership-change events; not “unique provinces”)
- **provinces_contested_unique_count** (unique provinces with ≥1 ownership change)
- **provinces_never_captured_count**

#### Economy totals
- **money_generated_sum**
- **resources_produced_sum_by_type** (map: resource_type → sum)

#### Market pricing (optional, only if price samples exist)
- **price_samples_count_by_type**
- **price_sum_by_type**
- **price_sum_sq_by_type**
- **average_resource_price_by_type** (derived) = `price_sum_by_type / max(1, price_samples_count_by_type)`
- **resource_price_volatility_by_type** (derived stddev) = `sqrt(E[x^2] - E[x]^2)`

#### Map control (derived from churn + province ownership data)
- **average_province_ownership_duration_seconds** (derived, rough) = `duration_seconds / max(1, province_owner_change_events_count)`
  - Better: compute per-province ownership durations from `owner_time_sum_seconds_by_country` and aggregate.

---

### 1.3 Game Time Buckets (per game day + per completion %)

Cross-game charts often need aligned x-axes that are *not wall-clock timestamps*.
We support two alignments:

1) **Game Day**: integer day index (0,1,2,...) based on in-game day boundaries.
2) **Completion %**: bins of the game’s progress from 0–100% (time-normalized).

You can compute Step 2 “per day” and “per completion %” without keeping per-tick history by persisting the following buckets.

#### 1.3.1 `GameDay` buckets
Key: `(game_id, game_day_index)`

- **day_start_ts**, **day_end_ts** (optional; useful for debugging)
- Participation:
  - **active_humans_count**
  - **active_players_count**
- Economy totals that day:
  - **money_generated_day_sum**
  - **resources_produced_day_sum_by_type**
- Diplomacy events that day:
  - **alliances_formed_day_count**, **alliances_dissolved_day_count**
  - **wars_declared_day_count**, **peace_treaties_day_count**, **right_of_way_signed_day_count**
- Territory churn that day:
  - **province_owner_change_events_day_count**

#### 1.3.2 `GameCompletionBin` buckets
Key: `(game_id, completion_bin)` where completion_bin is e.g. `0-5, 5-10, ..., 95-100`.

Store the same fields as `GameDay`, but bucketed by completion percentage:
- **bin_start_pct**, **bin_end_pct**
- **bin_start_ts**, **bin_end_ts** (optional)
- Participation, economy totals, diplomacy events, territory churn (same as above)

> Definition note: treat completion % as **time-based** by default: `(t - start_ts) / (end_ts - start_ts)`.

---

### 1.4 Per Country Per Game (primitives)

Key: `(game_id, country_id)`

#### Identification / segmentation
- **country_id**
- **player_id** (nullable)
- **country_name / faction**
- **player_name** (optional)
- **is_ai** (boolean)

#### Outcome primitives
- **final_rank**
- **final_victory_points**
- **was_eliminated** (boolean)
- **elimination_timestamp** (nullable)
- **time_survived_seconds** (derived) = `coalesce(elimination_timestamp, end_timestamp) - start_timestamp`

#### Territory primitives
- **provinces_owned_start**
- **provinces_owned_end**
- **provinces_owned_min**
- **provinces_owned_max**
- **province_captures_count**
- **province_losses_count**
- **province_days_owned_sum** (sum over game days: provinces_owned_on_day; enables averages later)
- **net_province_gain_loss** (derived) = `provinces_owned_end - provinces_owned_start`
- **average_provinces_controlled** (derived) = `province_days_owned_sum / max(1, days_observed)`
- **territory_expansion_rate** (derived, optional) = `province_captures_count / max(1, time_survived_days)`
- **victory_points_per_day** (derived, optional) = `final_victory_points / max(1, time_survived_days)`

#### Economy primitives
- **money_earned_sum**
- **resources_produced_sum_by_type**

#### Development / buildings primitives
- **buildings_constructed_count_by_type**
- **buildings_destroyed_count_by_type**
- **building_damage_events_count_by_type** (if “damage taken” is observable; otherwise omit)
- **infrastructure_investment_cost_sum** (only if costs are reliably derivable)

#### Morale primitives
To compute averages/variance later, store sum+count and extremes.
- **morale_samples_count**
- **morale_sum**
- **morale_min**
- **morale_max**
- **time_below_25_morale_sum_seconds**
- **time_above_75_morale_sum_seconds**
- **time_25_to_75_morale_sum_seconds**
- **average_morale** (derived) = `morale_sum / max(1, morale_samples_count)`
- **morale_volatility** (derived stddev) requires `morale_sum_sq` in addition to `morale_sum` + `morale_samples_count`.

#### Diplomacy primitives
- **alliances_joined_count**
- **alliance_time_sum_seconds**
- **wars_participated_count** (or replace with **war_time_sum_seconds** if available)
- **peace_treaties_signed_count**
- **right_of_way_signed_count**

#### Country time buckets
- `CountryDay(game_id,country_id,day)`:
  - **provinces_owned**
  - **captures_day_count**, **losses_day_count**
  - **money_generated_day_sum**
  - **resources_produced_day_sum_by_type**
  - **morale_samples_day_count**, **morale_sum_day**

- `CountryCompletionBin(game_id,country_id,bin)` with the same fields.
  - **provinces_owned**
  - **captures_day_count**, **losses_day_count**
  - **money_generated_day_sum**
  - **resources_produced_day_sum_by_type**
  - **morale_samples_day_count**, **morale_sum_day**
---

### 1.5 Per Province Per Game (primitives)

Key: `(game_id, province_id)`

#### Static attributes (needed for cross-game province analysis)
- **province_id**
- **province_name**
- **region**
- **terrain_type**
- **is_coastal**
- **resource_production_type**
- **was_capital_ever** (boolean)

#### Ownership history primitives
- **owner_start_country_id**
- **owner_end_country_id**
- **ownership_change_count**
- **owner_time_sum_seconds_by_country** (map: country_id → seconds controlled)
- **was_contested** (derived) = `ownership_change_count > 0`
- **longest_owner / longest_ownership_duration** (derived) = `argmax(owner_time_sum_seconds_by_country)`
- **average_ownership_duration** (derived) = `duration_seconds / max(1, ownership_change_count)` (very rough)
  - Better: requires ownership *segments*; if you store segments, then `owner_time_sum_seconds_by_country / ownership_segments_count`.
- **list_of_all_owners_chronological** (deferred unless ownership-change events or segments are stored)

#### Economy primitives
- **money_produced_sum**
- **resource_produced_sum** (or by type, depending on province model)

#### Development primitives
- **buildings_constructed_count_by_type**
- **construction_time_sum_seconds** (if available)
- **infrastructure_investment_cost_sum** (if available)

#### Morale primitives
- **morale_samples_count**
- **morale_sum**
- **morale_min**
- **morale_max**
- **time_below_25_morale_sum_seconds**
- **time_above_75_morale_sum_seconds**
- **time_25_to_75_morale_sum_seconds**

---

## Step 2: Cross-Game Aggregate Analysis (displayed)

Everything in this section must be computable only from Step 1 primitives.

### 2.1 Global Aggregates (all games)

#### Game characteristics
- **Average / median / distribution of game duration**
- **Duration standard deviation**
- **Average / median number of updates**
- **Distribution of num_provinces_total** (to detect mixed scenarios)

#### Victory analysis
- **Most common victory type**
- **Victory type distribution**
- **Win rates by scenario_id/map_id**

#### Participation patterns
- **Average players per game** (total / humans)
- **Dropout distribution** (human_start → human_end)
- **Average survival time (overall)**
- **Rank / placement distribution**

#### Economy trends
- **Average total resources produced per game (overall and by type)**
- **Average total money generated per game**

#### Diplomacy & conflict trends
*(These were previously only in Step 1; promote them to cross-game outputs.)*
- **Average alliances formed per game**
- **Average alliances dissolved per game**
- **Average wars declared per game**
- **Average peace treaties per game**
- **Average right-of-way agreements per game**

#### Map control / territory churn
*(These were previously only in Step 1; promote them to cross-game outputs.)*
- **Average contested provinces per game**
- **Average province ownership change events per game**
- **Average provinces never captured per game**

---

### 2.2 Per Country Aggregates (across games)

Key: `country_id` (optionally segmented by scenario_id/map_id)

#### Performance
- **Win / loss rate** (and coalition win rate if desired)
- **Average / median final rank**
- **Average / median final victory points**

#### Survival
- **Elimination rate**
- **Average survival time**
- **Early / mid / late survival rate**

#### Territory
- **Average provinces owned (computed from province_days_owned_sum / days_alive)**
- **Average captures and losses**
- **Average max provinces**

#### Economy
- **Average money earned**
- **Average resources produced (overall and by type)**

#### Diplomacy
- **Alliance participation rate**
- **Average alliance time**
- **Average wars participated**
- **Average peace treaties signed**
- **Average right-of-way signed**

#### Development & morale
*(These were previously per-game-only; promote them to cross-game outputs.)*
- **Average buildings constructed by type**
- **Average buildings destroyed by type**
- **Average morale** (computed from morale_sum / morale_samples_count)
- **Morale distribution and time-in-band** (below 25%, 25–75%, above 75%)

---

### 2.3 Per Province Aggregates (across games)

Key: `province_id` (segmented by scenario_id/map_id)

#### Contest frequency
- **Contest frequency rate** (fraction of games where province had ≥1 ownership change)
- **Average ownership change count**

#### Strategic importance
- **Win correlation** (fraction of winning games where winner controls province at end / during key phases)
- **Average time controlled by winner** (from owner_time_sum_seconds_by_country)

#### Ownership patterns
- **Most common owner (end-of-game)**
- **Average time controlled by each country**

#### Economic value
- **Average money produced**
- **Average resources produced**

#### Development & morale
*(These were previously per-game-only; promote them to cross-game outputs.)*
- **Most common buildings constructed by type**
- **Average infrastructure investment** (if costs available)
- **Average morale and morale stability proxies** (use sum/count/min/max + time-in-band)

---

### 2.4 Per Game Day Aggregates (across games)

Key: `game_day_index`

Computed by aggregating `GameDay` buckets across games (optionally segment by scenario_id/map_id).

- Participation: **avg active players on day D**
- Economy: **avg money/resources produced on day D (by type)**
- Diplomacy: **avg wars declared / alliances formed on day D**
- Territory churn: **avg owner change events on day D**

Optional deeper cuts (if `CountryDay` / `ProvinceDay` are stored):
- **avg provinces owned by country on day D**
- **avg captures/losses by country on day D**

---

### 2.5 Per Completion % Aggregates (across games)

Key: `completion_bin` (e.g. 0–5%, 5–10%, …)

Computed by aggregating `GameCompletionBin` buckets across games.

- Participation: **avg active players at completion bin B**
- Economy: **avg money/resources produced at completion bin B**
- Diplomacy: **avg diplomacy events at completion bin B**
- Territory churn: **avg owner change events at completion bin B**

Optional (if `CountryCompletionBin` / `ProvinceCompletionBin` are stored):
- **country performance trajectories vs completion %**
- **province contesting timing vs completion %**

---

## Glossary

- **Peace Treaty**: Switches from war to peace relation and both parties are still alive.
- **Contested province**: A province with at least one ownership change event in a game.
- **Completion %**: `(timestamp - start_ts) / (end_ts - start_ts)`; bucketed for cross-game alignment.
