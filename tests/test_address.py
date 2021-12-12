
from alsa_midi import SequencerAddress


def test_construct_int():
    addr = SequencerAddress(128)
    assert isinstance(addr, SequencerAddress)
    assert addr.client_id == 128
    assert addr.port_id == 0


def test_construct_int_int():
    addr = SequencerAddress(129, 2)
    assert isinstance(addr, SequencerAddress)
    assert addr.client_id == 129
    assert addr.port_id == 2


def test_construct_tuple():
    addr = SequencerAddress((1, 2))
    assert isinstance(addr, SequencerAddress)
    assert addr.client_id == 1
    assert addr.port_id == 2


def test_construct_string():
    addr = SequencerAddress("130:10")
    assert isinstance(addr, SequencerAddress)
    assert addr.client_id == 130
    assert addr.port_id == 10


def test_copy():
    addr1 = SequencerAddress(129, 2)
    addr2 = SequencerAddress(addr1)
    assert isinstance(addr2, SequencerAddress)
    assert addr2.client_id == 129
    assert addr2.port_id == 2


def test_str():
    addr = SequencerAddress(131, 5)
    assert str(addr) == "131:5"
