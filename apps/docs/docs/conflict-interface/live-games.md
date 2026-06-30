---
id: live-games
title: Live Games
sidebar_position: 2
---

# Working with Live Games

This guide covers the full lifecycle of interacting with a live Conflict of Nations game: authenticating, discovering games, joining, selecting a country, querying state, and performing actions.

## Authentication

```python
from conflict_interface.interface.hub_interface import HubInterface

hub = HubInterface()
hub.login("your_username", "your_password")

# When done:
hub.logout()
```

To route traffic through a proxy:

```python
hub = HubInterface(proxy={"https": "http://proxy.example.com:8080"})
```

`login()` raises `AuthenticationException` if credentials are invalid.

## Discovering Games

### Global game listings

`get_global_games()` returns every publicly visible game. Pass keyword filters matching fields of `HubGameProperties`:

```python
from conflict_interface.data_types.hub_types.hub_game_state_enum import HubGameState

# All World War 3 games (scenario 5975) that are open to join
games = hub.get_global_games(
    scenario_id=5975,
    state=HubGameState.READY_TO_JOIN,
)

for g in games:
    print(f"[{g.game_id}] Day {g.day_of_game} — {g.open_slots} open slots")
```

Key fields on `HubGameProperties`:

| Field | Type | Description |
|---|---|---|
| `game_id` | `int` | Unique game identifier |
| `title` | `str` | Game title |
| `day_of_game` | `int` | Current in-game day |
| `open_slots` | `int` | Available country slots |
| `scenario_id` | `int` | Map/scenario identifier |
| `state` | `HubGameState` | `READY_TO_JOIN`, `ACTIVE`, `FINISHED` |
| `time_scale` | `float` | Speed multiplier (0.25 = 4× speed) |
| `alliance_game` | `bool` | Whether teams are enabled |
| `ranked` | `bool` | Ranked game |

### Your games

```python
my_games = hub.get_my_games()          # active games
archived  = hub.get_my_games(archived=True)
```

## Joining a Game

```python
# Join as a player (you will need to select a country)
game = hub.join_game(game_id=12345)

# Join as a guest — read-only, no country required
game = hub.join_game(game_id=12345, guest=True)
```

`join_game()` returns an `OnlineInterface` with the full game state already loaded.

To avoid an error when joining a game you are already registered in, check first:

```python
if not hub.is_in_game(12345):
    game = hub.join_game(12345)
```

## Selecting a Country

When joining as a player (not a guest), you must select a country before using methods marked *requires country selected*.

```python
# List available countries
countries = game.get_playable_countries()   # dict[int, PlayerProfile]
for player_id, profile in countries.items():
    print(f"{player_id}: {profile.nation_name}")

# Pick a specific one
game.select_country(country_id=42)

# Or let the server pick one for you
game.select_country(random_country_team_selection=True)

print(game.is_country_selected())  # True
```

Methods that require a selected country raise `CountryUnselectedException` if called before `select_country()`.

## Querying Game State

### Game info

```python
info = game.get_game_info_state()
print(info.day_of_game)         # current in-game day
print(info.start_of_game)       # datetime of game start
print(info.next_day_time)       # datetime when next day begins
print(info.open_slots)          # remaining country slots
print(info.game_ended)          # bool
```

### Time utilities

```python
print(game.game_day())                      # current day (int)
print(game.client_time())                   # current server time (datetime)
print(game.speed_modifier)                  # e.g. 4.0 for a 4× game

real = game.ingame_time_to_real(some_dt)    # convert ingame datetime to wall time
ingame = game.real_time_to_ingame(some_dt)  # convert wall time to ingame datetime
```

### Provinces and map

```python
# All provinces (land + sea)
all_provinces = game.get_provinces()

# Only land provinces
land = game.get_land_provinces()

# Filter by owner
owned = game.get_provinces(owner_id=game.player_id)

# By name
berlin = game.get_province_by_name("Berlin")

# Your provinces / cities (requires country selected)
my_provs  = game.get_my_provinces()
my_cities = game.get_my_cities()
```

Key fields on a `LandProvince`:

| Field | Type | Description |
|---|---|---|
| `id` | `int` | Province ID |
| `name` | `str` | Province name |
| `owner_id` | `int` | Player ID of current owner |
| `province_state_id` | `ProvinceStateID` | `MAINLAND_CITY`, `OCCUPIED_CITY`, `ANNEXED_CITY`, `MAINLAND_PROVINCE`, `OCCUPIED_PROVINCE` |
| `morale` | `float` | Province morale (0–100) |
| `resource_production` | `dict` | Resource output per day |
| `victory_points` | `int` | VP contribution |

### Players and teams

```python
all_players   = game.get_players()
human_players = game.get_human_players()     # excludes AI
my_profile    = game.get_my_player()         # requires country selected

# Filter by any PlayerProfile field
western_players = game.get_players(faction=Faction.WESTERN)
```

Key fields on `PlayerProfile`:

| Field | Type | Description |
|---|---|---|
| `player_id` | `int` | Player ID |
| `name` | `str` | Account name |
| `nation_name` | `str` | Country name |
| `faction` | `Faction` | `WESTERN` (US), `EASTERN` (RU), `EUROPEAN` (EU) |
| `defeated` | `bool` | Whether the player has been eliminated |
| `average_national_morale` | `float` | Nation-wide average morale |
| `computer_player` | `bool` | True for AI-controlled countries |

### Armies

```python
all_armies   = game.get_armies()
my_armies    = game.get_my_armies()                   # requires country selected
specific     = game.get_army(army_id=1234)
in_province  = game.get_armies_in_province(province_id=55)
```

Key fields on `Army`:

| Field | Type | Description |
|---|---|---|
| `id` | `int` | Army ID |
| `owner_id` | `int` | Owning player ID |
| `army_number` | `int` | Player-visible army number |
| `location_id` | `int` | Province ID where the army is located |
| `size` | `int` | Number of units |
| `health` | `float` | Overall health percentage |
| `fight_status` | `FightStatus` | `IDLE`, `FIGHTING`, `PATROLLING`, `SIEGING`, … |
| `on_sea` | `bool` | True if the army is at sea |

### Resources

```python
# Your resource amounts as dict[ResourceType, int]
amounts = game.get_my_resource_amounts()

from conflict_interface.data_types.newest.resource_state.resource_state_enums import ResourceType
print(amounts[ResourceType.SUPPLY])
print(amounts[ResourceType.MANPOWER])

# Affordability check
cost = {ResourceType.SUPPLY: 500, ResourceType.MANPOWER: 100}
if game.is_affordable(cost):
    print("Can afford it")
```

`ResourceType` values include: `SUPPLY`, `COMPONENT`, `MANPOWER`, `RARE_MATERIAL`, `FUEL`, `ELECTRONIC`, `CONVENTIONAL_WARHEAD`, `MONEY`.

### Research

```python
current   = game.get_current_research()           # list[Research]
completed = game.get_completed_research()          # dict[int, Research]
unlocked  = game.has_item_unlocked(item_id=42)    # bool
```

### Diplomatic relations

```python
from conflict_interface.data_types.newest.foreign_affairs_state.foreign_affairs_state_enums import ForeignAffairRelationTypes

relation = game.get_relation(sender_id=1, receiver_id=2)
```

## Performing Actions

Actions are queued on game objects and sent to the server in a single batch when you call `game.update()`. State is not refreshed until `update()` completes.

### Building upgrades

```python
# Look up the upgrade type
arms = game.get_upgrade_type_by_name_and_tier("Arms Industry", 1)

# Get the province
city = next(iter(game.get_my_provinces(name="Berlin").values()))

# Check and build
upgrade = city.get_possible_upgrade(id=arms.id)
if city.is_upgrade_buildable(upgrade):
    city.build_upgrade(upgrade)
    print(f"Queued: build {arms.upgrade_name} in {city.name}")

game.update()
```

To demolish or cancel an in-progress construction: `city.cancel_construction()`.

### Mobilizing units

```python
inf = game.get_unit_type_by_name_and_tier("Motorized Infantry", 1)
city.mobilize_unit_by_id(inf.id)
game.update()
```

Some unit types are faction-specific. Pass the optional `faction` argument if needed, or omit it to use the current player's faction automatically:

```python
from conflict_interface.data_types.newest.mod_state.faction import Faction

unit = game.get_unit_type_by_name_and_tier("Tank", 3, faction=Faction.WESTERN)
```

### Commanding armies

Armies expose command methods on the `Army` object:

```python
army = game.get_my_army_by_number(1)
target_province = game.get_province_by_name("Warsaw")

army.goto(target_province)   # move order
game.update()
```

See `examples/command_army.py` for split, attack, and patrol examples.

### Researching technologies

```python
research_type = game.get_research_type_by_name_and_tier("UAV", 1)
research_type.start_research()
game.update()
```

To cancel active research: `research.cancel_research()` on the `Research` object from `get_current_research()`.

### Trading resources

```python
resource_state = game.game_state.states.resource_state
resource_state.create_ask(ResourceType.SUPPLY, amount=15, price=10_000)  # sell offer
resource_state.create_bid(ResourceType.SUPPLY, amount=15, price=10_000)  # buy offer
game.update()
```

## The Update Cycle

```python
game.update()
```

`update()` does two things atomically:
1. Sends all queued actions to the game server.
2. Fetches the latest game state and merges it in.

After `update()` returns, all query methods reflect the new server state.

### Custom event handler

Register a callback that fires after each `update()`:

```python
def on_update(online_interface):
    day = online_interface.get_game_info_state().day_of_game
    print(f"Updated — now day {day}")

game.set_event_handler(on_update)
```
