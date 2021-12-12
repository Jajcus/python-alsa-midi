
from typing import TYPE_CHECKING, Tuple, Union

from ._ffi import asound
from .address import SequencerAddress
from .exceptions import SequencerError, SequencerStateError
from .util import _check_alsa_error

if TYPE_CHECKING:
    from .client import SequencerClient, _snd_seq_t_p

READ_PORT = asound.SND_SEQ_PORT_CAP_READ | asound.SND_SEQ_PORT_CAP_SUBS_READ
WRITE_PORT = asound.SND_SEQ_PORT_CAP_WRITE | asound.SND_SEQ_PORT_CAP_SUBS_WRITE
RW_PORT = READ_PORT | WRITE_PORT


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

    def _get_client_handle(self) -> '_snd_seq_t_p':
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
        self._client = None
        if handle:
            err = asound.snd_seq_delete_simple_port(handle[0], port_id)
            _check_alsa_error(err)

    def connect_to(self, dest: Union[SequencerAddress, Tuple[int, int]]):
        client_id, port_id = dest
        handle = self._get_client_handle()
        err = asound.snd_seq_connect_to(handle[0], self.port_id, client_id, port_id)
        _check_alsa_error(err)

    def disconnect_to(self, dest: Union[SequencerAddress, Tuple[int, int]]):
        client_id, port_id = dest
        handle = self._get_client_handle()
        err = asound.snd_seq_disconnect_to(handle[0], self.port_id, client_id, port_id)
        _check_alsa_error(err)

    def connect_from(self, src: Union[SequencerAddress, Tuple[int, int]]):
        client_id, port_id = src
        handle = self._get_client_handle()
        err = asound.snd_seq_connect_from(handle[0], self.port_id, client_id, port_id)
        _check_alsa_error(err)

    def disconnect_from(self, src: Union[SequencerAddress, Tuple[int, int]]):
        client_id, port_id = src
        handle = self._get_client_handle()
        err = asound.snd_seq_disconnect_from(handle[0], self.port_id, client_id, port_id)
        _check_alsa_error(err)

    # SequencerAddress interface – it is tuple-like

    def __iter__(self):
        return iter((self.client_id, self.port_id))

    def __getitem__(self, index):
        return (self.client_id, self.port_id)[index]


SequencerAddress.register(SequencerPort)

__all__ = ["SequencerPort", "READ_PORT", "WRITE_PORT", "RW_PORT"]
