from time import time

from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.replay.replay import Replay

if __name__ == "__main__":
    t1 = time()
    replay = Replay("test.zip", 'r')
    replay.open()
    print(replay.start_time)
    replay.close()