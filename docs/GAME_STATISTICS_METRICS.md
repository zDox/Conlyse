# Game Statistics Metrics for Conflict of Nations

This document provides a comprehensive list of metrics to analyze 1000+ recorded Conflict of Nations games. The analysis is performed in two steps with multiple aggregation levels.

## Table of Contents
- [Step 1: Per-Game Analysis](#step-1-per-game-analysis)
  - [1.1 Entire Game Metrics](#11-entire-game-metrics)
  - [1.2 Per Country Per Entire Game](#12-per-country-per-entire-game)
  - [1.3 Per Province Per Entire Game](#13-per-province-per-entire-game)
  - [1.4 Per Country Per Timestamp](#14-per-country-per-timestamp)
  - [1.5 Per Province Per Timestamp](#15-per-province-per-timestamp)
- [Step 2: Cross-Game Aggregate Analysis](#step-2-cross-game-aggregate-analysis)
  - [2.1 Global Metrics](#21-global-metrics)
  - [2.2 Per Country Aggregate](#22-per-country-aggregate)
  - [2.3 Per Province Aggregate](#23-per-province-aggregate)
- [Additional Aggregation Levels](#additional-aggregation-levels)
- [Glossary](#glossary)

---

## Step 1: Per-Game Analysis

### 1.1 Entire Game Metrics

#### Game Duration & Timeline
- **Total game duration** (in days/hours)
- **Game start timestamp**
- **Game end timestamp**
- **Number of game days simulated**
- **Average time between updates**
- **Total number of updates**

#### Victory & Outcome
- **Winner player IDs**
- **Victory type** (Solo or Coalition)

#### Participation Metrics
- **Total number of players**
- **Number of active players at start**
- **Number of active players at end**
- **Player dropout rate**
- **Number of AI players**
- **Number of human players**

#### Economic Overview
- **Total resources produced** (all types combined)
- **Total money generated**
- **Total resources traded**
- **Total trade volume** (money exchanged)
- **Average resource prices over game**
- **Resource price volatility**

#### Military Overview
- **Number of provinces that changed ownership**

#### Diplomatic Overview
- **Number of alliances formed**
- **Number of alliance dissolutions**
- **Number of wars declared**
- **Number of peace treaties**
- **Number of right of way agreements**

#### Map Control
- **Total number of provinces in game**
- **Number of provinces contested** (changed hands at least once)
- **Average province ownership duration**
- **Number of provinces never captured**

---

### 1.2 Per Country Per Entire Game

#### Identification
- **Country/Player ID**
- **Country/Faction name**
- **Player name**
- **Team/Alliance ID**
- **Is AI or Human**

#### Performance & Ranking
- **Final rank/placement**
- **Victory points earned**
- **Victory points rank**
- **Time survived** (until elimination or game end)
- **Was eliminated** (boolean)
- **Elimination timestamp**

#### Territory Metrics
- **Starting number of provinces**
- **Ending number of provinces**
- **Maximum provinces controlled**
- **Minimum provinces controlled**
- **Net province gain/loss**
- **Average number of provinces controlled**
- **Total provinces captured**
- **Total provinces lost**
- **Territory expansion rate** (Victory points per day)

#### Economic Metrics
- **Total money earned**
- **Total resource production** (by type)
- **Average resource production rate** (by type)
- **Peak resource production**

#### Diplomatic Activity
- **Number of alliances joined**
- **Alliance membership duration**
- **Number of wars participated in**
- **Number of peace treaties signed**
- **Trade agreements signed**

#### Province Management
- **Total buildings constructed**
- **Buildings constructed** (by type)
- **Total buildings destroyed**
- **Buildings destroyed** (by type)
- **Building damage taken** (by type)
- **Average province morale**
- **Minimum province morale experienced**
- **Infrastructure investment** (total spent on buildings)
---

### 1.3 Per Province Per Entire Game

#### Identification
- **Province ID**
- **Province name**
- **Region**
- **Terrain type**
- **Is coastal** (boolean)

#### Ownership History
- **Starting owner**
- **Ending owner**
- **Number of ownership changes**
- **List of all owners** (chronological)
- **Average ownership duration**
- **Longest owner**
- **Longest ownership duration**
- **Was contested** (boolean)

#### Economic Activity
- **Resource production type**
- **Resource production amount**
- **Average resource production rate**
- **Money production amount**
- **Was capital province**

#### Development
- **Buildings/upgrades constructed**
- **Final upgrades**
- **Total construction time**
- **Total infrastructure investment**

#### Morale & Stability
- **Average morale level**
- **Minimum morale level**
- **Maximum morale level**
- **Morale volatility** (standard deviation)
- **Time spent below 25% morale**
- **Time spent above 75% morale**
- **Time spent between 25% and 75% morale**

---

### 1.4 Per Country Per Timestamp

This aggregation level tracks how each country's metrics evolve over time, allowing for time-series analysis.

#### Territory
- **Number of provinces owned**
- **Territory size change** (vs previous timestamp)
- **Provinces gained since last update**
- **Provinces lost since last update**

#### Economy
- **Resource production rate** (by type)
- **Money production rate**

#### Development
- **Buildings under construction**
- **Average province morale**

#### Diplomacy
- **Active wars**

---

### 1.5 Per Province Per Timestamp

This tracks province-level changes over time within each game.

#### Ownership
- **Current owner**
- **Owner changed** (boolean, vs previous timestamp)
- **Time since ownership change**

#### Production
- **Current resource production**
- **Current money production**

#### Morale
- **Current morale level**
- **Morale change** (vs previous timestamp)

#### Development
- **Construction in progress**

---

## Step 2: Cross-Game Aggregate Analysis

### 2.1 Global Metrics

These metrics aggregate data across all 1000 games to identify global patterns.

#### Game Characteristics
- **Average game duration**
- **Median game duration**
- **Game duration distribution**
- **Standard deviation of game duration**

#### Victory Analysis
- **Most common victory type**
- **Victory type distribution** (percentages)

#### Participation Patterns
- **Average players per game**
- **Player dropout distribution**
- **Average survival time by country**
- **Average player survival time**
- **Average player rank**
- **Player rank distribution**

#### Economic Trends
- **Average total resources produced per game**
- **Average resources produced per game** (by type)
- **Average money earned per game**
- **Average resource production rate per game** (by type)
---

### 2.2 Per Country Aggregate

Metrics aggregated per country/faction across all games where that country was played.

#### Performance Statistics
- **Win rate**
- **Draw rate**
- **Loss rate**
- **Average placement**
- **Median placement**

#### Economic Performance
- **Average resources produced**
- **Average resources produced** (by type)
- **Average resource production rate** (by type)
- **Average money earned**

#### Territory Performance
- **Average provinces controlled**
- **Average expansion rate**
- **Most commonly controlled occupied provinces**

#### Diplomatic Tendencies
- **Alliance participation rate**
- **Average alliance duration**
- **Average wars declared**
- **Average peace treaties signed**
- **Average right of ways signed**

#### Survival Analysis
- **Average survival time**
- **Elimination rate**
- **Early game survival rate**
- **Mid game survival rate**
- **Late game survival rate**

---

### 2.3 Per Province Aggregate

Metrics aggregated per province across all games.

#### Contest Frequency
- **Contest frequency rate**
- **Average number of ownership changes**

#### Strategic Importance
- **Win correlation** (do winners typically control this province?)
- **Average time controlled by winner**

#### Ownership Patterns
- **Most common owner**
- **Average ownership duration by country**

#### Economic Value
- **Average resources produced**
- **Average resource production rate**
- **Average money produced**
- **Average money production rate**
- **Total economic contribution**

#### Development Patterns
- **Most common upgrades built**
- **Total investment** (resources spent)
- **Investment distribution** (by type)

#### Morale Patterns
- **Average morale**
- **Morale stability** (variance)


---

## Additional Aggregation Levels

### Per Time Period (Early/Mid/Late Game)
- **Early game metrics** (first 25% of game time)
- **Mid game metrics** (middle 50%)
- **Late game metrics** (final 25%)
- **Phase transition patterns**

### Per Resource Type
- **Average resource production rate** (by type)
- **Win rate and production rate by type correlation**

---

## Glossary

- **Peace Trity**: Switches from war to peace relation and both parties are still alive
