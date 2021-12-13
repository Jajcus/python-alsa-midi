import sys

from setuptools import setup

if sys.version_info < (3, 10):
    cffi_modules = ["alsa_midi/_ffi_defs.py:ffi"]
else:
    cffi_modules = None

setup(
    cffi_modules=cffi_modules
    )
