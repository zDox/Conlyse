import numpy as np

PATCH_INDEX_DTYPE = np.dtype([
    ('offset', np.uint64),
    ('size', np.uint32),
])