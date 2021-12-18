
from typing import TYPE_CHECKING

from ._ffi import alsa, ffi
from .event import EventType
from .exceptions import Error, StateError
from .util import _check_alsa_error

if TYPE_CHECKING:
    from .client import SequencerClientBase, _snd_seq_t


class Queue:
    def __init__(self, client: 'SequencerClientBase', queue_id: int):
        self.client = client
        self.queue_id = queue_id

    def __del__(self):
        try:
            self.close()
        except Error:
            pass

    def _get_client_handle(self) -> '_snd_seq_t':
        if self.client is None:
            raise StateError("Already closed")
        handle = self.client.handle
        if handle is None:
            raise StateError("Sequencer already closed")
        return handle

    def close(self):
        if self.queue_id is None or self.client is None:
            return
        handle = self.client.handle
        queue = self.queue_id
        self.queue_id = None
        self.client = None
        if handle:
            err = alsa.snd_seq_free_queue(handle, queue)
            _check_alsa_error(err)

    def set_tempo(self, tempo: int = 500000, ppq: int = 96):
        handle = self._get_client_handle()
        q_tempo = ffi.new("snd_seq_queue_tempo_t **", ffi.NULL)
        err = alsa.snd_seq_queue_tempo_malloc(q_tempo)
        _check_alsa_error(err)
        try:
            alsa.snd_seq_queue_tempo_set_tempo(q_tempo[0], tempo)
            alsa.snd_seq_queue_tempo_set_ppq(q_tempo[0], ppq)
            err = alsa.snd_seq_set_queue_tempo(handle, self.queue_id, q_tempo[0])
            _check_alsa_error(err)
        finally:
            alsa.snd_seq_queue_tempo_free(q_tempo[0])

    def control(self, event_type: EventType, value: int = 0):
        handle = self._get_client_handle()
        err = alsa.snd_seq_control_queue(handle, self.queue_id, event_type, value, ffi.NULL)
        _check_alsa_error(err)

    def start(self):
        return self.control(EventType.START)

    def stop(self):
        return self.control(EventType.STOP)

    def continue_(self):
        return self.control(EventType.CONTINUE)


__all__ = ["Queue"]
