
import os

from setuptools import setup

if "PY_ALSA_MIDI_NO_COMPILE" in os.environ:
    cffi_modules = []
else:
    cffi_modules = ["alsa_midi/_ffi_defs.py:ffi"]

setup(cffi_modules=cffi_modules)
