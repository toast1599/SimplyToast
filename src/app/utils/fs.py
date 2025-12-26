import ctypes
import os
from pathlib import Path

_THIS_FILE = Path(__file__).resolve()

# fs.py → utils → app → src
_LIB_PATH = _THIS_FILE.parents[2] / "libfs.so"

_lib = ctypes.CDLL(str(_LIB_PATH))

_lib.atomic_write.argtypes = (
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_size_t,
)
_lib.atomic_write.restype = ctypes.c_int


def atomic_write(path, data: str):
    path_b = os.fspath(path).encode("utf-8")
    data_b = data.encode("utf-8")

    rc = _lib.atomic_write(path_b, data_b, len(data_b))
    if rc != 0:
        raise OSError("atomic_write failed")
