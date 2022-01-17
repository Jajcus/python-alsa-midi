
from typing import TYPE_CHECKING, NewType, Optional

from ._ffi import alsa, ffi
from .event import EventType
from .exceptions import Error, StateError
from .util import _check_alsa_error

if TYPE_CHECKING:
    from .client import SequencerClientBase, _snd_seq_t

_snd_seq_queue_info_t = NewType("_snd_seq_queue_info_t", object)


class QueueInfo:
    """Sequencer queue information.

    Represents :alsa:`snd_seq_queue_info_t`.

    :param queue_id: queue identifier
    :param name: queue name
    :param owner: client id of the queue owner
    :param locked: queue locked flag
    :param flags: conditional bit flags

    :ivar queue_id: queue identifier
    :ivar name: queue name
    :ivar owner: client id of the queue owner
    :ivar locked: queue locked flag
    :ivar flags: conditional bit flags
    """

    queue_id: int
    name: str
    owner: int
    locked: bool
    flags: int

    def __init__(self,
                 queue_id: int = 0,
                 name: str = "",
                 owner: int = 0,
                 locked: bool = False,
                 flags: int = 0):

        self.queue_id = queue_id
        self.name = name
        self.owner = owner
        self.locked = locked
        self.flags = flags

    def __repr__(self):
        return f"<QueueInfo #{self.queue_id} {self.name!r}>"

    @classmethod
    def _from_alsa(cls, info: _snd_seq_queue_info_t):
        name = ffi.string(alsa.snd_seq_queue_info_get_name(info))
        return cls(
                queue_id=alsa.snd_seq_queue_info_get_queue(info),
                name=name.decode(),
                owner=alsa.snd_seq_queue_info_get_owner(info),
                locked=bool(alsa.snd_seq_queue_info_get_locked(info)),
                flags=alsa.snd_seq_queue_info_get_flags(info),
                )

    def _to_alsa(self, client_id) -> _snd_seq_queue_info_t:
        info_p = ffi.new("snd_seq_queue_info_t **")
        err = alsa.snd_seq_queue_info_malloc(info_p)
        _check_alsa_error(err)
        info = ffi.gc(info_p[0], alsa.snd_seq_queue_info_free)
        alsa.snd_seq_queue_info_set_name(info, self.name.encode())
        if self.owner == 0:
            alsa.snd_seq_queue_info_set_owner(info, client_id)
        else:
            alsa.snd_seq_queue_info_set_owner(info, self.owner)
        alsa.snd_seq_queue_info_set_locked(info, int(self.locked))
        alsa.snd_seq_queue_info_set_flags(info, self.flags)
        return info


class Queue:
    """Sequencer queue.

    :ivar client: client object this queue belongs to
    :ivar queue_id: queue identifier
    """

    client: Optional['SequencerClientBase']
    queue_id: int

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
        """Close the queue, freeing any resources.

        Wraps :alsa:`snd_seq_free_queue`."""
        if self.queue_id is None or self.client is None:
            return
        handle = self.client.handle
        queue = self.queue_id
        self.queue_id = None  # type: ignore
        self.client = None
        if handle:
            err = alsa.snd_seq_free_queue(handle, queue)
            _check_alsa_error(err)

    def set_tempo(self, tempo: int = 500000, ppq: int = 96):
        """Set the tempo of the queue.

        :param tempo: MIDI tempo – microseconds per quarter note
        :param ppq: MIDI pulses per quarter note

        Wraps :alsa:`snd_seq_set_queue_tempo`.
        """
        handle = self._get_client_handle()
        q_tempo_p = ffi.new("snd_seq_queue_tempo_t **", ffi.NULL)
        err = alsa.snd_seq_queue_tempo_malloc(q_tempo_p)
        _check_alsa_error(err)
        q_tempo = ffi.gc(q_tempo_p[0], alsa.snd_seq_queue_tempo_free)
        alsa.snd_seq_queue_tempo_set_tempo(q_tempo, tempo)
        alsa.snd_seq_queue_tempo_set_ppq(q_tempo, ppq)
        err = alsa.snd_seq_set_queue_tempo(handle, self.queue_id, q_tempo)
        _check_alsa_error(err)

    def control(self, event_type: EventType, value: int = 0):
        """Queue control (start/stop/continue).

        :param event_type: queue control event type
        :param value: value for the event

        Creates and sends (to the output buffer) queue control event.
        :meth:`~alsa_midi.SequencerClient.drain_output()` needs to be called for the
        event to actually be sent and executed.

        Wraps :alsa:`snd_seq_control_queue`.
        """
        # TODO: event argument
        handle = self._get_client_handle()
        err = alsa.snd_seq_control_queue(handle, self.queue_id, event_type, value, ffi.NULL)
        _check_alsa_error(err)

    def start(self):
        """Start the queue.

        :meth:`~alsa_midi.SequencerClient.drain_output()` needs to be called for actual effect.
        """
        return self.control(EventType.START)

    def stop(self):
        """Stop the queue.

        :meth:`~alsa_midi.SequencerClient.drain_output()` needs to be called for actual effect.
        """
        return self.control(EventType.STOP)

    def continue_(self):
        """Continue running the queue.

        :meth:`~alsa_midi.SequencerClient.drain_output()` needs to be called for actual effect.
        """
        return self.control(EventType.CONTINUE)

    def get_info(self) -> QueueInfo:
        """Obtain queue attributes.

        Wraps :alsa:`snd_seq_get_queue_info`."""

        if self.client is None or self.queue_id is None:
            raise StateError("Already closed")
        return self.client.get_queue_info(self.queue_id)

    def set_info(self, info: QueueInfo):
        """Change queue attributes.

        :param info: new values

        Wraps :alsa:`snd_seq_set_queue_info`."""

        if self.client is None or self.queue_id is None:
            raise StateError("Already closed")
        return self.client.set_queue_info(self.queue_id, info)

    def get_usage(self) -> bool:
        """Get the queue usage flag.

        Wraps :alsa:`snd_seq_get_queue_usage`.

        :return: `True` if the queue is considered in use by the current client."""
        handle = self._get_client_handle()
        result = alsa.snd_seq_get_queue_usage(handle, self.queue_id)
        _check_alsa_error(result)
        return bool(result)

    def set_usage(self, usage: bool):
        """Marks the queue in use by the current client.

        Wraps :alsa:`snd_seq_set_queue_usage`.

        :param usage: True to enable queue usage
        """
        handle = self._get_client_handle()
        err = alsa.snd_seq_set_queue_usage(handle, self.queue_id, int(usage))
        _check_alsa_error(err)


__all__ = ["Queue", "QueueInfo"]
