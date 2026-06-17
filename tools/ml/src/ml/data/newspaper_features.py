"""
Per-player newspaper feature vector derived from in-game military event articles.

Articles are filtered to a 1-day sliding window per snapshot (STEP_DAYS=1), so
each snapshot's features reflect only that day's reported events. The temporal
Transformer aggregates the sequence across T_STEPS snapshots.

Feature layout (NUM_NEWSPAPER_FEATURES = NUM_UNIT_TYPES + 7):
  [0 .. NUM_UNIT_TYPES-1] — per-unit-type loss counts (log1p), keyed by UNIT_VOCAB
  [NUM_UNIT_TYPES + 0]    — buildings_damaged count (log1p)
  [NUM_UNIT_TYPES + 1]    — veterans_recruited count (log1p)
  [NUM_UNIT_TYPES + 2]    — nuclear_strikes_launched count (log1p)
  [NUM_UNIT_TYPES + 3]    — nuclear_strikes_received count (log1p)
  [NUM_UNIT_TYPES + 4]    — insurgent_attacks count (log1p)
  [NUM_UNIT_TYPES + 5]    — dissent_events count (log1p)
  [NUM_UNIT_TYPES + 6]    — military_articles_total catch-all (log1p)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

import numpy as np
from conflict_interface.data_types.newest.newspaper_state.statistics_article import StatisticsArticle

_UNIT_VOCAB_PATH = Path(__file__).parent / "unit_vocab.json"
UNIT_VOCAB: list[str] = json.loads(_UNIT_VOCAB_PATH.read_text(encoding="utf-8"))
UNIT_VOCAB_INDEX: dict[str, int] = {name: i for i, name in enumerate(UNIT_VOCAB)}
NUM_UNIT_TYPES = len(UNIT_VOCAB)

NUM_NEWSPAPER_FEATURES = NUM_UNIT_TYPES + 7

# Scalar feature offsets (relative to NUM_UNIT_TYPES)
_OFF_BUILDINGS_DAMAGED = 0
_OFF_VETERANS_RECRUITED = 1
_OFF_NUCLEAR_LAUNCHED = 2
_OFF_NUCLEAR_RECEIVED = 3
_OFF_INSURGENT_ATTACKS = 4
_OFF_DISSENT_EVENTS = 5
_OFF_MILITARY_TOTAL = 6

FEATURE_NAMES: list[str] = UNIT_VOCAB + [
    "buildings_damaged",
    "veterans_recruited",
    "nuclear_strikes_launched",
    "nuclear_strikes_received",
    "insurgent_attacks",
    "dissent_events",
    "military_articles_total",
]

# --- regexes ------------------------------------------------------------------

_SEGMENT_RE = re.compile(r"<p>(.*?)</p>", re.DOTALL)
_UNIT_LOSS_RE = re.compile(r"lost:?\s+(\d+)\s+([A-Za-z][\w ]*?)(?=\s+over\s|</p>|$)")
_BUILDING_DAMAGE_RE = re.compile(r"Building damaged in .*?:\s*([\w ]+?)\.")
_VETERAN_TITLE_RE = re.compile(r"recruits new .+ Veteran\.$")
_NUCLEAR_ATTACK_TITLE_PREFIXES = (r"^Nuclear ICBM attack on ",)
_INSURGENT_AUTHOR = "BREAKING NEWS: Violent Insurgency"
_DISSENT_AUTHOR = "Crimes against Humanity"


# --- event type ---------------------------------------------------------------

@dataclass
class NewspaperEvent:
    feature_idx: int
    player_id: int
    weight: float = 1.0


# --- body helpers -------------------------------------------------------------

def _iter_body_segments(message_body: str) -> list[str]:
    segments = _SEGMENT_RE.findall(message_body)
    return segments if segments else [message_body]


# --- classifiers --------------------------------------------------------------

def _classify_casualty_shape(article) -> list[NewspaperEvent]:
    """Casualty/damage articles: receiver_id==-1, author=='', body contains 'lost' or 'damaged'."""
    if article.receiver_id != -1 or article.author != "":
        return []
    body = article.message_body or ""
    if "lost" not in body and "damaged" not in body:
        return []

    events: list[NewspaperEvent] = []
    fired = False

    for segment in _iter_body_segments(body):
        for m in _UNIT_LOSS_RE.finditer(segment):
            count = int(m.group(1))
            unit_name = m.group(2).strip()
            idx = UNIT_VOCAB_INDEX.get(unit_name)
            if idx is not None:
                events.append(NewspaperEvent(feature_idx=idx, player_id=article.sender_id, weight=count))
            fired = True

        if _BUILDING_DAMAGE_RE.search(segment):
            events.append(NewspaperEvent(
                feature_idx=NUM_UNIT_TYPES + _OFF_BUILDINGS_DAMAGED,
                player_id=article.sender_id,
            ))
            fired = True

    if fired:
        events.append(NewspaperEvent(
            feature_idx=NUM_UNIT_TYPES + _OFF_MILITARY_TOTAL,
            player_id=article.sender_id,
        ))
    return events


def _classify_veteran_recruitment(article) -> list[NewspaperEvent]:
    if article.receiver_id != -1 or article.author != "":
        return []
    if not _VETERAN_TITLE_RE.search(article.title or ""):
        return []
    return [
        NewspaperEvent(feature_idx=NUM_UNIT_TYPES + _OFF_VETERANS_RECRUITED, player_id=article.sender_id),
        NewspaperEvent(feature_idx=NUM_UNIT_TYPES + _OFF_MILITARY_TOTAL, player_id=article.sender_id),
    ]


def _classify_nuclear_attack(article) -> list[NewspaperEvent]:
    title = article.title or ""
    if not any(re.search(p, title) for p in _NUCLEAR_ATTACK_TITLE_PREFIXES):
        return []
    events = [
        NewspaperEvent(feature_idx=NUM_UNIT_TYPES + _OFF_NUCLEAR_LAUNCHED, player_id=article.sender_id),
        NewspaperEvent(feature_idx=NUM_UNIT_TYPES + _OFF_MILITARY_TOTAL, player_id=article.sender_id),
    ]
    if article.receiver_id != -1:
        events.append(NewspaperEvent(
            feature_idx=NUM_UNIT_TYPES + _OFF_NUCLEAR_RECEIVED,
            player_id=article.receiver_id,
        ))
    return events


def _classify_insurgent_attack(article) -> list[NewspaperEvent]:
    if article.author != _INSURGENT_AUTHOR:
        return []
    return [
        NewspaperEvent(feature_idx=NUM_UNIT_TYPES + _OFF_INSURGENT_ATTACKS, player_id=article.sender_id),
        NewspaperEvent(feature_idx=NUM_UNIT_TYPES + _OFF_MILITARY_TOTAL, player_id=article.sender_id),
    ]


def _classify_dissent(article) -> list[NewspaperEvent]:
    if article.author != _DISSENT_AUTHOR:
        return []
    return [
        NewspaperEvent(feature_idx=NUM_UNIT_TYPES + _OFF_DISSENT_EVENTS, player_id=article.sender_id),
        NewspaperEvent(feature_idx=NUM_UNIT_TYPES + _OFF_MILITARY_TOTAL, player_id=article.sender_id),
    ]


_CLASSIFIERS = (
    _classify_casualty_shape,
    _classify_veteran_recruitment,
    _classify_nuclear_attack,
    _classify_insurgent_attack,
    _classify_dissent,
)


def classify_article(article) -> list[NewspaperEvent]:
    """Returns events for one article; returns [] for StatisticsArticle."""
    if isinstance(article, StatisticsArticle):
        return []
    events: list[NewspaperEvent] = []
    for classifier in _CLASSIFIERS:
        events.extend(classifier(article))
    return events


# --- windowing ----------------------------------------------------------------

def filter_articles_in_window(articles, start_time: datetime, window_start_day: float, window_end_day: float) -> list:
    """Return articles whose timestamp falls in (window_start_day, window_end_day]."""
    result = []
    for article in articles:
        article_day = (
            datetime.fromtimestamp(article.time_stamp / 1000, tz=timezone.utc) - start_time
        ).total_seconds() / 86400.0
        if window_start_day < article_day <= window_end_day:
            result.append(article)
    return result


# --- aggregation --------------------------------------------------------------

def compute_newspaper_features(
    articles_in_window: list,
    seat_idx: dict[int, int],
    num_players: int,
) -> np.ndarray:
    """Return float32 array of shape (num_players, NUM_NEWSPAPER_FEATURES), log1p-scaled."""
    raw = np.zeros((num_players, NUM_NEWSPAPER_FEATURES), dtype=np.float32)
    for article in articles_in_window:
        for event in classify_article(article):
            seat = seat_idx.get(event.player_id)
            if seat is None:
                continue  # AI / pseudo-country (e.g. "Insurgencies" id=115) — not a real player
            raw[seat - 1, event.feature_idx] += event.weight
    return np.log1p(raw)
