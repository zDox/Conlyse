from typing import Union

import numpy as np

ADD_OPERATION = 1
REPLACE_OPERATION = 2
REMOVE_OPERATION = 3

REPLAY_VERSION = 207

PATCH_INDEX_DTYPE = np.dtype([
    ('offset', np.uint64),
    ('size', np.uint32),
])
PathNode = Union[str, int]
