
from enum import IntFlag
from typing import NewType, Tuple, Union

from ._ffi import asound, ffi
from .address import SequencerAddress
from .event import SequencerEvent
from .exceptions import SequencerStateError
from .port import DEFAULT_PORT_TYPE, RW_PORT, SequencerPort, SequencerPortCaps, SequencerPortType
from .queue import SequencerQueue
from .util import _check_alsa_error

_snd_seq_t = NewType("_snd_seq_t", object)
_snd_seq_t_p = NewType("_snd_seq_t_p", Tuple[_snd_seq_t])


class SequencerStreamOpenTypes(IntFlag):
    OUTPUT = asound.SND_SEQ_OPEN_OUTPUT
    INPUT = asound.SND_SEQ_OPEN_INPUT
    DUPLEX = asound.SND_SEQ_OPEN_DUPLEX


class SequencerOpenMode(IntFlag):
    NONBLOCK = asound.SND_SEQ_NONBLOCK


class SequencerClient:
    client_id: str
    handle: _snd_seq_t
    _handle_p: _snd_seq_t_p

    def __init__(
            self,
            client_name: str,
            streams: int = SequencerStreamOpenTypes.DUPLEX,
            mode: int = SequencerOpenMode.NONBLOCK,
            sequencer_name: str = "default"):

        client_name_b = client_name.encode("utf-8")
        sequencer_name_b = sequencer_name.encode("utf-8")
        self._handle_p = ffi.new("snd_seq_t **", ffi.NULL)
        err = asound.snd_seq_open(self._handle_p, sequencer_name_b, streams, mode)
        _check_alsa_error(err)
        self.handle = self._handle_p[0]
        asound.snd_seq_set_client_name(self.handle, client_name_b)
        self.client_id = asound.snd_seq_client_id(self.handle)

    def __del__(self):
        self.close()

    def _check_handle(self):
        if self._handle_p is None:
            raise SequencerStateError("Already closed")

    def close(self):
        if self._handle_p is None:
            return
        asound.snd_seq_close(self._handle_p[0])
        self._handle_p = None  # type: ignore
        self.handle = None  # type: ignore

    def create_port(self,
                    name: str,
                    caps: SequencerPortCaps = RW_PORT,
                    port_type: SequencerPortType = DEFAULT_PORT_TYPE,
                    ) -> SequencerPort:
        self._check_handle()
        port = asound.snd_seq_create_simple_port(self.handle,
                                                 name.encode("utf-8"),
                                                 caps, port_type)
        _check_alsa_error(port)
        return SequencerPort(self, port)

    def create_queue(self, name: str = None) -> SequencerQueue:
        self._check_handle()
        if name is not None:
            queue = asound.snd_seq_alloc_named_queue(self.handle, name.encode("utf-8"))
        else:
            queue = asound.snd_seq_alloc_queue(self.handle)
        _check_alsa_error(queue)
        return SequencerQueue(self, queue)

    def drain_output(self):
        self._check_handle()
        err = asound.snd_seq_drain_output(self.handle)
        _check_alsa_error(err)

    def drop_output(self):
        self._check_handle()
        err = asound.snd_seq_drop_output(self.handle)
        _check_alsa_error(err)

    def event_input(self):
        self._check_handle()
        result = ffi.new("snd_seq_event_t**", ffi.NULL)
        err = asound.snd_seq_event_input(self.handle, result)
        _check_alsa_error(err)
        cls = SequencerEvent._specialized.get(result[0].type, SequencerEvent)
        return cls._from_alsa(result[0])

    def event_output(self,
                     event: SequencerEvent,
                     queue: Union['SequencerQueue', int] = None,
                     port: Union['SequencerPort', int] = None,
                     dest: SequencerAddress = None):
        self._check_handle()
        alsa_event = event._to_alsa()
        if queue is not None:
            if isinstance(queue, SequencerQueue):
                alsa_event.queue = queue.queue
            else:
                alsa_event.queue = queue
        elif event.queue is None:
            alsa_event.queue = asound.SND_SEQ_QUEUE_DIRECT
        if port is not None:
            if isinstance(port, SequencerPort):
                alsa_event.source.port = port.port_id
            else:
                alsa_event.source.port = port
        if dest is not None:
            alsa_event.dest.client = dest.client_id
            alsa_event.dest.port = dest.port_id
        elif event.dest is None:
            alsa_event.dest.client = asound.SND_SEQ_ADDRESS_SUBSCRIBERS
        err = asound.snd_seq_event_output(self.handle, alsa_event)
        _check_alsa_error(err)


__all__ = ["SequencerClient"]
