
import asyncio
import errno
import select
import time
from collections import namedtuple
from enum import IntEnum, IntFlag
from functools import partial
from typing import Any, Callable, List, NewType, Optional, Set, Tuple, Union, overload

from ._ffi import alsa, ffi
from .address import Address, AddressType
from .event import MIDI_BYTES_EVENTS, Event, EventType, MidiBytesEvent, _snd_seq_event_t
from .exceptions import StateError
from .port import (DEFAULT_PORT_TYPE, READ_PORT_PREFERRED_TYPES, RW_PORT, RW_PORT_PREFERRED_TYPES,
                   WRITE_PORT_PREFERRED_TYPES, Port, PortCaps, PortInfo, PortType,
                   get_port_info_sort_key)
from .queue import Queue
from .util import _check_alsa_error

_snd_seq_t = NewType("_snd_seq_t", object)
_snd_seq_t_p = NewType("_snd_seq_t_p", Tuple[_snd_seq_t])
_snd_midi_event_t = NewType("_snd_midi_event_t", object)


class StreamOpenType(IntFlag):
    """Stream open type flags."""
    OUTPUT = alsa.SND_SEQ_OPEN_OUTPUT
    INPUT = alsa.SND_SEQ_OPEN_INPUT
    DUPLEX = alsa.SND_SEQ_OPEN_DUPLEX


class OpenMode(IntFlag):
    """Sequencer client open mode flags."""
    NONBLOCK = alsa.SND_SEQ_NONBLOCK


class ClientType(IntEnum):
    """Client type constants."""
    _UNSET = 0
    USER = alsa.SND_SEQ_USER_CLIENT
    KERNEL = alsa.SND_SEQ_KERNEL_CLIENT


class SequencerType(IntEnum):
    """Sequencer type constants."""
    _UNSET = 0
    HW = alsa.SND_SEQ_TYPE_HW
    SHM = alsa.SND_SEQ_TYPE_SHM
    INET = alsa.SND_SEQ_TYPE_INET


_snd_seq_client_info_t = NewType("_snd_seq_client_info_t", object)


class ClientInfo:
    """Client information.

    Represents data from :alsa:`snd_seq_client_info_t`

    :param client_id: client identifier
    :param name: client name
    :param broadcast_filter: broadcast filter usage
    :param error_bounce: error-bounce usage
    :param type: client type
    :param card_id: card identifier for hardware clients
    :param pid: process id for software clients
    :param num_ports: number of opened ports
    :param event_lost: number of lost events

    :ivar client_id: client identifier
    :ivar name: client name
    :ivar broadcast_filter: broadcast filter usage
    :ivar error_bounce: error-bounce usage
    :ivar type: client type
    :ivar card_id: card identifier for hardware clients
    :ivar pid: process id for software clients
    :ivar num_ports: number of opened ports
    :ivar event_lost: number of lost events
    """
    client_id: int
    name: str
    broadcast_filter: bool
    error_bounce: bool
    type: Optional[ClientType]
    card_id: Optional[int]
    pid: Optional[int]
    num_ports: int
    event_lost: int
    event_filter: Optional[Set[EventType]]

    def __init__(self,
                 client_id: int,
                 name: str,
                 broadcast_filter: bool = False,
                 error_bounce: bool = False,
                 type: ClientType = None,
                 card_id: Optional[int] = None,
                 pid: Optional[int] = None,
                 num_ports: int = 0,
                 event_lost: int = 0,
                 event_filter: Optional[Set[EventType]] = None):
        self.client_id = client_id
        self.name = name
        self.broadcast_filter = broadcast_filter
        self.error_bounce = error_bounce
        self.type = type
        self.card_id = card_id
        self.pid = pid
        self.num_ports = num_ports
        self.event_lost = event_lost
        self.event_filter = event_filter

    @classmethod
    def _from_alsa(cls, info: _snd_seq_client_info_t):
        """Create a ClientInfo object from ALSA :alsa:`snd_seq_client_info_t`."""
        broadcast_filter = alsa.snd_seq_client_info_get_broadcast_filter(info)
        error_bounce = alsa.snd_seq_client_info_get_broadcast_filter(info)
        try:
            card_id = alsa.snd_seq_client_info_get_card(info)
            if card_id < 0:
                card_id = None
        except AttributeError:
            card_id = None
        try:
            pid = alsa.snd_seq_client_info_get_pid(info)
            if pid < 0:
                pid = None
        except AttributeError:
            pid = None
        name = ffi.string(alsa.snd_seq_client_info_get_name(info))

        # deprecated but seems the only way to check if there is a filter
        has_filter = bool(alsa.snd_seq_client_info_get_event_filter(info))
        if has_filter:
            event_filter = set()
            for e_type in EventType:
                if e_type == EventType.NONE:
                    continue
                if alsa.snd_seq_client_info_event_filter_check(info, e_type):
                    event_filter.add(e_type)
        else:
            event_filter = None
        return cls(
                client_id=alsa.snd_seq_client_info_get_client(info),
                name=name.decode(),
                broadcast_filter=(broadcast_filter == 1),
                error_bounce=error_bounce == 1,
                type=ClientType(alsa.snd_seq_client_info_get_type(info)),
                card_id=card_id,
                pid=pid,
                num_ports=alsa.snd_seq_client_info_get_num_ports(info),
                event_lost=alsa.snd_seq_client_info_get_event_lost(info),
                event_filter=event_filter,
                )

    def _to_alsa(self) -> _snd_seq_client_info_t:
        """Create a an ALSA :alsa:`snd_seq_client_info_t` object from self."""
        info_p = ffi.new("snd_seq_client_info_t **")
        err = alsa.snd_seq_client_info_malloc(info_p)
        _check_alsa_error(err)
        info = ffi.gc(info_p[0], alsa.snd_seq_client_info_free)
        alsa.snd_seq_client_info_set_client(info, self.client_id)
        alsa.snd_seq_client_info_set_name(info, self.name.encode())
        alsa.snd_seq_client_info_set_broadcast_filter(info, 1 if self.broadcast_filter else 0)
        alsa.snd_seq_client_info_set_error_bounce(info, 1 if self.error_bounce else 0)
        if self.event_filter:
            for e_type in self.event_filter:
                alsa.snd_seq_client_info_event_filter_add(info, e_type)
        else:
            alsa.snd_seq_client_info_event_filter_clear(info)
        return info


_snd_seq_system_info_t = NewType("_snd_seq_system_info_t", object)


class SystemInfo(namedtuple("SystemInfo", "queues clients ports channels cur_clients cur_queues")):
    """System information.

    Represents data from :alsa:`snd_seq_system_info_t`

    :ivar queues: maximum number of clients
    :ivar clients: maximum number of ports
    :ivar ports: maximum number of channels
    :ivar channels: maximum number of channels
    :ivar cur_clients: current number of clients
    :ivar cur_queues: current number of queues
    """
    queues: int
    clients: int
    ports: int
    channels: int
    cur_clients: int
    cur_queues: int

    __slots__ = ()

    @classmethod
    def _from_alsa(cls, info: _snd_seq_system_info_t):
        """Create a ClientInfo object from ALSA :alsa:`snd_seq_system_info_t`."""
        return cls(
                queues=alsa.snd_seq_system_info_get_queues(info),
                clients=alsa.snd_seq_system_info_get_clients(info),
                ports=alsa.snd_seq_system_info_get_ports(info),
                channels=alsa.snd_seq_system_info_get_channels(info),
                cur_clients=alsa.snd_seq_system_info_get_cur_clients(info),
                cur_queues=alsa.snd_seq_system_info_get_cur_queues(info),
                )


_snd_seq_query_subscribe_t = NewType("_snd_seq_query_subscribe_t", object)


class SubscriptionQueryType(IntEnum):
    READ = alsa.SND_SEQ_QUERY_SUBS_READ
    WRITE = alsa.SND_SEQ_QUERY_SUBS_WRITE


class SubscriptionQuery:
    """Port subscription (connection) information.

    Represents data from :alsa:`snd_seq_query_subscribe_t`

    :param root: address of the port queried
    :param type: either :data:`SubscriptionQueryType.READ` or :data:`SubscriptionQueryType.WRITE`
    :param index: subscription index inside query result
    :param num_subs: number of subscription in query result
    :param addr: address of the subscriber
    :param queue_id: queue id
    :param exclusive: exclusive access
    :param time_update: time update enabled
    :param time_real: user real time stamps

    :ivar root: address of the port queried
    :ivar type: either :data:`SubscriptionQueryType.READ` or :data:`SubscriptionQueryType.WRITE`
    :ivar index: subscription index inside query result
    :ivar num_subs: number of subscription in query result
    :ivar addr: address of the subscriber
    :ivar queue_id: queue id
    :ivar exclusive: exclusive access
    :ivar time_update: time update enabled
    :ivar time_real: user real time stamps
    """
    root: Address
    type: SubscriptionQueryType
    index: int
    num_subs: int
    addr: Address
    queue_id: int
    exclusive: bool
    time_update: bool
    time_real: bool

    def __init__(self,
                 root: AddressType,
                 type: SubscriptionQueryType,
                 *,
                 index: int = 0,
                 num_subs: int = 0,
                 addr: AddressType = (0, 0),
                 queue_id: int = 0,
                 exclusive: bool = False,
                 time_update: bool = False,
                 time_real: bool = False):

        self.root = Address(root)
        self.type = type
        self.index = index
        self.num_subs = num_subs
        self.addr = Address(addr)
        self.queue_id = queue_id
        self.exlusive = bool(exclusive)
        self.time_update = bool(time_update)
        self.time_real = bool(time_real)

    @classmethod
    def _from_alsa(cls, query: _snd_seq_query_subscribe_t):
        """Create a ClientInfo object from ALSA :alsa:`snd_seq_query_subscribe_t`."""
        a_root = alsa.snd_seq_query_subscribe_get_root(query)
        a_addr = alsa.snd_seq_query_subscribe_get_addr(query)
        return cls(
                root=Address(a_root.client, a_root.port),
                type=SubscriptionQueryType(alsa.snd_seq_query_subscribe_get_type(query)),
                index=alsa.snd_seq_query_subscribe_get_index(query),
                num_subs=alsa.snd_seq_query_subscribe_get_num_subs(query),
                addr=Address(a_addr.client, a_addr.port),
                queue_id=alsa.snd_seq_query_subscribe_get_queue(query),
                exclusive=alsa.snd_seq_query_subscribe_get_exclusive(query),
                time_update=alsa.snd_seq_query_subscribe_get_time_update(query),
                time_real=alsa.snd_seq_query_subscribe_get_time_real(query),
                )

    def _to_alsa(self) -> _snd_seq_query_subscribe_t:
        """Create a an ALSA :alsa:`snd_seq_query_subscribe_t` object from self."""
        query_p = ffi.new("snd_seq_query_subscribe_t **")
        err = alsa.snd_seq_query_subscribe_malloc(query_p)
        _check_alsa_error(err)
        query = ffi.gc(query_p[0], alsa.snd_seq_query_subscribe_free)
        alsa.snd_seq_query_subscribe_set_client(query, self.root.client_id)
        alsa.snd_seq_query_subscribe_set_port(query, self.root.port_id)
        alsa.snd_seq_query_subscribe_set_type(query, self.type)
        alsa.snd_seq_query_subscribe_set_index(query, self.index)
        return query


_snd_seq_client_pool_t = NewType("_snd_seq_client_pool_t", object)


class ClientPool:
    """Client kernel-side memory pool information.

    Represents data from :alsa:`snd_seq_client_pool_t`

    :ivar client_id: client id
    :ivar output_pool: output pool size
    :ivar input_pool: input pool size
    :ivar output_room: output pool room size
    :ivar output_free: amount of free space in the output pool
    :ivar input_free: amount of free space in the input pool
    """
    client_id: int
    output_pool: int
    input_pool: int
    output_room: int
    output_free: int
    input_free: int

    def __init__(self,
                 output_pool: int,
                 input_pool: int,
                 output_room: int,
                 *,
                 client_id: int = 0,
                 output_free: int = 0,
                 input_free: int = 0):

        self.client_id = client_id
        self.output_pool = output_pool
        self.input_pool = input_pool
        self.output_room = output_room
        self.output_free = output_free
        self.input_free = input_free

    @classmethod
    def _from_alsa(cls, pool: _snd_seq_client_pool_t):
        """Create a ClientInfo object from ALSA :alsa:`snd_seq_client_pool_t`."""
        return cls(
                client_id=alsa.snd_seq_client_pool_get_client(pool),
                output_pool=alsa.snd_seq_client_pool_get_output_pool(pool),
                input_pool=alsa.snd_seq_client_pool_get_input_pool(pool),
                output_room=alsa.snd_seq_client_pool_get_output_room(pool),
                output_free=alsa.snd_seq_client_pool_get_output_free(pool),
                input_free=alsa.snd_seq_client_pool_get_input_free(pool),
                )

    def _to_alsa(self) -> _snd_seq_client_pool_t:
        """Create a an ALSA :alsa:`snd_seq_client_pool_t` object from self."""
        pool_p = ffi.new("snd_seq_client_pool_t **")
        err = alsa.snd_seq_client_pool_malloc(pool_p)
        _check_alsa_error(err)
        pool = ffi.gc(pool_p[0], alsa.snd_seq_client_pool_free)
        alsa.snd_seq_client_pool_set_output_pool(pool, self.output_pool)
        alsa.snd_seq_client_pool_set_input_pool(pool, self.input_pool)
        alsa.snd_seq_client_pool_set_output_room(pool, self.output_room)
        return pool


class SequencerClientBase:
    """Base class for :class:`SequencerClient` and :class:`AsyncSequencerClient`.

    Constructor wraps :alsa:`snd_seq_open`.

    :param client_name: Client name
    :param streams: client streams open type
    :param mode: open mode (should be: :attr:`OpenMode.NONBLOCK`)

    :ivar client_id: ALSA client id
    :ivar handle: ALSA client handle (for use with the cffi bindings)
    """
    client_id: int
    handle: _snd_seq_t
    _handle_p: _snd_seq_t_p
    _fd: int = -1
    _event_parser: Optional[_snd_midi_event_t] = None

    def __init__(
            self,
            client_name: str,
            streams: int = StreamOpenType.DUPLEX,
            mode: int = OpenMode.NONBLOCK,
            sequencer_name: str = "default"):

        client_name_b = client_name.encode("utf-8")
        sequencer_name_b = sequencer_name.encode("utf-8")
        self._handle_p = ffi.new("snd_seq_t **", ffi.NULL)
        err = alsa.snd_seq_open(self._handle_p, sequencer_name_b, streams, mode)
        _check_alsa_error(err)
        self.handle = self._handle_p[0]
        alsa.snd_seq_set_client_name(self.handle, client_name_b)
        self.client_id = alsa.snd_seq_client_id(self.handle)
        self._get_fds()

    def __del__(self):
        try:
            self.close()
        except AttributeError:
            # not fully initialized
            pass

    def _check_handle(self):
        if self._handle_p is None:
            raise StateError("Already closed")

    def close(self):
        """Close the client connection and release any associated resources.

        The SequencerClient object won't be usable any more.

        Wraps :alsa:`snd_seq_close`.
        """
        if self._handle_p is None:
            return
        if self._handle_p[0] != ffi.NULL:
            alsa.snd_seq_close(self._handle_p[0])
        self._handle_p = None  # type: ignore
        self.handle = None  # type: ignore
        self._event_parser = None

    def _get_fds(self):
        """Get the file descriptor number for the client connection into :data:`self._fd`."""
        pfds_count = alsa.snd_seq_poll_descriptors_count(self.handle,
                                                         select.POLLIN | select.POLLOUT)
        # current ALSA does not use more than one fd
        # and if it would a lot of code would have to be more complicated
        assert pfds_count == 1
        pfds = ffi.new("struct pollfd[]", pfds_count)
        filled = alsa.snd_seq_poll_descriptors(self.handle, pfds, pfds_count,
                                               select.POLLIN | select.POLLOUT)
        assert filled == 1
        assert (pfds[0].events & select.POLLIN) and (pfds[0].events & select.POLLOUT)
        self._fd = pfds[0].fd

    def _get_event_parser(self):
        parser = self._event_parser
        if parser is None:
            parser_p = ffi.new("snd_midi_event_t **")
            err = alsa.snd_midi_event_new(1024, parser_p)
            _check_alsa_error(err)
            parser = ffi.gc(parser_p[0], alsa.snd_midi_event_free)
            alsa.snd_midi_event_no_status(parser, 1)
            self._event_parser = parser
        return parser

    def get_sequencer_name(self) -> str:
        """Get sequencer name.

        Wraps :alsa:`snd_seq_name`."""
        self._check_handle()
        return ffi.string(alsa.snd_seq_name(self.handle)).decode()

    def get_sequencer_type(self) -> SequencerType:
        """Get sequencer type.

        Wraps :alsa:`snd_seq_type`."""
        self._check_handle()
        result = alsa.snd_seq_type(self.handle)
        _check_alsa_error(result)
        return SequencerType(result)

    def get_output_buffer_size(self) -> int:
        """Get output buffer size.

        Wraps :alsa:`snd_seq_get_output_buffer_size`."""
        self._check_handle()
        return alsa.snd_seq_get_output_buffer_size(self.handle)

    def set_output_buffer_size(self, size: int):
        """Change output buffer size.

        :param size: the size of output buffer in bytes

        Wraps :alsa:`snd_seq_set_output_buffer_size`."""
        self._check_handle()
        err = alsa.snd_seq_set_output_buffer_size(self.handle, size)
        _check_alsa_error(err)

    def get_input_buffer_size(self) -> int:
        """Get input buffer size.

        Wraps :alsa:`snd_seq_get_input_buffer_size`."""
        self._check_handle()
        return alsa.snd_seq_get_input_buffer_size(self.handle)

    def set_input_buffer_size(self, size: int):
        """Change input buffer size.

        :param size: the size of input buffer in bytes

        Wraps :alsa:`snd_seq_set_input_buffer_size`."""
        self._check_handle()
        err = alsa.snd_seq_set_input_buffer_size(self.handle, size)
        _check_alsa_error(err)

    def create_port(self,
                    name: str,
                    caps: PortCaps = RW_PORT,
                    type: PortType = DEFAULT_PORT_TYPE,
                    *,
                    port_id: Optional[int] = None,
                    midi_channels: Optional[int] = None,
                    midi_voices: Optional[int] = None,
                    synth_voices: Optional[int] = None,
                    timestamping: Optional[bool] = None,
                    timestamp_real: Optional[bool] = None,
                    timestamp_queue: Optional[Union[Queue, int]] = None,
                    ) -> Port:
        """Create a sequencer port.

        Wraps :alsa:`snd_seq_create_port` or
        :alsa:`snd_seq_create_simple_port`.

        :param name: port name
        :param caps: port capability flags
        :param type: port type flags
        :param port_id: requested port id
        :param midi_channels: number of MIDI channels
        :param midi_voices: number of MIDI voices
        :param synth_voices: number of synth voices
        :param timestamping: request timestamping of incoming events
        :param timestamp_real: timestamp events with real time (otherwise MIDI
                               ticks are used)
        :param timestamp_queue: queue to use for timestamping

        :return: sequencer port created
        """
        self._check_handle()
        extra = [port_id, midi_channels, midi_voices, synth_voices,
                 timestamping, timestamp_real, timestamp_queue]
        if all(x is None for x in extra):
            port = alsa.snd_seq_create_simple_port(self.handle,
                                                   name.encode(),
                                                   caps, type)
        else:
            info_p = ffi.new("snd_seq_port_info_t **")
            err = alsa.snd_seq_port_info_malloc(info_p)
            _check_alsa_error(err)
            info = ffi.gc(info_p[0], alsa.snd_seq_port_info_free)
            alsa.snd_seq_port_info_set_name(info, name.encode())
            alsa.snd_seq_port_info_set_capability(info, caps)
            alsa.snd_seq_port_info_set_type(info, type)
            if port_id is not None:
                alsa.snd_seq_port_info_set_port(info, port_id)
                alsa.snd_seq_port_info_set_port_specified(info, 1)
            if midi_channels is not None:
                alsa.snd_seq_port_info_set_midi_channels(info, midi_channels)
            if midi_voices is not None:
                alsa.snd_seq_port_info_set_midi_voices(info, midi_voices)
            if synth_voices is not None:
                alsa.snd_seq_port_info_set_synth_voices(info, synth_voices)
            if timestamping is not None:
                alsa.snd_seq_port_info_set_timestamping(info, int(timestamping))
            if timestamp_real is not None:
                alsa.snd_seq_port_info_set_timestamp_real(info, int(timestamp_real))
            if timestamp_queue is not None:
                if isinstance(timestamp_queue, int):
                    queue_id = timestamp_queue
                else:
                    queue_id = timestamp_queue.queue_id
                alsa.snd_seq_port_info_set_timestamp_queue(info, queue_id)
            port = alsa.snd_seq_create_port(self.handle, info)
        _check_alsa_error(port)
        return Port(self, port)

    def create_queue(self, name: str = None) -> Queue:
        """Create a new queue.

        Wraps :alsa:`snd_seq_alloc_named_queue` or :alsa:`snd_seq_alloc_queue`.

        :param name: queue name

        :return: queue object created.
        """
        self._check_handle()
        if name is not None:
            queue = alsa.snd_seq_alloc_named_queue(self.handle, name.encode("utf-8"))
        else:
            queue = alsa.snd_seq_alloc_queue(self.handle)
        _check_alsa_error(queue)
        return Queue(self, queue)

    def drop_input(self):
        """Remove all incoming events in the input buffer and sequencer queue.

        Wraps :alsa:`snd_seq_drop_input`.
        """
        self._check_handle()
        err = alsa.snd_seq_drop_input(self.handle)
        _check_alsa_error(err)

    def drop_input_buffer(self):
        """Remove all incoming events in the input buffer.

        Wraps :alsa:`snd_seq_drop_input_buffer`.
        """
        self._check_handle()
        err = alsa.snd_seq_drop_input_buffer(self.handle)
        _check_alsa_error(err)

    def drain_output(self):
        """Send any outgoing events from the output buffer to the sequencer.

        Wraps :alsa:`snd_seq_drain_output`.
        """
        self._check_handle()
        err = alsa.snd_seq_drain_output(self.handle)
        _check_alsa_error(err)

    def drop_output(self):
        """Remove all events from the output buffer.

        Wraps :alsa:`snd_seq_drop_output`.
        """
        self._check_handle()
        err = alsa.snd_seq_drop_output(self.handle)
        _check_alsa_error(err)

    def _event_input(self, prefer_bytes: bool = False) -> Tuple[int, Optional[Event]]:
        buf = ffi.new("snd_seq_event_t**", ffi.NULL)
        result = alsa.snd_seq_event_input(self.handle, buf)
        if result < 0:
            return result, None
        alsa_event = buf[0]
        try:
            if prefer_bytes and alsa_event.type in MIDI_BYTES_EVENTS:
                parser = self._get_event_parser()
                if alsa_event.type == EventType.SYSEX:
                    buf_len = alsa_event.data.ext.len
                else:
                    buf_len = 12
                bytes_buf = ffi.new("char[]", buf_len)
                count = alsa.snd_midi_event_decode(parser, bytes_buf, buf_len, alsa_event)
                if count < 0:
                    return count, None
                event = MidiBytesEvent._from_alsa(alsa_event,
                                                  midi_bytes=ffi.buffer(bytes_buf, count))
                return result, event
            else:
                cls = Event._specialized.get(buf[0].type, Event)
                return result, cls._from_alsa(alsa_event)
        finally:
            alsa.snd_seq_free_event(alsa_event)

    def event_input(self, prefer_bytes: bool = False):
        """Receive an incoming event.

        When no event is available :class:`ALSAError` will be raised with `errnum` set to
        -\xa0:data:`errno.EAGAIN`.

        Wraps :alsa:`snd_seq_event_input` and :alsa:`snd_midi_event_decode` when `prefer_bytes` is
        `True`.

        :param prefer_bytes: set to `True` to return :class:`MidiBytesEvent` when possible.
        :param timeout: maximum time (in seconds) to wait for an event. Default: wait forever.

        :return: The event received or `None` if the timeout has been reached.
        """
        result, event = self._event_input(prefer_bytes=prefer_bytes)
        _check_alsa_error(result)
        return event

    def _prepare_event(self,
                       event: Event,
                       queue: Union['Queue', int] = None,
                       port: Union['Port', int] = None,
                       dest: AddressType = None,
                       remainder: Optional[Any] = None) -> Tuple[_snd_seq_event_t, Any]:
        """Prepare ALSA :alsa:`snd_seq_event_t` for given `event` object for output.

        For :class:`alsa_midi.MidiBytesEvent` may need to be called more than
        once, when multiple ALSA events need to be created for the byte
        sequence provided.

        :param event: the event
        :param queue: the queue to force the event to. Default: send directly, unless
                      :data:`event.queue` is set.
        :param port: the port to send the event from. Default: the one set in the `event`.
        :param dest: the destination. Default: all subscribers, unless :data:`event.dest` says
                     otherwise.
        :param remainder: remainder returned by the previous call to :meth:`_prepare_event` for the
                          same event.

        :return: :alsa:`snd_seq_event_t` object prepared and, if there are more
        ALSA events to be created from the `event`, the `reminder` value to be
        used in the next call to :meth:`_prepare_event`.
        """
        if not isinstance(event, MidiBytesEvent):
            alsa_event: _snd_seq_event_t = ffi.new("snd_seq_event_t *")
            event._to_alsa(alsa_event, queue=queue, port=port, dest=dest)
            return alsa_event, None

        if remainder is None:
            alsa_event: _snd_seq_event_t = ffi.new("snd_seq_event_t *")
            event._to_alsa(alsa_event, queue=queue, port=port, dest=dest)
            midi_bytes = event.midi_bytes
        else:
            alsa_event, midi_bytes = remainder

        parser = self._get_event_parser()

        length = len(midi_bytes)
        processed = alsa.snd_midi_event_encode(parser,
                                               ffi.from_buffer(midi_bytes),
                                               length,
                                               alsa_event)

        if processed < length:
            return alsa_event, (alsa_event, midi_bytes[processed:])
        else:
            return alsa_event, None

    def _event_output(self,
                      event: Event,
                      queue: Union['Queue', int] = None,
                      port: Union['Port', int] = None,
                      dest: AddressType = None,
                      remainder: Optional[Any] = None) -> Tuple[int, Any]:
        alsa_event, remainder = self._prepare_event(event,
                                                    queue=queue, port=port, dest=dest,
                                                    remainder=remainder)
        if alsa_event.type == EventType.NONE:
            return alsa.snd_seq_event_output_pending(self.handle), remainder
        result = alsa.snd_seq_event_output(self.handle, alsa_event)
        return result, remainder

    def event_output(self,
                     event: Event,
                     queue: Union['Queue', int] = None,
                     port: Union['Port', int] = None,
                     dest: AddressType = None) -> int:
        """Output an event.

        The event will be appended to the output buffer and sent only when the
        buffer is full. Use :meth:`drain_output` to force sending of the events buffered.

        May raise an :class:`ALSAError` when both the client-side and the kernel-side buffers are
        full.

        Wraps :alsa:`snd_seq_event_output`.

        :param event: the event to be sent
        :param queue: the queue to force the event to. Default: send directly, unless
                      :data:`event.queue` is set.
        :param port: the port to send the event from. Default: the one set in the `event`.
        :param dest: the destination. Default: all subscribers, unless :data:`event.dest` says
                     otherwise.

        :return: Number of bytes used in the output buffer.
        """
        self._check_handle()
        remainder = None
        while True:
            result, remainder = self._event_output(event, queue, port, dest, remainder=remainder)
            _check_alsa_error(result)
            if remainder is None:
                break
        return result

    def event_output_buffer(self,
                            event: Event,
                            queue: Union['Queue', int] = None,
                            port: Union['Port', int] = None,
                            dest: AddressType = None) -> int:
        """Output an event to a buffer.

        The event won't be sent, it will just be appended to the output buffer.

        The method never blocks, but may raise :exc:`ALSAError` with
        `errnum`\xa0=\xa0-\xa0:data:`errno.EAGAIN` when the buffer is full.

        Wraps :alsa:`snd_seq_event_output_buffer`.

        :param event: the event to be sent
        :param queue: the queue to force the event to. Default: send directly, unless
                      :data:`event.queue` is set.
        :param port: the port to send the event from. Default: the one set in the `event`.
        :param dest: the destination. Default: all subscribers, unless :data:`event.dest` says
                     otherwise.

        :return: Number of bytes used in the output buffer.
        """
        self._check_handle()
        remainder = None
        while True:
            alsa_event, remainder = self._prepare_event(event,
                                                        queue=queue, port=port, dest=dest,
                                                        remainder=remainder)
            if alsa_event.type == EventType.NONE:
                return alsa.snd_seq_event_output_pending(self.handle)
            result = alsa.snd_seq_event_output(self.handle, alsa_event)
            _check_alsa_error(result)
            if remainder is None:
                break
        return result

    def _event_output_direct(self,
                             event: Event,
                             queue: Union['Queue', int] = None,
                             port: Union['Port', int] = None,
                             dest: AddressType = None,
                             remainder: Optional[Any] = None) -> Tuple[int, Any]:
        alsa_event, remainder = self._prepare_event(event,
                                                    queue=queue, port=port, dest=dest,
                                                    remainder=remainder)
        if alsa_event.type == EventType.NONE:
            return alsa.snd_seq_event_output_pending(self.handle), remainder
        result = alsa.snd_seq_event_output(self.handle, alsa_event)
        return result, None

    def event_output_direct(self,
                            event: Event,
                            queue: Union['Queue', int] = None,
                            port: Union['Port', int] = None,
                            dest: AddressType = None) -> int:
        """Output an event directly to the sequencer.

        The event will be sent directly to the kernel and not stored in the local buffer.

        May raise an :class:`ALSAError` when the kernel-side buffers are full.

        Wraps :alsa:`snd_seq_event_output_direct`.

        :param event: the event to be sent
        :param queue: the queue to force the event to. Default: send directly, unless
                      :data:`event.queue` is set.
        :param port: the port to send the event from. Default: the one set in the `event`.
        :param dest: the destination. Default: all subscribers, unless :data:`event.dest` says
                     otherwise.

        :return: Number of bytes used in the output buffer.
        """
        self._check_handle()
        remainder = None
        while True:
            result, remainder = self._event_output_direct(event, queue, port, dest,
                                                          remainder=remainder)
            _check_alsa_error(result)
            if remainder is None:
                break
        return result

    def get_system_info(self) -> SystemInfo:
        """Obtain information about the sequencer.

        Wraps :alsa:`snd_seq_system_info`.

        :return: system information
        """
        info_p = ffi.new("snd_seq_system_info_t **")
        err = alsa.snd_seq_system_info_malloc(info_p)
        _check_alsa_error(err)
        info = ffi.gc(info_p[0], alsa.snd_seq_system_info_free)
        err = alsa.snd_seq_system_info(self.handle, info)
        _check_alsa_error(err)
        result = SystemInfo._from_alsa(info)
        return result

    def get_client_info(self, client_id: Optional[int] = None) -> ClientInfo:
        """Obtain information about a client.

        Wraps :alsa:`snd_seq_get_client_info` or :alsa:`snd_seq_get_any_client_info`.

        :param client_id: client to get information about. Default: self.

        :return: client information
        """
        info_p = ffi.new("snd_seq_client_info_t **")
        err = alsa.snd_seq_client_info_malloc(info_p)
        _check_alsa_error(err)
        info = ffi.gc(info_p[0], alsa.snd_seq_client_info_free)
        if client_id is None:
            err = alsa.snd_seq_get_client_info(self.handle, info)
        else:
            err = alsa.snd_seq_get_any_client_info(self.handle, client_id, info)
        _check_alsa_error(err)
        result = ClientInfo._from_alsa(info)
        return result

    def set_client_info(self, info: ClientInfo):
        """Set client information including event filter.

        Wraps :alsa:`snd_seq_set_client_info`.

        :param info: new client info
        """
        self._check_handle()
        a_info = info._to_alsa()
        err = alsa.snd_seq_set_client_info(self.handle, a_info)
        _check_alsa_error(err)

    def set_client_event_filter(self, event_type: EventType):
        """Add an event to client's event filter.

        Wraps :alsa:`snd_seq_set_client_event_filter`.

        :param event_type: event type to accept
        """
        self._check_handle()
        err = alsa.snd_seq_set_client_event_filter(self.handle, int(event_type))
        _check_alsa_error(err)

    @overload
    def query_next_client(self, previous: ClientInfo) -> Optional[ClientInfo]:
        ...

    @overload
    def query_next_client(self, previous: Optional[int] = None) -> Optional[ClientInfo]:
        ...

    def query_next_client(self, previous: Optional[Union[ClientInfo, int]] = None
                          ) -> Optional[ClientInfo]:
        """Obtain information about the first or the next sequencer client.

        Wraps :alsa:`snd_seq_query_next_client`.

        :param previous: previous client id or info object, `None` to query the first one

        :return: client information of `None` if there are no more clients
        """
        self._check_handle()
        if isinstance(previous, ClientInfo):
            info = previous._to_alsa()
        else:
            info_p = ffi.new("snd_seq_client_info_t **")
            err = alsa.snd_seq_client_info_malloc(info_p)
            _check_alsa_error(err)
            info = ffi.gc(info_p[0], alsa.snd_seq_client_info_free)
            alsa.snd_seq_client_info_set_client(info, -1 if previous is None else previous)
        err = alsa.snd_seq_query_next_client(self.handle, info)
        if err == -errno.ENOENT:
            return None
        _check_alsa_error(err)
        result = ClientInfo._from_alsa(info)
        return result

    def get_port_info(self, port: Union[int, AddressType]) -> PortInfo:
        """Obtain information about a specific port.

        Wraps :alsa:`snd_seq_get_port_info` or :alsa:`snd_seq_get_any_port_info`.

        :param port: port to get information about

        :return: port information
        """
        if isinstance(port, int):
            client_id = self.client_id
            port_id = port
        else:
            client_id, port_id = Address(port)
        info_p = ffi.new("snd_seq_port_info_t **")
        err = alsa.snd_seq_port_info_malloc(info_p)
        _check_alsa_error(err)
        info = ffi.gc(info_p[0], alsa.snd_seq_port_info_free)
        if client_id == self.client_id:
            err = alsa.snd_seq_get_port_info(self.handle, port_id, info)
        else:
            err = alsa.snd_seq_get_any_port_info(self.handle, client_id, port_id, info)
        _check_alsa_error(err)
        result = PortInfo._from_alsa(info)
        return result

    def set_port_info(self, port: Union[int, Port], info: PortInfo):
        """Set information about a specific own port.

        Wraps :alsa:`snd_seq_set_port_info`.

        :return: port information
        """
        if isinstance(port, int):
            port_id = port
        else:
            port_id = port.port_id
        alsa_info = info._to_alsa()
        err = alsa.snd_seq_set_port_info(self.handle, port_id, alsa_info)
        _check_alsa_error(err)

    @overload
    def query_next_port(self, client_id: int, previous: PortInfo
                        ) -> Optional[PortInfo]:
        ...

    @overload
    def query_next_port(self, client_id: int, previous: Optional[int] = None
                        ) -> Optional[PortInfo]:
        ...

    def query_next_port(self,
                        client_id: int,
                        previous: Optional[Union[PortInfo, int]] = None
                        ) -> Optional[PortInfo]:
        """Obtain information about the first or the next port of a sequencer client.

        Wraps :alsa:`snd_seq_query_next_port`.

        :param client_id: client id
        :param previous: previous client id or info object, `None` to query the first one

        :return: client information of `None` if there are no more ports
        """

        self._check_handle()
        if isinstance(previous, PortInfo):
            if not previous.client_id == client_id:
                raise ValueError("client_id mismatch")
            info = previous._to_alsa()
        else:
            info_p = ffi.new("snd_seq_port_info_t **")
            err = alsa.snd_seq_port_info_malloc(info_p)
            _check_alsa_error(err)
            info = ffi.gc(info_p[0], alsa.snd_seq_port_info_free)
            alsa.snd_seq_port_info_set_client(info, client_id)
            alsa.snd_seq_port_info_set_port(info, -1 if previous is None else previous)
        err = alsa.snd_seq_query_next_port(self.handle, info)
        if err == -errno.ENOENT:
            return None
        _check_alsa_error(err)
        result = PortInfo._from_alsa(info)
        return result

    def list_ports(self, *,
                   input: bool = None,
                   output: bool = None,
                   type: PortType = PortType.MIDI_GENERIC,
                   include_system: bool = False,
                   include_midi_through: bool = True,
                   include_no_export: bool = True,
                   only_connectable: bool = True,
                   sort: Union[bool, Callable[[PortInfo], Any]] = True,
                   ) -> List[PortInfo]:
        """More friendly interface to list available ports.

        Queries ALSA for all clients and ports and returns those matching the selected criteria.

        The result is sorted in a way that the first returned entry should be the 'most usable'
        one for the selected purpose. E.g. when `output` = `True` then the first entry will be
        a synthesizer input port rather than the dummy 'Midi Through' port. This is still a guess,
        though, so in the end the user should be able to choose.

        Wraps :alsa:`snd_seq_query_next_client` and :alsa:`snd_seq_query_next_port`.

        :param input: return ports usable for event input (`PortCaps.READ`)
        :param output: return ports usable for event output (`PortCaps.WRITE`)
        :param type: limit ouput to ports of this type
        :param include_system: include system ports
        :param include_midi_through: include 'midi through' ports
        :param include_no_export: include 'no export' ports
        :param only_connectable: only list ports that can be connected to/from
        :param sort: output sorting. `True` to for default algorithm, `False` to disable sorting
                     (return in ALSA identifiers order) or callable for custom sort key.

        :return: list of port information
        """

        result = []
        self._check_handle()

        client_ainfo_p = ffi.new("snd_seq_client_info_t **")
        err = alsa.snd_seq_client_info_malloc(client_ainfo_p)
        _check_alsa_error(err)
        client_ainfo = ffi.gc(client_ainfo_p[0], alsa.snd_seq_client_info_free)
        port_ainfo_p = ffi.new("snd_seq_port_info_t **")
        err = alsa.snd_seq_port_info_malloc(port_ainfo_p)
        _check_alsa_error(err)
        port_ainfo = ffi.gc(port_ainfo_p[0], alsa.snd_seq_port_info_free)

        alsa.snd_seq_client_info_set_client(client_ainfo, -1)
        while True:
            err = alsa.snd_seq_query_next_client(self.handle, client_ainfo)
            if err == -errno.ENOENT:
                break
            _check_alsa_error(err)

            client_id = alsa.snd_seq_client_info_get_client(client_ainfo)
            if client_id == 0 and not include_system:
                continue

            client_name = alsa.snd_seq_client_info_get_name(client_ainfo)
            client_name = ffi.string(client_name).decode()

            if client_name == "Midi Through" and not include_midi_through:
                continue

            alsa.snd_seq_port_info_set_client(port_ainfo, client_id)
            alsa.snd_seq_port_info_set_port(port_ainfo, -1)
            while True:
                err = alsa.snd_seq_query_next_port(self.handle, port_ainfo)
                if err == -errno.ENOENT:
                    break
                _check_alsa_error(err)

                port_info = PortInfo._from_alsa(port_ainfo)

                if type and (port_info.type & type) != type:
                    continue

                if port_info.capability & PortCaps.NO_EXPORT \
                        and not include_no_export:
                    continue

                can_write = port_info.capability & PortCaps.WRITE
                can_sub_write = port_info.capability & PortCaps.SUBS_WRITE
                can_read = port_info.capability & PortCaps.READ
                can_sub_read = port_info.capability & PortCaps.SUBS_READ

                if output:
                    if not can_write:
                        continue
                    if only_connectable and not can_sub_write:
                        continue

                if input:
                    if not can_read:
                        continue
                    if only_connectable and not can_sub_read:
                        continue

                if not input and not output:
                    if only_connectable:
                        if can_read and can_sub_read:
                            pass
                        elif can_write and can_sub_write:
                            pass
                        else:
                            continue
                    elif not can_read and not can_write:
                        continue

                port_info.client_name = client_name
                result.append(port_info)

        if callable(sort):
            sort_key = sort
        elif sort:
            if input and not output:
                sort_key = get_port_info_sort_key(READ_PORT_PREFERRED_TYPES)
            if output and not input:
                sort_key = get_port_info_sort_key(WRITE_PORT_PREFERRED_TYPES)
            else:
                sort_key = get_port_info_sort_key(RW_PORT_PREFERRED_TYPES)
        else:
            sort_key = None

        if sort_key is not None:
            result.sort(key=sort_key)

        return result

    def _subunsub_port(self, func,
                       sender: AddressType, dest: AddressType, *,
                       queue: Optional[Union[Queue, int]] = None,
                       exclusive: bool = False,
                       time_update: bool = False,
                       time_real: bool = False):
        sender = Address(sender)
        dest = Address(dest)
        if queue is None or isinstance(queue, int):
            queue_id = queue
        else:
            queue_id = queue.queue_id
        sub_p = ffi.new("snd_seq_port_subscribe_t **")
        err = alsa.snd_seq_port_subscribe_malloc(sub_p)
        _check_alsa_error(err)
        sub = ffi.gc(sub_p[0], alsa.snd_seq_port_subscribe_free)
        addr = ffi.new("snd_seq_addr_t *")
        addr.client, addr.port = sender.client_id, sender.port_id
        alsa.snd_seq_port_subscribe_set_sender(sub, addr)
        addr.client, addr.port = dest.client_id, dest.port_id
        alsa.snd_seq_port_subscribe_set_dest(sub, addr)
        if queue_id is not None:
            alsa.snd_seq_port_subscribe_set_queue(sub, queue_id)
        alsa.snd_seq_port_subscribe_set_exclusive(sub, int(exclusive))
        alsa.snd_seq_port_subscribe_set_time_update(sub, int(time_update))
        alsa.snd_seq_port_subscribe_set_time_real(sub, int(time_real))
        err = func(self.handle, sub)
        _check_alsa_error(err)

    def subscribe_port(self, sender: AddressType, dest: AddressType, *,
                       queue: Optional[Union[Queue, int]] = None,
                       exclusive: bool = False,
                       time_update: bool = False,
                       time_real: bool = False):
        """Connect two ALSA ports.

        Wraps :alsa:`snd_seq_subscribe_port`.

        :param sender: source port address
        :param dest: destination port adddress
        :param exclusive: set up an exclusive connection
        :param queue: queue to use for time stamping
        :param time_update: enable time stamp updates
        :param time_real: use real time instead of MIDI ticks for time stamps
        """
        self._check_handle()
        return self._subunsub_port(alsa.snd_seq_subscribe_port,
                                   sender, dest,
                                   queue=queue,
                                   exclusive=exclusive,
                                   time_update=time_update,
                                   time_real=time_real)

    def unsubscribe_port(self, sender: AddressType, dest: AddressType):
        """Disconnect two ALSA ports.

        Wraps :alsa:`snd_seq_unsubscribe_port`.

        :param sender: source port address
        :param dest: destination port adddress
        """
        self._check_handle()
        return self._subunsub_port(alsa.snd_seq_unsubscribe_port,
                                   sender, dest)

    def query_port_subscribers(self,
                               query: SubscriptionQuery
                               ) -> SubscriptionQuery:
        """Queries the subscribers subscribers to a port.

        At least, the client id, the port id, the index number and the query
        type must be set in to perform a proper query. As the query type,
        :data:`SubscriptionQueryType.READ` or
        :data:`SubscriptionQueryType.WRITE` can be specified to check whether
        the readers or the writers to the port. To query the first
        subscription, set 0 to the index number. To list up all the
        subscriptions, call this method with the index numbers from 0 until
        this raises :class:`ALSAError`. Or use :meth:`list_port_subscribers()`
        instead.

        Wraps :alsa:`snd_seq_query_port_subscribers`.

        :param query: Query parameters
        """
        self._check_handle()
        a_query = query._to_alsa()
        err = alsa.snd_seq_query_port_subscribers(self.handle, a_query)
        _check_alsa_error(err)
        result = SubscriptionQuery._from_alsa(a_query)
        return result

    def list_port_subscribers(self,
                              port: AddressType,
                              type: Optional[SubscriptionQueryType] = None,
                              ) -> List[SubscriptionQuery]:
        """Lists subscribers accessing a port.

        Wraps :alsa:`snd_seq_query_port_subscribers`.

        :param port: Port address to query
        :param type: limit query to the specific type
        """
        if type is None:
            types = [SubscriptionQueryType.READ, SubscriptionQueryType.WRITE]
        else:
            types = [type]

        self._check_handle()
        query_p = ffi.new("snd_seq_query_subscribe_t **")
        err = alsa.snd_seq_query_subscribe_malloc(query_p)
        _check_alsa_error(err)
        query = ffi.gc(query_p[0], alsa.snd_seq_query_subscribe_free)

        client_id, port_id = Address(port)

        result = []

        for type in types:
            alsa.snd_seq_query_subscribe_set_client(query, client_id)
            alsa.snd_seq_query_subscribe_set_port(query, port_id)
            alsa.snd_seq_query_subscribe_set_type(query, type)
            i = 0
            while True:
                alsa.snd_seq_query_subscribe_set_index(query, i)
                err = alsa.snd_seq_query_port_subscribers(self.handle, query)
                if err < 0:
                    break
                result.append(SubscriptionQuery._from_alsa(query))
                i += 1
        return result

    def get_client_pool(self) -> ClientPool:
        """Obtain the pool information of the client.

        Wraps :alsa:`snd_seq_get_client_pool`.
        """
        self._check_handle()
        pool_p = ffi.new("snd_seq_client_pool_t **")
        err = alsa.snd_seq_client_pool_malloc(pool_p)
        _check_alsa_error(err)
        a_pool = ffi.gc(pool_p[0], alsa.snd_seq_client_pool_free)
        err = alsa.snd_seq_get_client_pool(self.handle, a_pool)
        _check_alsa_error(err)
        return ClientPool._from_alsa(a_pool)

    def set_client_pool(self, pool: ClientPool):
        """Change pool settings of the client.

        :param pool: new pool settings

        Wraps :alsa:`snd_seq_set_client_pool`.
        """
        self._check_handle()
        a_pool = pool._to_alsa()
        err = alsa.snd_seq_set_client_pool(self.handle, a_pool)
        _check_alsa_error(err)

    def set_client_pool_output(self, size: int):
        """Change output pool size for the client.

        :param size: requested pool size

        Wraps :alsa:`snd_seq_set_client_pool_output`
        """
        err = alsa.snd_seq_set_client_pool_output(self.handle, size)
        _check_alsa_error(err)

    def set_client_pool_output_room(self, size: int):
        """Change output pool room size for the client.

        :param size: requested room size

        Wraps :alsa:`snd_seq_set_client_pool_output_room`
        """
        err = alsa.snd_seq_set_client_pool_output_room(self.handle, size)
        _check_alsa_error(err)

    def set_client_pool_input(self, size: int):
        """Change input pool size for the client.

        :param size: requested pool size

        Wraps :alsa:`snd_seq_set_client_pool_input`
        """
        err = alsa.snd_seq_set_client_pool_input(self.handle, size)
        _check_alsa_error(err)


class SequencerClient(SequencerClientBase):
    """ALSA sequencer client connection.

    This is the main interface to interact with the sequencer.  Provides
    synchronous (blocking) event I/O.

    :param client_name: client name for the connection
    :param kwargs: arguments for the `SequencerClientBase` constructor
    """

    def __init__(self, client_name: str, **kwargs):
        if "mode" in kwargs and not kwargs["mode"] & OpenMode.NONBLOCK:
            raise ValueError("NONBLOCK open mode must be used")
        super().__init__(client_name, **kwargs)
        self._read_poll = select.poll()
        self._read_poll.register(self._fd, select.POLLIN)
        self._write_poll = select.poll()
        self._write_poll.register(self._fd, select.POLLOUT)

    def event_input(self, prefer_bytes: bool = False, timeout: Optional[float] = None
                    ) -> Optional[Event]:
        """Wait for and receive an incoming event.

        Wraps :alsa:`snd_seq_event_input` and :alsa:`snd_midi_event_decode` when `prefer_bytes` is
        `True`.

        :param prefer_bytes: set to `True` to return :class:`MidiBytesEvent` when possible.
        :param timeout: maximum time (in seconds) to wait for an event. Default: wait forever.

        :return: The event received or `None` if the timeout has been reached.
        """
        if timeout:
            until = time.monotonic() + timeout
        else:
            until = None

        while True:
            result, event = self._event_input(prefer_bytes=prefer_bytes)
            if result != -errno.EAGAIN:
                break
            if until is not None:
                remaining = until - time.monotonic()
                if remaining <= 0:
                    return None
            else:
                remaining = None
            self._read_poll.poll(remaining)

        _check_alsa_error(result)
        return event

    @overload
    def _event_output_wait(self, func) -> int:
        ...

    @overload
    def _event_output_wait(self, func, timeout: float) -> Union[int, None]:
        ...

    def _event_output_wait(self, func, timeout: Optional[float] = None) -> Union[int, None]:
        if timeout:
            until = time.monotonic() + timeout
        else:
            until = None

        remainder = None

        while True:
            result, remainder = func(remainder=remainder)
            if result != -errno.EAGAIN and remainder is None:
                break
            if until is not None:
                remaining = until - time.monotonic()
                if remaining <= 0:
                    return None
            else:
                remaining = None
            self._write_poll.poll(remaining)
        _check_alsa_error(result)
        return result

    def drain_output(self) -> int:
        """Send events in the output queue to the sequencer.

        May block when the kernel-side buffer is full.

        Wraps :alsa:`snd_seq_drain_output`.

        :return: Number of bytes remaining in the buffer.
        """

        self._check_handle()

        def func(remainder=None):
            _ = remainder
            return alsa.snd_seq_drain_output(self.handle), None

        return self._event_output_wait(func)

    def event_output(self,
                     event: Event,
                     queue: Union['Queue', int] = None,
                     port: Union['Port', int] = None,
                     dest: AddressType = None) -> int:
        """Output an event.

        The event will be appended to the output buffer and sent only when the
        buffer is full. Use :meth:`drain_output` to force sending of the events buffered.

        May block when both the client-side and the kernel-side buffers are full.

        Wraps :alsa:`snd_seq_event_output`.

        :param event: the event to be sent
        :param queue: the queue to force the event to. Default: send directly, unless
                      :data:`event.queue` is set.
        :param port: the port to send the event from. Default: the one set in the `event`.
        :param dest: the destination. Default: all subscribers, unless :data:`event.dest` says
                     otherwise.

        :return: Number of bytes used in the output buffer.
        """
        self._check_handle()
        func = partial(self._event_output, event, queue, port, dest)
        return self._event_output_wait(func)

    def event_output_direct(self,
                            event: Event,
                            queue: Union['Queue', int] = None,
                            port: Union['Port', int] = None,
                            dest: AddressType = None) -> int:
        """Output an event without buffering.

        The event will be sent immediately. The function may block when the
        kernel-side buffer is full.

        Wraps :alsa:`snd_seq_event_output_direct`.

        :param event: the event to be sent
        :param queue: the queue to force the event to. Default: send directly,
                      unless :data:`event.queue` is set.
        :param port: the port to send the event from. Default: the one set in the `event`.
        :param dest: the destination. Default: all subscribers, unless :data:`event.dest` says
                     otherwise.

        :return: Number of bytes sent to the sequencer.
        """
        self._check_handle()
        func = partial(self._event_output_direct, event, queue, port, dest)
        return self._event_output_wait(func)


class AsyncSequencerClient(SequencerClientBase):
    """ALSA sequencer client connection (async API).

    This is the other main interface to interact with the sequencer. Provides
    asynchronous (asyncio) event I/O.

    Mostly the same as :class:`SequencerClient`, but a few methods are
    coroutines here.

    :param client_name: client name for the connection
    :param kwargs: arguments for the `SequencerClientBase` constructor
    """

    def __init__(self, *args, **kwargs):
        if "mode" in kwargs and not kwargs["mode"] & OpenMode.NONBLOCK:
            raise ValueError("NONBLOCK open mode must be used")
        super().__init__(*args, **kwargs)

    async def aclose(self):
        """Close the client connection and release any associated resources.

        The SequencerClient object won't be usable any more.

        Currently the same as :meth:`close`.
        """
        self.close()

    async def event_input(self, prefer_bytes: bool = False, timeout: Optional[float] = None
                          ) -> Optional[Event]:
        """Wait for and receive an incoming event.

        Wraps :alsa:`snd_seq_event_input` and alsa:`snd_midi_event_decode` when `prefer_bytes` is
        `True`.

        :param prefer_bytes: set to `True` to return :class:`MidiBytesEvent` when possible.
        :param timeout: maximum time (in seconds) to wait for an event. Default: wait forever.

        :return: The event received or `None` if the timeout has been reached.
        """
        result, event = self._event_input(prefer_bytes=prefer_bytes)
        if result != -errno.EAGAIN:
            _check_alsa_error(result)
            return event

        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        fd = self._fd

        def reader_cb():
            result = None
            try:
                result, event = self._event_input(prefer_bytes=prefer_bytes)
            except Exception as err:
                fut.set_exception(err)
                return
            finally:
                if result != -errno.EAGAIN:
                    loop.remove_reader(fd)
            if result != -errno.EAGAIN:
                fut.set_result((result, event))

        loop.add_reader(fd, reader_cb)

        if timeout:
            try:
                result, event = await asyncio.wait_for(fut, timeout)
            except asyncio.TimeoutError:
                return None
        else:
            result, event = await fut
        _check_alsa_error(result)
        return event

    @overload
    async def _event_output_wait(self, func) -> int:
        ...

    @overload
    async def _event_output_wait(self, func, timeout: float) -> Union[int, None]:
        ...

    async def _event_output_wait(self, func, timeout: Optional[float] = None) -> Union[int, None]:
        result, remainder = func()
        if result != -errno.EAGAIN and remainder is None:
            _check_alsa_error(result)
            return result

        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        fd = self._fd

        def writer_cb():
            nonlocal remainder
            result = None
            try:
                result, remainder = func(remainder=remainder)
            except Exception as err:
                fut.set_exception(err)
                return
            finally:
                if result != -errno.EAGAIN and remainder is None:
                    loop.remove_reader(fd)
            if result != -errno.EAGAIN and remainder is None:
                fut.set_result(result)

        loop.add_reader(fd, writer_cb)

        if timeout:
            try:
                result = await asyncio.wait_for(fut, timeout)
            except asyncio.TimeoutError:
                return None
        else:
            result = await fut
        _check_alsa_error(result)
        return result

    async def drain_output(self) -> int:
        """Send events in the output queue to the sequencer.

        May block when the kernel-side buffer is full.

        Wraps :alsa:`snd_seq_drain_output`.

        :return: Number of bytes remaining in the buffer.
        """

        self._check_handle()

        def func(remainder=None):
            _ = remainder
            return alsa.snd_seq_drain_output(self.handle), None

        return await self._event_output_wait(func)

    async def event_output(self,
                           event: Event,
                           queue: Union['Queue', int] = None,
                           port: Union['Port', int] = None,
                           dest: AddressType = None) -> int:
        """Output an event.

        The event will be appended to the output buffer and sent only when the
        buffer is full. Use :meth:`drain_output` to force sending of the events buffered.

        May block when both the client-side and the kernel-side buffers are full.

        Wraps :alsa:`snd_seq_event_output`.

        :param event: the event to be sent
        :param queue: the queue to force the event to. Default: send directly,
                      unless :data:`event.queue` is set.
        :param port: the port to send the event from. Default: the one set in the `event`.
        :param dest: the destination. Default: all subscribers, unless
                     :data:`event.dest` says otherwise.

        :return: Number of bytes used in the output buffer.
        """
        self._check_handle()
        func = partial(self._event_output, event, queue, port, dest)
        return await self._event_output_wait(func)

    async def event_output_direct(self,
                                  event: Event,
                                  queue: Union['Queue', int] = None,
                                  port: Union['Port', int] = None,
                                  dest: AddressType = None) -> int:
        """Output an event without buffering.

        The event will be sent immediately. The function may block when the
        kernel-side buffer is full.

        Wraps :alsa:`snd_seq_event_output_direct`.

        :param event: the event to be sent
        :param queue: the queue to force the event to. Default: send directly,
                      unless :data:`event.queue` is set.
        :param port: the port to send the event from. Default: the one set in
                     the `event`.
        :param dest: the destination. Default: all subscribers, unless
                     :data:`event.dest` says otherwise.

        :return: Number of bytes sent to the sequencer.
        """
        self._check_handle()
        func = partial(self._event_output_direct, event, queue, port, dest)
        return await self._event_output_wait(func)


__all__ = ["SequencerClientBase", "SequencerClient", "ClientInfo", "ClientType", "SequencerType",
           "SystemInfo", "SubscriptionQueryType", "SubscriptionQuery", "ClientPool"]
