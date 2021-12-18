
from alsa_midi import Address


def test_construct_int():
    addr = Address(128)
    assert isinstance(addr, Address)
    assert addr.client_id == 128
    assert addr.port_id == 0


def test_construct_int_int():
    addr = Address(129, 2)
    assert isinstance(addr, Address)
    assert addr.client_id == 129
    assert addr.port_id == 2


def test_construct_tuple():
    addr = Address((1, 2))
    assert isinstance(addr, Address)
    assert addr.client_id == 1
    assert addr.port_id == 2


def test_construct_string():
    addr = Address("130:10")
    assert isinstance(addr, Address)
    assert addr.client_id == 130
    assert addr.port_id == 10


def test_copy():
    addr1 = Address(129, 2)
    addr2 = Address(addr1)
    assert isinstance(addr2, Address)
    assert addr2.client_id == 129
    assert addr2.port_id == 2


def test_str():
    addr = Address(131, 5)
    assert str(addr) == "131:5"
