from time import time

from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.replay.replay import Replay

if __name__ == "__main__":
    t1 = time()
    replay = ReplayInterface("test.zip")
    replay.open()
    print(replay.get_my_resource_amounts())
    replay.close()