
import errno

import pytest

from alsa_midi import (ALSAError, AsyncSequencerClient, ClientInfo, ClientType, SequencerClient,
                       StateError, alsa, ffi)
from alsa_midi.client import SequencerClientBase


@pytest.mark.require_no_alsa_seq
def test_client_open_fail():
    with pytest.raises(ALSAError):
        SequencerClient("test")


@pytest.mark.require_alsa_seq
def test_client_open_close():
    client = SequencerClient("test")
    assert isinstance(client.client_id, int)
    assert client.handle is not None
    assert client.handle == client._handle_p[0]

    client.close()
    assert client.handle is None
    assert client._handle_p is None

    with pytest.raises(StateError):
        client.drain_output()

    # another close should not change anything
    client.close()

    # neither should this
    del client


@pytest.mark.require_alsa_seq
def test_client_open_close_alsa(alsa_seq_state):
    client = SequencerClient("test123")

    alsa_seq_state.load()
    assert alsa_seq_state.clients[client.client_id].name == "test123"

    client.close()

    alsa_seq_state.load()
    assert client.client_id not in alsa_seq_state.clients


@pytest.mark.require_alsa_seq
def test_client_open_del_alsa(alsa_seq_state):
    client = SequencerClient("test123")
    client_id = client.client_id

    alsa_seq_state.load()
    assert alsa_seq_state.clients[client_id].name == "test123"

    del client

    alsa_seq_state.load()
    assert client_id not in alsa_seq_state.clients


@pytest.mark.require_alsa_seq
def test_open_blocking():
    with pytest.raises(ValueError):
        SequencerClient("test", mode=0)
    with pytest.raises(ValueError):
        AsyncSequencerClient("test", mode=0)

    # allowed, but stupid
    client = SequencerClientBase("test", mode=0)
    client.close()


def test_client_info():

    # test defaults
    info = ClientInfo(client_id=11, name="client_info_test")

    assert info.client_id == 11
    assert info.name == "client_info_test"
    assert info.broadcast_filter is False
    assert info.error_bounce is False
    assert info.type is None
    assert info.card_id is None
    assert info.pid is None
    assert info.num_ports == 0
    assert info.event_lost == 0

    # test initializing all attributes
    info = ClientInfo(client_id=15,
                      name="client_info_test2",
                      broadcast_filter=True,
                      error_bounce=True,
                      type=ClientType.KERNEL,
                      card_id=8,
                      pid=100,
                      num_ports=5,
                      event_lost=7)

    assert info.client_id == 15
    assert info.name == "client_info_test2"
    assert info.broadcast_filter is True
    assert info.error_bounce is True
    assert info.type == ClientType.KERNEL
    assert info.card_id == 8
    assert info.pid == 100
    assert info.num_ports == 5
    assert info.event_lost == 7

    # test _to_alsa (only some values are writable to the ALSA struct)
    info = ClientInfo(client_id=17,
                      name="client_info_test3",
                      broadcast_filter=True,
                      error_bounce=False)

    assert info.client_id == 17
    assert info.name == "client_info_test3"
    assert info.broadcast_filter is True
    assert info.error_bounce is False

    alsa_info = info._to_alsa()
    assert alsa.snd_seq_client_info_get_client(alsa_info) == 17
    assert ffi.string(alsa.snd_seq_client_info_get_name(alsa_info)) == b"client_info_test3"
    assert alsa.snd_seq_client_info_get_broadcast_filter(alsa_info) == 1
    assert alsa.snd_seq_client_info_get_error_bounce(alsa_info) == 0

    # test _from_alsa (only the attributes we can set)
    info_p = ffi.new("snd_seq_client_info_t **")
    err = alsa.snd_seq_client_info_malloc(info_p)
    assert err >= 0
    alsa_info = ffi.gc(info_p[0], alsa.snd_seq_client_info_free)
    alsa.snd_seq_client_info_set_client(alsa_info, 44)
    alsa.snd_seq_client_info_set_name(alsa_info, b"client_info_test4")
    alsa.snd_seq_client_info_set_broadcast_filter(alsa_info, 1)
    alsa.snd_seq_client_info_set_error_bounce(alsa_info, 1)
    info = ClientInfo._from_alsa(alsa_info)

    assert info.client_id == 44
    assert info.name == "client_info_test4"
    assert info.broadcast_filter is True
    assert info.error_bounce is True
    assert info.type == ClientType._UNSET


@pytest.mark.require_alsa_seq
def test_query_next_client(alsa_seq_state):
    client = SequencerClient("test")
    alsa_seq_state.load()

    first_client_id = min(client_id for client_id in alsa_seq_state.clients)
    last_client_id = max(client_id for client_id in alsa_seq_state.clients)

    all_infos = []

    info = client.query_next_client()
    assert info is not None
    assert info.client_id == first_client_id

    client_id = -1

    while info is not None:
        all_infos.append(info)
        client_id = info.client_id
        alsa_client = alsa_seq_state.clients[client_id]
        assert info.name == alsa_client.name
        assert info.type is not None
        assert info.type.name.lower() == alsa_client.type.lower()
        assert info.num_ports == len(alsa_client.ports)

        info = client.query_next_client(info)

    assert client_id == last_client_id

    assert len(all_infos) == len(alsa_seq_state.clients)

    client.close()


@pytest.mark.require_alsa_seq
def test_port_subscribe_unsubscribe(alsa_seq_state):
    c1 = SequencerClient("c1")
    p11 = c1.create_port("p11")
    p12 = c1.create_port("p12")
    p13 = c1.create_port("p13")
    c2 = SequencerClient("c2")
    p21 = c1.create_port("p21")
    p22 = c1.create_port("p22")

    try:
        c1.subscribe_port(p13, p22)

        with pytest.raises(ALSAError) as err:
            c1.subscribe_port(p13, p22)
        assert err.value.errnum == -errno.EBUSY

        c1.subscribe_port(p13, p21)

        with pytest.raises(ALSAError) as err:
            c1.subscribe_port(p13, p21)
        assert err.value.errnum == -errno.EBUSY

        c1.subscribe_port(p11, p22)
        c1.subscribe_port(p21, p12)

        # FIXME: test the optional arguments to subscribe_port

        alsa_seq_state.load()
        ap11 = alsa_seq_state.ports[p11.client_id, p11.port_id]
        ap12 = alsa_seq_state.ports[p12.client_id, p12.port_id]
        ap13 = alsa_seq_state.ports[p13.client_id, p13.port_id]
        ap21 = alsa_seq_state.ports[p21.client_id, p21.port_id]
        ap22 = alsa_seq_state.ports[p22.client_id, p22.port_id]

        assert set(ap11.connected_to) == {(p22.client_id, p22.port_id)}
        assert set(ap11.connected_from) == set()
        assert set(ap12.connected_to) == set()
        assert set(ap12.connected_from) == {(p21.client_id, p21.port_id)}
        assert set(ap13.connected_to) == {(p21.client_id, p21.port_id),
                                          (p22.client_id, p22.port_id)}
        assert set(ap13.connected_from) == set()

        assert set(ap21.connected_to) == {(p12.client_id, p12.port_id)}
        assert set(ap21.connected_from) == {(p13.client_id, p13.port_id)}
        assert set(ap22.connected_to) == set()
        assert set(ap22.connected_from) == {(p11.client_id, p11.port_id),
                                            (p13.client_id, p13.port_id)}

        c1.unsubscribe_port(p11, p22)
        c1.unsubscribe_port(p21, p12)

        with pytest.raises(ALSAError) as err:
            c1.unsubscribe_port(p21, p12)
        assert err.value.errnum == -errno.ENOENT

        alsa_seq_state.load()
        ap11 = alsa_seq_state.ports[p11.client_id, p11.port_id]
        ap12 = alsa_seq_state.ports[p12.client_id, p12.port_id]
        ap13 = alsa_seq_state.ports[p13.client_id, p13.port_id]
        ap21 = alsa_seq_state.ports[p21.client_id, p21.port_id]
        ap22 = alsa_seq_state.ports[p22.client_id, p22.port_id]

        assert set(ap11.connected_to) == set()
        assert set(ap11.connected_from) == set()
        assert set(ap12.connected_to) == set()
        assert set(ap12.connected_from) == set()
        assert set(ap13.connected_to) == {(p21.client_id, p21.port_id),
                                          (p22.client_id, p22.port_id)}
        assert set(ap13.connected_from) == set()

        assert set(ap21.connected_to) == set()
        assert set(ap21.connected_from) == {(p13.client_id, p13.port_id)}
        assert set(ap22.connected_to) == set()
        assert set(ap22.connected_from) == {(p13.client_id, p13.port_id)}

    finally:
        c2.close()
        c1.close()
