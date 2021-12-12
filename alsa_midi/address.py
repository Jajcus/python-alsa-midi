
from abc import ABCMeta
from collections import namedtuple
from typing import TYPE_CHECKING, Tuple, Union, overload

from ._ffi import asound, ffi
from .util import _check_alsa_error

if TYPE_CHECKING:
    from .client import SequencerClient


class SequencerAddress(namedtuple("SequencerAddress", "client_id port_id"), metaclass=ABCMeta):
    __slots__ = ()

    @overload
    def __new__(cls, arg1: int, arg2: int = 0) -> 'SequencerAddress':
        ...

    @overload
    def __new__(cls, arg1: Tuple[int, int]) -> 'SequencerAddress':
        ...

    @overload
    def __new__(cls, arg1: str) -> 'SequencerAddress':
        ...

    @overload
    def __new__(cls, arg1: 'SequencerAddress') -> 'SequencerAddress':
        ...

    @overload
    def __new__(cls, arg1: 'SequencerClient', arg2: int = 0) -> 'SequencerAddress':
        ...

    def __new__(cls,
                arg1: Union[int, str, 'SequencerClient', tuple],
                arg2: int = 0) -> 'SequencerAddress':
        if isinstance(arg1, str):
            return super().__new__(cls, *cls._parse(arg1))
        elif hasattr(arg1, "client_id"):
            client_id = arg1.client_id  # type: ignore
            port_id = getattr(arg1, "port_id", arg2)
            return super().__new__(cls, client_id, port_id)
        elif isinstance(arg1, tuple):
            return super().__new__(cls, *arg1)
        else:
            return super().__new__(cls, arg1, arg2)

    @staticmethod
    def _parse(arg: str) -> Tuple[int, int]:
        addr_p = ffi.new("snd_seq_addr_t *")
        result = asound.snd_seq_parse_address(ffi.NULL, addr_p, arg.encode())
        _check_alsa_error(result)
        return addr_p.client, addr_p.port

    def __str__(self):
        return f"{self.client_id}:{self.port_id}"


ALL_SUBSCRIBERS = SequencerAddress(asound.SND_SEQ_ADDRESS_SUBSCRIBERS, 0)
SYSTEM_TIMER = SequencerAddress(asound.SND_SEQ_CLIENT_SYSTEM, asound.SND_SEQ_PORT_SYSTEM_TIMER)
SYSTEM_ANNOUNCE = SequencerAddress(asound.SND_SEQ_CLIENT_SYSTEM,
                                   asound.SND_SEQ_PORT_SYSTEM_ANNOUNCE)

__all__ = ["SequencerAddress", "ALL_SUBSCRIBERS", "SYSTEM_TIMER", "SYSTEM_ANNOUNCE"]
