
import errno
import os

import pytest

from alsa_midi import SequencerALSAError
from alsa_midi.util import _check_alsa_error, _ensure_4bit, _ensure_7bit


def test_check_alsa_error():
    _check_alsa_error(0)
    _check_alsa_error(1)
    _check_alsa_error(100)
    _check_alsa_error(10000)

    with pytest.raises(SequencerALSAError) as exc_info:
        _check_alsa_error(-1)
    assert exc_info.value.errnum == -1
    assert isinstance(exc_info.value.message, str)
    assert str(exc_info.value.message) == exc_info.value.message

    with pytest.raises(SequencerALSAError) as exc_info:
        _check_alsa_error(-errno.ENOENT)
    assert exc_info.value.errnum == -errno.ENOENT
    assert isinstance(exc_info.value.message, str)
    assert str(exc_info.value.message) == exc_info.value.message
    assert exc_info.value.message == os.strerror(errno.ENOENT)

    with pytest.raises(SequencerALSAError) as exc_info:
        _check_alsa_error(-500000)
    assert exc_info.value.errnum == -500000
    assert isinstance(exc_info.value.message, str)
    assert str(exc_info.value.message) == exc_info.value.message

    with pytest.raises(TypeError):
        _check_alsa_error("xxx")

    with pytest.raises(TypeError):
        _check_alsa_error(None)


def test_ensure_4bit():
    assert _ensure_4bit(0x00) == 0x00
    assert _ensure_4bit(0x01) == 0x01
    assert _ensure_4bit(0x0f) == 0x0f

    with pytest.raises(ValueError):
        _ensure_4bit(-1)
    with pytest.raises(ValueError):
        _ensure_4bit(0x10)
    with pytest.raises(ValueError):
        _ensure_4bit(100000)
    with pytest.raises(ValueError):
        _ensure_4bit("xxx")


def test_ensure_7bit():
    assert _ensure_7bit(0x00) == 0x00
    assert _ensure_7bit(0x01) == 0x01
    assert _ensure_7bit(0x0f) == 0x0f
    assert _ensure_7bit(0x7f) == 0x7f

    with pytest.raises(ValueError):
        _ensure_7bit(-1)
    with pytest.raises(ValueError):
        _ensure_7bit(0x80)
    with pytest.raises(ValueError):
        _ensure_7bit(100000)
    with pytest.raises(ValueError):
        _ensure_7bit("xxx")
