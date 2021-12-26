
import os

import pytest


@pytest.mark.skipif("PY_ALSA_MIDI_NO_COMPILE" not in os.environ,
                    reason="PY_ALSA_MIDI_NO_COMPILE not set")
def test_no_compile():
    with pytest.raises(ImportError):
        from alsa_midi import _ffi_bin  # type: ignore
        _ = _ffi_bin
    import alsa_midi
    from alsa_midi import _ffi_defs

    assert alsa_midi.ffi is _ffi_defs.ffi


@pytest.mark.skipif("PY_ALSA_MIDI_NO_COMPILE" in os.environ,
                    reason="PY_ALSA_MIDI_NO_COMPILE set")
def test_no_no_compile():
    import alsa_midi
    from alsa_midi import _ffi_bin  # type: ignore
    from alsa_midi import _ffi_defs

    assert alsa_midi.ffi is not _ffi_defs.ffi
    assert alsa_midi.ffi is _ffi_bin.ffi
