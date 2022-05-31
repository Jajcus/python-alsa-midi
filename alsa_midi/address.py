
from collections import namedtuple
from typing import TYPE_CHECKING, Any, Tuple, Union, overload

from ._ffi import alsa, ffi
from .util import _check_alsa_error

if TYPE_CHECKING:
    from .client import SequencerClient
    from .port import Port, PortInfo


AddressType = Union['Address', 'Port', 'PortInfo', Tuple[int, int]]


class Address(namedtuple("Address", "client_id port_id")):
    """ALSA sequencer port address (immutable).

    Usage:

    >>> addr = Address(128, 1)
    >>> addr
    Address(client_id=128, port_id=1)
    >>> print(f"addres: {addr} client id: {addr.client_id} port id: {addr.port_id}")
    addres: 128:1 client id: 128 port id: 1
    >>> Address(128, 1)
    Address(client_id=128, port_id=1)
    >>> Address("128:1")
    Address(client_id=128, port_id=1)
    >>> addr = Address((128, 1))
    Address(client_id=128, port_id=1)
    >>> addr = Address(client, 1)
    >>> addr = Address(port)

    :param arg1: address or client_id
    :param arg2: port id

    :ivar client_id: client id
    :ivar port_id: port id
    """
    __slots__ = ()

    @overload
    def __new__(cls, arg1: int, arg2: int = 0) -> 'Address':
        ...

    @overload
    def __new__(cls, arg1: AddressType) -> 'Address':
        ...

    @overload
    def __new__(cls, arg1: str) -> 'Address':
        ...

    @overload
    def __new__(cls, arg1: 'SequencerClient', arg2: int = 0) -> 'Address':
        ...

    def __new__(cls,
                arg1: Union[int, str, AddressType, 'SequencerClient'],
                arg2: int = 0) -> 'Address':
        if isinstance(arg1, str):
            tple: Any = cls._parse(arg1)
            return tuple.__new__(cls, tple)
        elif hasattr(arg1, "client_id"):
            client_id = arg1.client_id  # type: ignore
            port_id = getattr(arg1, "port_id", arg2)
            if port_id is None:
                port_id = 0
            tple: Any = (client_id, port_id)
            return tuple.__new__(cls, tple)
        elif isinstance(arg1, tuple):
            if len(arg1) != 2:
                raise ValueError("Wrong tuple length")
            tple: Any = (int(v) if v is not None else 0 for v in arg1)
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


ALL_SUBSCRIBERS = Address(alsa.SND_SEQ_ADDRESS_SUBSCRIBERS, 0)
SYSTEM_TIMER = Address(alsa.SND_SEQ_CLIENT_SYSTEM, alsa.SND_SEQ_PORT_SYSTEM_TIMER)
SYSTEM_ANNOUNCE = Address(alsa.SND_SEQ_CLIENT_SYSTEM, alsa.SND_SEQ_PORT_SYSTEM_ANNOUNCE)

__all__ = ["Address", "AddressType",
           "ALL_SUBSCRIBERS", "SYSTEM_TIMER", "SYSTEM_ANNOUNCE"]
