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
- **Starting position** (geographic region)

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
- **Territory expansion rate** (provinces per day)

#### Economic Metrics
- **Total money earned**
- **Total resource production** (by type)
- **Average resource production rate** (per day, by type)
- **Peak resource production**
- **Total money spent**
- **Total resources traded** (bought/sold separately)
- **Net trade balance** (by resource type)
- **Market activity** (number of orders placed)
- **Average resource prices paid/received**

#### Military Production
- **Total units produced** (overall)
- **Units produced by type** (infantry, armor, air, naval, etc.)
- **Total military spending**
- **Average unit production rate** (units per day)
- **Peak unit production rate**
- **Production diversity** (number of different unit types produced)

#### Military Performance
- **Total units destroyed** (inflicted on enemies)
- **Total units lost** (own casualties)
- **Kill/Death ratio**
- **Total armies commanded**
- **Average army size**
- **Maximum army size**
- **Number of battles initiated** (offensive)
- **Number of battles defended**
- **Offensive win rate**
- **Defensive win rate**
- **Total damage dealt**
- **Total damage received**

#### Research & Development
- **Total research points earned**
- **Number of technologies researched**
- **Research completion rate**
- **Technology tree diversity** (spread across categories)
- **Time to first research completion**

#### Diplomatic Activity
- **Number of alliances joined**
- **Alliance membership duration**
- **Number of wars participated in**
- **Number of peace treaties signed**
- **Trade agreements signed**
- **Diplomatic messages sent**

#### Province Management
- **Total buildings/upgrades constructed**
- **Average province morale**
- **Minimum province morale experienced**
- **Number of provinces with max upgrades**
- **Infrastructure investment** (total spent on buildings)

#### Activity Patterns
- **Actions per day** (average)
- **Peak activity period** (time of day)
- **Longest inactive period**
- **Average response time to threats**

---

### 1.3 Per Province Per Entire Game

#### Identification
- **Province ID**
- **Province name**
- **Geographic region**
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

#### Strategic Value
- **Victory points value**
- **Resource production type**
- **Resource production amount**
- **Money production**
- **Total value score** (combined metrics)
- **Was capital/core province**

#### Economic Activity
- **Total resources produced** (over game)
- **Total money produced**
- **Average production rate**
- **Production efficiency** (actual vs potential)

#### Military Activity
- **Number of battles fought in province**
- **Total units stationed over time**
- **Was used as staging area** (for attacks)
- **Number of armies garrisoned**

#### Development
- **Buildings/upgrades constructed**
- **Final upgrade level**
- **Total construction time**
- **Total infrastructure investment**

#### Morale & Stability
- **Average morale level**
- **Minimum morale level**
- **Maximum morale level**
- **Morale volatility** (standard deviation)
- **Number of morale drops below 50%**

---

### 1.4 Per Country Per Timestamp

This aggregation level tracks how each country's metrics evolve over time, allowing for time-series analysis.

#### Territory
- **Number of provinces owned**
- **Territory size change** (vs previous timestamp)
- **Provinces gained since last update**
- **Provinces lost since last update**

#### Economy
- **Current resource stockpiles** (by type)
- **Money available**
- **Resource production rate** (current)
- **Money production rate** (current)
- **Active trade orders**
- **Resources bought/sold since last update**

#### Military Strength
- **Total army count**
- **Total unit count**
- **Units by type** (breakdown)
- **Average army size**
- **Units in combat**
- **Units in transit**
- **Units garrisoned**
- **Military power index** (composite score)

#### Military Actions
- **Battles initiated**
- **Battles defended**
- **Units produced since last update**
- **Units lost since last update**
- **Units killed since last update**

#### Development
- **Buildings under construction**
- **Units in production queue**
- **Research in progress**
- **Average province morale**

#### Research
- **Research points accumulated**
- **Active research projects**
- **Technologies completed**

#### Diplomacy
- **Current alliances**
- **Active wars**
- **Diplomatic stance changes**

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
- **Production efficiency**

#### Morale
- **Current morale level**
- **Morale change** (vs previous timestamp)
- **Morale trend** (improving/declining/stable)

#### Military Presence
- **Number of friendly armies**
- **Number of enemy armies**
- **Garrison strength**
- **Is under attack** (boolean)
- **Battle in progress** (boolean)

#### Development
- **Current upgrades/buildings**
- **Construction in progress**
- **Construction completion progress**

#### Resources
- **Resource stockpile** (if applicable)
- **Resources consumed**
- **Resources added**

---

## Step 2: Cross-Game Aggregate Analysis

### 2.1 Global Metrics

These metrics aggregate data across all 1000 games to identify global patterns.

#### Game Characteristics
- **Average game duration**
- **Median game duration**
- **Shortest game**
- **Longest game**
- **Game duration distribution**
- **Standard deviation of game duration**

#### Victory Analysis
- **Most common victory type**
- **Average time to victory** (by victory type)
- **Victory type distribution** (percentages)
- **Win rate by starting position**
- **Win rate by country/faction**

#### Participation Patterns
- **Average players per game**
- **Player dropout distribution**
- **Average player survival time**
- **AI vs Human win rates**
- **Most active player count range**

#### Economic Trends
- **Average total resources produced per game**
- **Most traded resource type**
- **Average resource price trends**
- **Resource price correlation analysis**
- **Economic growth patterns**

#### Military Patterns
- **Average units produced per game**
- **Most produced unit types**
- **Average kill/death ratios**
- **Battle frequency distribution**
- **Army size distributions**

#### Temporal Patterns
- **Peak activity hours** (aggregated)
- **Seasonal patterns** (if games span seasons)
- **Update frequency patterns**

#### Strategic Patterns
- **Most contested provinces** (across games)
- **Most valuable starting positions**
- **Alliance formation patterns**
- **Technology research patterns**

---

### 2.2 Per Country Aggregate

Metrics aggregated per country/faction across all games where that country was played.

#### Performance Statistics
- **Games played**
- **Wins**
- **Losses**
- **Eliminations**
- **Win rate**
- **Average placement**
- **Median placement**

#### Economic Performance
- **Average resources produced**
- **Average money earned**
- **Resource production efficiency**
- **Trade activity level**
- **Economic growth rate**

#### Military Performance
- **Average units produced**
- **Average kill/death ratio**
- **Average military strength**
- **Most commonly produced units**
- **Battle win rates** (offensive/defensive)

#### Territory Performance
- **Average provinces controlled**
- **Average expansion rate**
- **Territory retention rate**
- **Provinces most commonly controlled**

#### Technology & Development
- **Average research completion**
- **Most researched technologies**
- **Technology diversity**
- **Upgrade investment patterns**

#### Diplomatic Tendencies
- **Alliance participation rate**
- **Average alliance duration**
- **War frequency**
- **Peace treaty frequency**

#### Survival Analysis
- **Average survival time**
- **Elimination rate**
- **Early game survival rate**
- **Mid game survival rate**
- **Late game survival rate**

#### Starting Advantage/Disadvantage
- **Win rate by starting position**
- **Average starting resources**
- **Average starting provinces**
- **Strategic starting value**

---

### 2.3 Per Province Aggregate

Metrics aggregated per province across all games.

#### Contest Frequency
- **Number of games where province existed**
- **Number of games contested**
- **Contest frequency rate**
- **Average number of ownership changes**

#### Strategic Importance
- **Win correlation** (do winners typically control this province?)
- **Average time controlled by winner**
- **Importance score** (derived metric)

#### Ownership Patterns
- **Most common owners**
- **Average ownership duration by country**
- **Control difficulty** (how often it changes hands)

#### Economic Value
- **Average resources produced**
- **Average money produced**
- **Total economic contribution**
- **Production consistency** (variance)

#### Military Significance
- **Average battles per game**
- **Total battles across all games**
- **Battle intensity** (battles per time owned)
- **Defensive value** (battles defended vs lost)

#### Development Patterns
- **Average upgrade level reached**
- **Most common upgrades built**
- **Investment level** (resources spent)

#### Morale Patterns
- **Average morale across games**
- **Morale stability** (variance)
- **Revolt frequency** (if applicable)

#### Geographic Analysis
- **Strategic location index**
- **Border province frequency**
- **Proximity to capitals**
- **Accessibility** (ease of attack/defense)

---

## Additional Aggregation Levels

### Per Alliance/Team
- **Alliance size over time**
- **Alliance victory rates**
- **Alliance stability** (member retention)
- **Alliance effectiveness** (collective performance)
- **Internal cooperation metrics**

### Per Time Period (Early/Mid/Late Game)
- **Early game metrics** (first 25% of game time)
- **Mid game metrics** (middle 50%)
- **Late game metrics** (final 25%)
- **Phase transition patterns**

### Per Unit Type
- **Production frequency**
- **Cost-effectiveness**
- **Kill/death ratio by unit type**
- **Usage patterns** (when in game timeline)
- **Counter relationships** (which units beat which)

### Per Technology/Research
- **Adoption rate**
- **Time to research**
- **Research priority** (order researched)
- **Impact on performance**
- **Win correlation**

### Per Resource Type
- **Production patterns**
- **Consumption patterns**
- **Trade volume**
- **Price trends**
- **Strategic value correlation**

---

## Advanced Analytics

### Correlation Analysis
- **Resource production vs military strength**
- **Territory size vs victory probability**
- **Alliance membership vs survival time**
- **Technology research vs win rate**
- **Activity level vs performance**
- **Starting position vs final placement**

### Time-Series Analysis
- **Growth trajectories** (economic, military, territorial)
- **Momentum indicators** (identifying turning points)
- **Trend detection** (expansion, contraction, stability)
- **Seasonal patterns** (if applicable)

### Comparative Analysis
- **AI vs Human performance differences**
- **Team vs solo player performance**
- **Aggressive vs defensive strategies**
- **Economic vs military focus**

### Predictive Metrics
- **Early indicators of victory**
- **Elimination risk factors**
- **Comeback potential metrics**
- **Critical moments identification**

### Network Analysis
- **Alliance network structures**
- **Trade network patterns**
- **Geographic connectivity**
- **Influence propagation**

### Efficiency Metrics
- **Resource utilization efficiency**
- **Military spending efficiency**
- **Territory management efficiency**
- **Time management efficiency**

---

## Implementation Notes

### Data Collection Requirements
- All metrics should be calculated from replay files using the replay system
- Timestamps should be normalized to game time (game day) for consistency
- Missing data should be handled gracefully (null/NaN values)

### Calculation Guidelines
- Use consistent units (e.g., game days, not real-time hours)
- Apply appropriate aggregation functions (mean, median, sum, etc.)
- Consider weighted averages where appropriate
- Document any derived/composite metrics clearly

### Visualization Recommendations
- Time-series metrics: line charts
- Distributions: histograms, box plots
- Comparisons: bar charts, radar charts
- Correlations: scatter plots, heatmaps
- Geographic: map overlays
- Networks: graph visualizations

### Performance Considerations
- Pre-compute frequently used aggregations
- Use efficient data structures for time-series data
- Consider parallel processing for cross-game analysis
- Implement caching for expensive calculations

---

## Glossary

- **Peace Trity**: Switches from war to peace relation and both parties are still alive
