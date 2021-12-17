
from collections import namedtuple
from typing import TYPE_CHECKING, Any, Tuple, Union, overload

from ._ffi import alsa, ffi
from .util import _check_alsa_error

if TYPE_CHECKING:
    from .client import SequencerClient
    from .port import SequencerPort, SequencerPortInfo


SequencerAddressType = Union['SequencerAddress',
                             'SequencerPort',
                             'SequencerPortInfo',
                             Tuple[int, int]]


class SequencerAddress(namedtuple("SequencerAddress", "client_id port_id")):
    __slots__ = ()

    @overload
    def __new__(cls, arg1: int, arg2: int = 0) -> 'SequencerAddress':
        ...

    @overload
    def __new__(cls, arg1: SequencerAddressType) -> 'SequencerAddress':
        ...

    @overload
    def __new__(cls, arg1: str) -> 'SequencerAddress':
        ...

    @overload
    def __new__(cls, arg1: 'SequencerClient', arg2: int = 0) -> 'SequencerAddress':
        ...

    def __new__(cls,
                arg1: Union[int, str, SequencerAddressType, 'SequencerClient'],
                arg2: int = 0) -> 'SequencerAddress':
        if isinstance(arg1, str):
            tple: Any = cls._parse(arg1)
            return tuple.__new__(cls, tple)
        elif hasattr(arg1, "client_id"):
            client_id = arg1.client_id  # type: ignore
            port_id = getattr(arg1, "port_id", arg2)
            tple: Any = (client_id, port_id)
            return tuple.__new__(cls, tple)
        elif isinstance(arg1, tuple):
            tple: Any = arg1
            return tuple.__new__(cls, tple)
        else:
            tple: Any = (int(arg1), int(arg2))  # type: ignore
            return tuple.__new__(cls, tple)

    @staticmethod
    def _parse(arg: str) -> Tuple[int, int]:
        addr_p = ffi.new("snd_seq_addr_t *")
        result = alsa.snd_seq_parse_address(ffi.NULL, addr_p, arg.encode())
        _check_alsa_error(result)
        return addr_p.client, addr_p.port

    def __str__(self):
        return f"{self.client_id}:{self.port_id}"


ALL_SUBSCRIBERS = SequencerAddress(alsa.SND_SEQ_ADDRESS_SUBSCRIBERS, 0)
SYSTEM_TIMER = SequencerAddress(alsa.SND_SEQ_CLIENT_SYSTEM, alsa.SND_SEQ_PORT_SYSTEM_TIMER)
SYSTEM_ANNOUNCE = SequencerAddress(alsa.SND_SEQ_CLIENT_SYSTEM,
                                   alsa.SND_SEQ_PORT_SYSTEM_ANNOUNCE)

__all__ = ["SequencerAddress", "SequencerAddressType",
           "ALL_SUBSCRIBERS", "SYSTEM_TIMER", "SYSTEM_ANNOUNCE"]
