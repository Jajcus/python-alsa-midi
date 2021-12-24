
import asyncio
import errno
import select
import time
from enum import IntEnum, IntFlag
from functools import partial
from typing import Any, Awaitable, Callable, List, NewType, Optional, Tuple, Union, overload

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
    OUTPUT = alsa.SND_SEQ_OPEN_OUTPUT
    INPUT = alsa.SND_SEQ_OPEN_INPUT
    DUPLEX = alsa.SND_SEQ_OPEN_DUPLEX


class OpenMode(IntFlag):
    NONBLOCK = alsa.SND_SEQ_NONBLOCK


class ClientType(IntEnum):
    _UNSET = 0
    USER = alsa.SND_SEQ_USER_CLIENT
    KERNEL = alsa.SND_SEQ_KERNEL_CLIENT


_snd_seq_client_info_t = NewType("_snd_seq_client_info_t", object)


class ClientInfo:
    client_id: int
    name: str
    broadcast_filter: bool
    error_bounce: bool
    type: Optional[ClientType]
    card_id: Optional[int]
    pid: Optional[int]
    num_ports: int
    event_lost: int

    def __init__(self,
                 client_id: int,
                 name: str,
                 broadcast_filter: bool = False,
                 error_bounce: bool = False,
                 type: ClientType = None,
                 card_id: Optional[int] = None,
                 pid: Optional[int] = None,
                 num_ports: int = 0,
                 event_lost: int = 0):
        self.client_id = client_id
        self.name = name
        self.broadcast_filter = broadcast_filter
        self.error_bounce = error_bounce
        self.type = type
        self.card_id = card_id
        self.pid = pid
        self.num_ports = num_ports
        self.event_lost = event_lost

    @classmethod
    def _from_alsa(cls, info: _snd_seq_client_info_t):
        broadcast_filter = alsa.snd_seq_client_info_get_broadcast_filter(info)
        error_bounce = alsa.snd_seq_client_info_get_broadcast_filter(info)
        card_id = alsa.snd_seq_client_info_get_card(info)
        pid = alsa.snd_seq_client_info_get_pid(info)
        name = ffi.string(alsa.snd_seq_client_info_get_name(info))
        return cls(
                client_id=alsa.snd_seq_client_info_get_client(info),
                name=name.decode(),
                broadcast_filter=(broadcast_filter == 1),
                error_bounce=error_bounce == 1,
                type=ClientType(alsa.snd_seq_client_info_get_type(info)),
                card_id=(card_id if card_id >= 0 else None),
                pid=(pid if pid > 0 else None),
                num_ports=alsa.snd_seq_client_info_get_num_ports(info),
                event_lost=alsa.snd_seq_client_info_get_event_lost(info),
                )

    def _to_alsa(self) -> _snd_seq_client_info_t:
        info_p = ffi.new("snd_seq_client_info_t **")
        err = alsa.snd_seq_client_info_malloc(info_p)
        _check_alsa_error(err)
        info = ffi.gc(info_p[0], alsa.snd_seq_client_info_free)
        alsa.snd_seq_client_info_set_client(info, self.client_id)
        alsa.snd_seq_client_info_set_name(info, self.name.encode())
        alsa.snd_seq_client_info_set_broadcast_filter(info, 1 if self.broadcast_filter else 0)
        alsa.snd_seq_client_info_set_error_bounce(info, 1 if self.error_bounce else 0)
        return info


class SequencerClientBase:
    """Base class for :class:`SequencerClient` and :class:`AsyncSequencerClient`.
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
        if self._handle_p is None:
            return
        if self._handle_p[0] != ffi.NULL:
            alsa.snd_seq_close(self._handle_p[0])
        self._handle_p = None  # type: ignore
        self.handle = None  # type: ignore

    def _get_fds(self):
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
            self._event_parser = parser
        return parser

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
        self._check_handle()
        if name is not None:
            queue = alsa.snd_seq_alloc_named_queue(self.handle, name.encode("utf-8"))
        else:
            queue = alsa.snd_seq_alloc_queue(self.handle)
        _check_alsa_error(queue)
        return Queue(self, queue)

    def drop_input(self):
        self._check_handle()
        err = alsa.snd_seq_drop_input(self.handle)
        _check_alsa_error(err)

    def drop_buffer(self):
        self._check_handle()
        err = alsa.snd_seq_drop_input_buffer(self.handle)
        _check_alsa_error(err)

    def drain_output(self):
        self._check_handle()
        err = alsa.snd_seq_drain_output(self.handle)
        _check_alsa_error(err)

    def drop_output(self):
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
        result, event = self._event_input(prefer_bytes=prefer_bytes)
        _check_alsa_error(result)
        return event

    def _prepare_event(self,
                       event: Event,
                       queue: Union['Queue', int] = None,
                       port: Union['Port', int] = None,
                       dest: AddressType = None,
                       remainder: Optional[Any] = None) -> Tuple[_snd_seq_event_t, Any]:

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
        :attr:`ALSAError.errnum` = - :data:`errno.EAGAIN` when the buffer is full.

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
        self._check_handle()
        remainder = None
        while True:
            result, remainder = self._event_output_direct(event, queue, port, dest,
                                                          remainder=remainder)
            _check_alsa_error(result)
            if remainder is None:
                break
        return result

    @overload
    def query_next_client(self, previous: ClientInfo) -> Optional[ClientInfo]:
        ...

    @overload
    def query_next_client(self, previous: Optional[int] = None) -> Optional[ClientInfo]:
        ...

    def query_next_client(self, previous: Optional[Union[ClientInfo, int]] = None
                          ) -> Optional[ClientInfo]:
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
        self._check_handle()
        return self._subunsub_port(alsa.snd_seq_subscribe_port,
                                   sender, dest,
                                   queue=queue,
                                   exclusive=exclusive,
                                   time_update=time_update,
                                   time_real=time_real)

    def unsubscribe_port(self, sender: AddressType, dest: AddressType, *,
                         queue: Optional[Union[Queue, int]] = None,
                         exclusive: bool = False,
                         time_update: bool = False,
                         time_real: bool = False):
        self._check_handle()
        return self._subunsub_port(alsa.snd_seq_unsubscribe_port,
                                   sender, dest,
                                   queue=queue,
                                   exclusive=exclusive,
                                   time_update=time_update,
                                   time_real=time_real)


class SequencerClient(SequencerClientBase):
    """ALSA sequencer client connection.

    This is the main interface to interact with the sequencer.  Provides
    synchronous (blocking) event I/O.

    :param client_name: client name for the connection
    """

    def __init__(self, client_name: str, *args, **kwargs):
        if "mode" in kwargs and not kwargs["mode"] & OpenMode.NONBLOCK:
            raise ValueError("NONBLOCK open mode must be used")
        super().__init__(client_name, *args, **kwargs)
        self._read_poll = select.poll()
        self._read_poll.register(self._fd, select.POLLIN)
        self._write_poll = select.poll()
        self._write_poll.register(self._fd, select.POLLOUT)

    def event_input(self, prefer_bytes: bool = False, timeout: Optional[float] = None
                    ) -> Optional[Event]:
        """Wait for and receive an incoming event.

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

        :return: Number of bytes sent to the sequencer.
        """
        self._check_handle()
        func = partial(self._event_output_direct, event, queue, port, dest)
        return self._event_output_wait(func)


class AsyncSequencerClient(SequencerClientBase):
    def __init__(self, *args, **kwargs):
        if "mode" in kwargs and not kwargs["mode"] & OpenMode.NONBLOCK:
            raise ValueError("NONBLOCK open mode must be used")
        super().__init__(*args, **kwargs)

    async def aclose(self):
        self.close()

    async def event_input(self, prefer_bytes: bool = False, timeout: Optional[float] = None):

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

    def drain_output(self) -> Awaitable[int]:
        self._check_handle()

        def func(remainder=None):
            _ = remainder
            return alsa.snd_seq_drain_output(self.handle), None

        return self._event_output_wait(func)

    def event_output(self,
                     event: Event,
                     queue: Union['Queue', int] = None,
                     port: Union['Port', int] = None,
                     dest: AddressType = None) -> Awaitable[int]:
        self._check_handle()
        func = partial(self._event_output, event, queue, port, dest)
        return self._event_output_wait(func)

    def event_output_direct(self,
                            event: Event,
                            queue: Union['Queue', int] = None,
                            port: Union['Port', int] = None,
                            dest: AddressType = None) -> Awaitable[int]:
        self._check_handle()
        func = partial(self._event_output_direct, event, queue, port, dest)
        return self._event_output_wait(func)


__all__ = ["SequencerClientBase", "SequencerClient", "ClientInfo", "ClientType"]
