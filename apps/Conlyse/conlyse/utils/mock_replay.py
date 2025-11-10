from datetime import datetime

class Replay:
    def __init__(self, id, game_id, length, game_mode, size_bytes, game_speed,
                 game_day, started_timestamp, file_path, status, player_country):
        self.id = id
        self.game_id = game_id
        self.length = length
        self.game_mode = game_mode
        self.size_bytes = size_bytes
        self.game_speed = game_speed
        self.game_day = game_day
        self.started_timestamp = started_timestamp
        self.file_path = file_path
        self.status = status
        self.player_country = player_country


# Mock data
MOCK_REPLAYS = [
    Replay('1', 'CON-4892341', '2h 34m', 'World War III', 45678901, '1x', 15,
           datetime(2025, 11, 8, 14, 30), '/replays/conflict_nations_20251108_143000.cnr',
           'Ended', 'United States'),
    Replay('2', 'CON-4892128', '5h 12m', 'Flashpoint', 89234567, '2x', 28,
           datetime(2025, 11, 7, 9, 15), '/replays/conflict_nations_20251107_091500.cnr',
           'Running', 'Russia'),
    Replay('3', 'CON-4891845', '1h 48m', 'Rising Tides', 34567890, '1x', 8,
           datetime(2025, 11, 6, 18, 45), '/replays/conflict_nations_20251106_184500.cnr',
           'Ended', 'China'),
    Replay('4', 'CON-4891234', '3h 22m', 'World War III', 67891234, '1.5x', 22,
           datetime(2025, 11, 5, 12, 0), '/replays/conflict_nations_20251105_120000.cnr',
           'Ended', 'United Kingdom'),
    Replay('5', 'CON-4890987', '4h 56m', 'Clash of Nations', 78901234, '2x', 35,
           datetime(2025, 11, 4, 16, 30), '/replays/conflict_nations_20251104_163000.cnr',
           'Running', 'Germany'),
    Replay('6', 'CON-4890654', '2h 15m', 'Flashpoint', 43218765, '1x', 12,
           datetime(2025, 11, 3, 21, 0), '/replays/conflict_nations_20251103_210000.cnr',
           'Ended', 'France'),
    Replay('7', 'CON-4890321', '6h 42m', 'World War III', 98765432, '1x', 45,
           datetime(2025, 11, 2, 8, 30), '/replays/conflict_nations_20251102_083000.cnr',
           'Ended', 'Japan'),
]

