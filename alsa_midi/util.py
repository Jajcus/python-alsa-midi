
from ._ffi import alsa, ffi
from .exceptions import SequencerALSAError


def _check_alsa_error(code):
    if not isinstance(code, int):
        raise TypeError("ALSA error code must be an int")
    if code < 0:
        message = ffi.string(alsa.snd_strerror(code))
        raise SequencerALSAError(message.decode(), code)


def _ensure_4bit(value):
    value = int(value)
    if value < 0x00 or value > 0x0f:
        raise ValueError("4-bit value expected")
    return value


def _ensure_7bit(value):
    value = int(value)
    if value < 0x00 or value > 0x7f:
        raise ValueError("7-bit value expected")
    return value


__all__ = ["_check_alsa_error", "_ensure_4bit", "_ensure_7bit"]
