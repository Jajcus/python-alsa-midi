from setuptools import setup

setup(
    cffi_modules=["alsa_midi/_ffi_defs.py:ffi"]
    )
