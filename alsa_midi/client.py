
import errno
from enum import IntEnum, IntFlag
from typing import Any, Callable, List, NewType, Optional, Tuple, Union, overload

from ._ffi import alsa, ffi
from .address import SequencerAddress, SequencerAddressType
from .event import SequencerEvent
from .exceptions import SequencerStateError
from .port import (DEFAULT_PORT_TYPE, READ_PORT_PREFERRED_TYPES, RW_PORT, RW_PORT_PREFERRED_TYPES,
                   WRITE_PORT_PREFERRED_TYPES, SequencerPort, SequencerPortCaps, SequencerPortInfo,
                   SequencerPortType, _snd_seq_port_info_t_p, get_port_info_sort_key)
from .queue import SequencerQueue
from .util import _check_alsa_error

_snd_seq_t = NewType("_snd_seq_t", object)
_snd_seq_t_p = NewType("_snd_seq_t_p", Tuple[_snd_seq_t])


class SequencerStreamOpenTypes(IntFlag):
    OUTPUT = alsa.SND_SEQ_OPEN_OUTPUT
    INPUT = alsa.SND_SEQ_OPEN_INPUT
    DUPLEX = alsa.SND_SEQ_OPEN_DUPLEX


class SequencerOpenMode(IntFlag):
    NONBLOCK = alsa.SND_SEQ_NONBLOCK


class SequencerClientType(IntEnum):
    _UNSET = 0
    USER = alsa.SND_SEQ_USER_CLIENT
    KERNEL = alsa.SND_SEQ_KERNEL_CLIENT


_snd_seq_client_info_t = NewType("_snd_seq_client_info_t", object)
_snd_seq_client_info_t_p = NewType("_snd_seq_client_info_t", Tuple[_snd_seq_client_info_t])


class SequencerClientInfo:
    client_id: int
    name: str
    broadcast_filter: bool
    error_bounce: bool
    type: Optional[SequencerClientType]
    card_id: Optional[int]
    pid: Optional[int]
    num_ports: int
    event_lost: int

    def __init__(self,
                 client_id: int,
                 name: str,
                 broadcast_filter: bool = False,
                 error_bounce: bool = False,
                 type: SequencerClientType = None,
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
                type=SequencerClientType(alsa.snd_seq_client_info_get_type(info)),
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


class SequencerClient:
    client_id: int
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
        err = alsa.snd_seq_open(self._handle_p, sequencer_name_b, streams, mode)
        _check_alsa_error(err)
        self.handle = self._handle_p[0]
        alsa.snd_seq_set_client_name(self.handle, client_name_b)
        self.client_id = alsa.snd_seq_client_id(self.handle)

    def __del__(self):
        self.close()

    def _check_handle(self):
        if self._handle_p is None:
            raise SequencerStateError("Already closed")

    def close(self):
        if self._handle_p is None:
            return
        if self._handle_p[0] != ffi.NULL:
            alsa.snd_seq_close(self._handle_p[0])
        self._handle_p = None  # type: ignore
        self.handle = None  # type: ignore

    def create_port(self,
                    name: str,
                    caps: SequencerPortCaps = RW_PORT,
                    port_type: SequencerPortType = DEFAULT_PORT_TYPE,
                    ) -> SequencerPort:
        self._check_handle()
        port = alsa.snd_seq_create_simple_port(self.handle,
                                               name.encode("utf-8"),
                                               caps, port_type)
        _check_alsa_error(port)
        return SequencerPort(self, port)

    def create_queue(self, name: str = None) -> SequencerQueue:
        self._check_handle()
        if name is not None:
            queue = alsa.snd_seq_alloc_named_queue(self.handle, name.encode("utf-8"))
        else:
            queue = alsa.snd_seq_alloc_queue(self.handle)
        _check_alsa_error(queue)
        return SequencerQueue(self, queue)

    def drain_output(self):
        self._check_handle()
        err = alsa.snd_seq_drain_output(self.handle)
        _check_alsa_error(err)

    def drop_output(self):
        self._check_handle()
        err = alsa.snd_seq_drop_output(self.handle)
        _check_alsa_error(err)

    def event_input(self):
        self._check_handle()
        result = ffi.new("snd_seq_event_t**", ffi.NULL)
        err = alsa.snd_seq_event_input(self.handle, result)
        _check_alsa_error(err)
        cls = SequencerEvent._specialized.get(result[0].type, SequencerEvent)
        return cls._from_alsa(result[0])

    def event_output(self,
                     event: SequencerEvent,
                     queue: Union['SequencerQueue', int] = None,
                     port: Union['SequencerPort', int] = None,
                     dest: SequencerAddressType = None):
        self._check_handle()
        alsa_event = event._to_alsa()
        if queue is not None:
            if isinstance(queue, SequencerQueue):
                alsa_event.queue = queue.queue_id
            else:
                alsa_event.queue = queue
        elif event.queue is None:
            alsa_event.queue = alsa.SND_SEQ_QUEUE_DIRECT
        if port is not None:
            if isinstance(port, SequencerPort):
                alsa_event.source.port = port.port_id
            else:
                alsa_event.source.port = port
        if dest is not None:
            dest = SequencerAddress(dest)
            alsa_event.dest.client = dest.client_id
            alsa_event.dest.port = dest.port_id
        elif event.dest is None:
            alsa_event.dest.client = alsa.SND_SEQ_ADDRESS_SUBSCRIBERS
        err = alsa.snd_seq_event_output(self.handle, alsa_event)
        _check_alsa_error(err)

    @overload
    def query_next_client(self, previous: SequencerClientInfo) -> Optional[SequencerClientInfo]:
        ...

    @overload
    def query_next_client(self, previous: Optional[int] = None) -> Optional[SequencerClientInfo]:
        ...

    def query_next_client(self, previous: Optional[Union[SequencerClientInfo, int]] = None
                          ) -> Optional[SequencerClientInfo]:
        self._check_handle()
        if isinstance(previous, SequencerClientInfo):
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
            result = SequencerClientInfo._from_alsa(info)
        finally:
            alsa.snd_seq_client_info_free(info)
        return result

    @overload
    def query_next_port(self, client_id: int, previous: SequencerPortInfo
                        ) -> Optional[SequencerPortInfo]:
        ...

    @overload
    def query_next_port(self, client_id: int, previous: Optional[int] = None
                        ) -> Optional[SequencerPortInfo]:
        ...

    def query_next_port(self,
                        client_id: int,
                        previous: Optional[Union[SequencerPortInfo, int]] = None
                        ) -> Optional[SequencerPortInfo]:
        self._check_handle()
        if isinstance(previous, SequencerPortInfo):
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
            result = SequencerPortInfo._from_alsa(info)
        finally:
            alsa.snd_seq_port_info_free(info)
        return result

    def list_ports(self, *,
                   input: bool = None,
                   output: bool = None,
                   include_system: bool = False,
                   include_midi_through: bool = True,
                   include_no_export: bool = True,
                   only_connectable: bool = True,
                   sort: Union[bool, Callable[[SequencerPortInfo], Any]] = True,
                   ) -> List[SequencerPortInfo]:

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

                    port_info = SequencerPortInfo._from_alsa(port_ainfo)

                    if port_info.capability & SequencerPortCaps.NO_EXPORT \
                            and not include_no_export:
                        continue

                    can_write = port_info.capability & SequencerPortCaps.WRITE
                    can_sub_write = port_info.capability & SequencerPortCaps.SUBS_WRITE
                    can_read = port_info.capability & SequencerPortCaps.READ
                    can_sub_read = port_info.capability & SequencerPortCaps.SUBS_READ

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


__all__ = ["SequencerClient", "SequencerClientInfo", "SequencerClientType"]
