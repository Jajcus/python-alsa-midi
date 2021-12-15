
from enum import IntFlag
from typing import TYPE_CHECKING, Tuple, Union

from ._ffi import asound
from .address import SequencerAddress
from .exceptions import SequencerError, SequencerStateError
from .util import _check_alsa_error

if TYPE_CHECKING:
    from .client import SequencerClient, _snd_seq_t


class SequencerPortCaps(IntFlag):
    READ = asound.SND_SEQ_PORT_CAP_READ
    WRITE = asound.SND_SEQ_PORT_CAP_WRITE
    SYNC_READ = asound.SND_SEQ_PORT_CAP_SYNC_READ
    SYNC_WRITE = asound.SND_SEQ_PORT_CAP_SYNC_WRITE
    DUPLEX = asound.SND_SEQ_PORT_CAP_DUPLEX
    SUBS_READ = asound.SND_SEQ_PORT_CAP_SUBS_READ
    SUBS_WRITE = asound.SND_SEQ_PORT_CAP_SUBS_WRITE
    NO_EXPORT = asound.SND_SEQ_PORT_CAP_NO_EXPORT


class SequencerPortType(IntFlag):
    SPECIFIC = asound.SND_SEQ_PORT_TYPE_SPECIFIC
    MIDI_GENERIC = asound.SND_SEQ_PORT_TYPE_MIDI_GENERIC
    MIDI_GM = asound.SND_SEQ_PORT_TYPE_MIDI_GM
    MIDI_GS = asound.SND_SEQ_PORT_TYPE_MIDI_GS
    MIDI_XG = asound.SND_SEQ_PORT_TYPE_MIDI_XG
    MIDI_MT32 = asound.SND_SEQ_PORT_TYPE_MIDI_MT32
    MIDI_GM2 = asound.SND_SEQ_PORT_TYPE_MIDI_GM2
    SYNTH = asound.SND_SEQ_PORT_TYPE_SYNTH
    DIRECT_SAMPLE = asound.SND_SEQ_PORT_TYPE_DIRECT_SAMPLE
    SAMPLE = asound.SND_SEQ_PORT_TYPE_SAMPLE
    HARDWARE = asound.SND_SEQ_PORT_TYPE_HARDWARE
    SOFTWARE = asound.SND_SEQ_PORT_TYPE_SOFTWARE
    SYNTHESIZER = asound.SND_SEQ_PORT_TYPE_SYNTHESIZER
    PORT = asound.SND_SEQ_PORT_TYPE_PORT
    APPLICATION = asound.SND_SEQ_PORT_TYPE_APPLICATION


READ_PORT = SequencerPortCaps.READ | SequencerPortCaps.SUBS_READ
WRITE_PORT = SequencerPortCaps.WRITE | SequencerPortCaps.SUBS_WRITE
RW_PORT = READ_PORT | WRITE_PORT

DEFAULT_PORT_TYPE = SequencerPortType.MIDI_GENERIC | SequencerPortType.SOFTWARE


class SequencerPort:
    def __init__(self, client: 'SequencerClient', port_id: int):
        self.client_id = client.client_id
        self.port_id = port_id
        self.client = client

    def __del__(self):
        try:
            self.close()
        except SequencerError:
            pass

    def _get_client_handle(self) -> '_snd_seq_t':
        if self.client is None:
            raise SequencerStateError("Already closed")
        handle = self.client.handle
        if handle is None:
            raise SequencerStateError("Sequencer already closed")
        return handle

    def close(self):
        if self.client is None:
            return
        handle = self.client.handle
        port_id = self.port_id
        self.client = None
        if handle:
            err = asound.snd_seq_delete_simple_port(handle, port_id)
            _check_alsa_error(err)

    def connect_to(self, dest: Union[SequencerAddress, Tuple[int, int]]):
        client_id, port_id = dest
        handle = self._get_client_handle()
        err = asound.snd_seq_connect_to(handle, self.port_id, client_id, port_id)
        _check_alsa_error(err)

    def disconnect_to(self, dest: Union[SequencerAddress, Tuple[int, int]]):
        client_id, port_id = dest
        handle = self._get_client_handle()
        err = asound.snd_seq_disconnect_to(handle, self.port_id, client_id, port_id)
        _check_alsa_error(err)

    def connect_from(self, src: Union[SequencerAddress, Tuple[int, int]]):
        client_id, port_id = src
        handle = self._get_client_handle()
        err = asound.snd_seq_connect_from(handle, self.port_id, client_id, port_id)
        _check_alsa_error(err)

    def disconnect_from(self, src: Union[SequencerAddress, Tuple[int, int]]):
        client_id, port_id = src
        handle = self._get_client_handle()
        err = asound.snd_seq_disconnect_from(handle, self.port_id, client_id, port_id)
        _check_alsa_error(err)

    # SequencerAddress interface – it is tuple-like

    def __iter__(self):
        return iter((self.client_id, self.port_id))

    def __getitem__(self, index):
        return (self.client_id, self.port_id)[index]

    def __eq__(self, other):
        if self is other:
            return True

        # no isinstance() here, as two different SequencerPort object are not equal,
        # even if they have the same address
        if other.__class__ is SequencerAddress:
            return (self.client_id, self.port_id) == other


SequencerAddress.register(SequencerPort)

__all__ = ["SequencerPortCaps", "SequencerPortType", "SequencerPort",
           "READ_PORT", "WRITE_PORT", "RW_PORT", "DEFAULT_PORT_TYPE"]
