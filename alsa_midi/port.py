
from enum import IntFlag
from typing import TYPE_CHECKING, Tuple, Union

from ._ffi import alsa
from .address import SequencerAddress
from .exceptions import SequencerError, SequencerStateError
from .util import _check_alsa_error

if TYPE_CHECKING:
    from .client import SequencerClient, _snd_seq_t


class SequencerPortCaps(IntFlag):
    READ = alsa.SND_SEQ_PORT_CAP_READ
    WRITE = alsa.SND_SEQ_PORT_CAP_WRITE
    SYNC_READ = alsa.SND_SEQ_PORT_CAP_SYNC_READ
    SYNC_WRITE = alsa.SND_SEQ_PORT_CAP_SYNC_WRITE
    DUPLEX = alsa.SND_SEQ_PORT_CAP_DUPLEX
    SUBS_READ = alsa.SND_SEQ_PORT_CAP_SUBS_READ
    SUBS_WRITE = alsa.SND_SEQ_PORT_CAP_SUBS_WRITE
    NO_EXPORT = alsa.SND_SEQ_PORT_CAP_NO_EXPORT


class SequencerPortType(IntFlag):
    SPECIFIC = alsa.SND_SEQ_PORT_TYPE_SPECIFIC
    MIDI_GENERIC = alsa.SND_SEQ_PORT_TYPE_MIDI_GENERIC
    MIDI_GM = alsa.SND_SEQ_PORT_TYPE_MIDI_GM
    MIDI_GS = alsa.SND_SEQ_PORT_TYPE_MIDI_GS
    MIDI_XG = alsa.SND_SEQ_PORT_TYPE_MIDI_XG
    MIDI_MT32 = alsa.SND_SEQ_PORT_TYPE_MIDI_MT32
    MIDI_GM2 = alsa.SND_SEQ_PORT_TYPE_MIDI_GM2
    SYNTH = alsa.SND_SEQ_PORT_TYPE_SYNTH
    DIRECT_SAMPLE = alsa.SND_SEQ_PORT_TYPE_DIRECT_SAMPLE
    SAMPLE = alsa.SND_SEQ_PORT_TYPE_SAMPLE
    HARDWARE = alsa.SND_SEQ_PORT_TYPE_HARDWARE
    SOFTWARE = alsa.SND_SEQ_PORT_TYPE_SOFTWARE
    SYNTHESIZER = alsa.SND_SEQ_PORT_TYPE_SYNTHESIZER
    PORT = alsa.SND_SEQ_PORT_TYPE_PORT
    APPLICATION = alsa.SND_SEQ_PORT_TYPE_APPLICATION


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
            err = alsa.snd_seq_delete_simple_port(handle, port_id)
            _check_alsa_error(err)

    def connect_to(self, dest: Union[SequencerAddress, Tuple[int, int]]):
        client_id, port_id = dest
        handle = self._get_client_handle()
        err = alsa.snd_seq_connect_to(handle, self.port_id, client_id, port_id)
        _check_alsa_error(err)

    def disconnect_to(self, dest: Union[SequencerAddress, Tuple[int, int]]):
        client_id, port_id = dest
        handle = self._get_client_handle()
        err = alsa.snd_seq_disconnect_to(handle, self.port_id, client_id, port_id)
        _check_alsa_error(err)

    def connect_from(self, src: Union[SequencerAddress, Tuple[int, int]]):
        client_id, port_id = src
        handle = self._get_client_handle()
        err = alsa.snd_seq_connect_from(handle, self.port_id, client_id, port_id)
        _check_alsa_error(err)

    def disconnect_from(self, src: Union[SequencerAddress, Tuple[int, int]]):
        client_id, port_id = src
        handle = self._get_client_handle()
        err = alsa.snd_seq_disconnect_from(handle, self.port_id, client_id, port_id)
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
