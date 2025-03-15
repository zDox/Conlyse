from time import time

from conflict_interface.replay.replay import Replay

if __name__ == "__main__":
    t1 = time()
    with Replay("test.zip", 'r') as r:
        r._load_existing_replay()
    print(time() - t1)