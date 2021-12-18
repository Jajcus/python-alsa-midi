
import errno
import select
import time
from enum import IntEnum, IntFlag
from functools import partial
from typing import Any, Callable, List, NewType, Optional, Tuple, Union, overload

from ._ffi import alsa, ffi
from .address import AddressType
from .event import Event
from .exceptions import StateError
from .port import (DEFAULT_PORT_TYPE, READ_PORT_PREFERRED_TYPES, RW_PORT, RW_PORT_PREFERRED_TYPES,
                   WRITE_PORT_PREFERRED_TYPES, Port, PortCaps, PortInfo, PortType,
                   _snd_seq_port_info_t_p, get_port_info_sort_key)
from .queue import Queue
from .util import _check_alsa_error

_snd_seq_t = NewType("_snd_seq_t", object)
_snd_seq_t_p = NewType("_snd_seq_t_p", Tuple[_snd_seq_t])


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
_snd_seq_client_info_t_p = NewType("_snd_seq_client_info_t", Tuple[_snd_seq_client_info_t])


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
        info_p: _snd_seq_client_info_t_p = ffi.new("snd_seq_client_info_t **")
        err = alsa.snd_seq_client_info_malloc(info_p)
        _check_alsa_error(err)
        info = info_p[0]
        alsa.snd_seq_client_info_set_client(info, self.client_id)
        alsa.snd_seq_client_info_set_name(info, self.name.encode())
        alsa.snd_seq_client_info_set_broadcast_filter(info, 1 if self.broadcast_filter else 0)
        alsa.snd_seq_client_info_set_error_bounce(info, 1 if self.error_bounce else 0)
        return info


class SequencerClientBase:
    client_id: int
    handle: _snd_seq_t
    _handle_p: _snd_seq_t_p
    _read_fds: List[int] = []
    _write_fds: List[int] = []

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
        self.close()

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
        pfds = ffi.new("struct pollfd[]", pfds_count)
        filled = alsa.snd_seq_poll_descriptors(self.handle, pfds, pfds_count,
                                               select.POLLIN | select.POLLOUT)
        for i in range(0, filled):
            if pfds[i].events & select.POLLIN:
                self._read_fds.append(pfds[i].fd)
            if pfds[i].events & select.POLLOUT:
                self._write_fds.append(pfds[i].fd)

    def create_port(self,
                    name: str,
                    caps: PortCaps = RW_PORT,
                    port_type: PortType = DEFAULT_PORT_TYPE,
                    ) -> Port:
        self._check_handle()
        port = alsa.snd_seq_create_simple_port(self.handle,
                                               name.encode("utf-8"),
                                               caps, port_type)
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

    def _event_input(self) -> Tuple[int, Optional[Event]]:
        buf = ffi.new("snd_seq_event_t**", ffi.NULL)
        result = alsa.snd_seq_event_input(self.handle, buf)
        if result >= 0:
            cls = Event._specialized.get(buf[0].type, Event)
            return result, cls._from_alsa(buf[0])
        else:
            return result, None

    def event_input(self):
        result, event = self._event_input()
        _check_alsa_error(result)
        return event

    def _event_output(self,
                      event: Event,
                      queue: Union['Queue', int] = None,
                      port: Union['Port', int] = None,
                      dest: AddressType = None):
        alsa_event = event._to_alsa(queue=queue, port=port, dest=dest)
        result = alsa.snd_seq_event_output(self.handle, alsa_event)
        return result

    def event_output(self,
                     event: Event,
                     queue: Union['Queue', int] = None,
                     port: Union['Port', int] = None,
                     dest: AddressType = None):
        self._check_handle()
        result = self._event_output(event, queue, port, dest)
        _check_alsa_error(result)
        return result

    def event_output_buffer(self,
                            event: Event,
                            queue: Union['Queue', int] = None,
                            port: Union['Port', int] = None,
                            dest: AddressType = None):
        self._check_handle()
        alsa_event = event._to_alsa(queue=queue, port=port, dest=dest)
        result = alsa.snd_seq_event_output(self.handle, alsa_event)
        _check_alsa_error(result)
        return result

    def _event_output_direct(self,
                             event: Event,
                             queue: Union['Queue', int] = None,
                             port: Union['Port', int] = None,
                             dest: AddressType = None):
        alsa_event = event._to_alsa(queue=queue, port=port, dest=dest)
        result = alsa.snd_seq_event_output(self.handle, alsa_event)
        return result

    def event_output_direct(self,
                            event: Event,
                            queue: Union['Queue', int] = None,
                            port: Union['Port', int] = None,
                            dest: AddressType = None):
        self._check_handle()
        result = self._event_output_direct(event, queue, port, dest)
        _check_alsa_error(result)
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
            info_p: _snd_seq_client_info_t_p = ffi.new("snd_seq_client_info_t **")
            err = alsa.snd_seq_client_info_malloc(info_p)
            _check_alsa_error(err)
            info = info_p[0]
            alsa.snd_seq_client_info_set_client(info, -1 if previous is None else previous)
        try:
            err = alsa.snd_seq_query_next_client(self.handle, info)
            if err == -errno.ENOENT:
                return None
            _check_alsa_error(err)
            result = ClientInfo._from_alsa(info)
        finally:
            alsa.snd_seq_client_info_free(info)
        return result

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
            info_p: _snd_seq_port_info_t_p = ffi.new("snd_seq_port_info_t **")
            err = alsa.snd_seq_port_info_malloc(info_p)
            _check_alsa_error(err)
            info = info_p[0]
            alsa.snd_seq_port_info_set_client(info, client_id)
            alsa.snd_seq_port_info_set_port(info, -1 if previous is None else previous)
        try:
            err = alsa.snd_seq_query_next_port(self.handle, info)
            if err == -errno.ENOENT:
                return None
            _check_alsa_error(err)
            result = PortInfo._from_alsa(info)
        finally:
            alsa.snd_seq_port_info_free(info)
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

        client_ainfo = None
        port_ainfo = None

        try:
            client_ainfo_p: _snd_seq_client_info_t_p = ffi.new("snd_seq_client_info_t **")
            err = alsa.snd_seq_client_info_malloc(client_ainfo_p)
            _check_alsa_error(err)
            client_ainfo = client_ainfo_p[0]
            port_ainfo_p: _snd_seq_port_info_t_p = ffi.new("snd_seq_port_info_t **")
            err = alsa.snd_seq_port_info_malloc(port_ainfo_p)
            _check_alsa_error(err)
            port_ainfo = port_ainfo_p[0]

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
        finally:
            if client_ainfo is not None:
                alsa.snd_seq_client_info_free(client_ainfo)
            if port_ainfo is not None:
                alsa.snd_seq_port_info_free(port_ainfo)

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


class SequencerClient(SequencerClientBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._read_poll = select.poll()
        for fd in self._read_fds:
            self._read_poll.register(fd, select.POLLIN)
        self._write_poll = select.poll()
        for fd in self._write_fds:
            self._write_poll.register(fd, select.POLLOUT)

    def event_input(self, timeout: Optional[float] = None):
        if timeout:
            until = time.monotonic() + timeout
        else:
            until = None

        while True:
            result, event = self._event_input()
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

    def _event_output_wait(self, func, timeout: Optional[float] = None):
        if timeout:
            until = time.monotonic() + timeout
        else:
            until = None

        while True:
            result = func()
            if result != -errno.EAGAIN:
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

    def drain_output(self):
        self._check_handle()
        func = partial(alsa.snd_seq_drain_output, self.handle)
        return self._event_output_wait(func)

    def event_output(self,
                     event: Event,
                     queue: Union['Queue', int] = None,
                     port: Union['Port', int] = None,
                     dest: AddressType = None):
        self._check_handle()
        func = partial(self._event_output, event, queue, port, dest)
        return self._event_output_wait(func)

    def event_output_direct(self,
                            event: Event,
                            queue: Union['Queue', int] = None,
                            port: Union['Port', int] = None,
                            dest: AddressType = None):
        self._check_handle()
        func = partial(self._event_output_direct, event, queue, port, dest)
        return self._event_output_wait(func)


__all__ = ["SequencerClientBase", "SequencerClient", "ClientInfo", "ClientType"]
