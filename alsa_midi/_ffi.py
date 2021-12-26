"""
FFI interface to ALSA library, either from a complied module (ABI level) or
from pure Python (API level)
"""

try:
    from ._ffi_bin import ffi  # type: ignore
    alsa = ffi.dlopen(None)
except ImportError:
    from ._ffi_defs import ffi
    alsa = ffi.dlopen("libasound.so.2")
