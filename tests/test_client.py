
import pytest

from alsa_midi import (SequencerALSAError, SequencerClient, SequencerClientInfo,
                       SequencerClientType, SequencerPortCaps, SequencerStateError, alsa, ffi)
from alsa_midi.port import SequencerPortInfo


@pytest.mark.require_no_alsa_seq
def test_client_open_fail():
    with pytest.raises(SequencerALSAError):
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

    with pytest.raises(SequencerStateError):
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
def test_client_drain_output_nothing():
    client = SequencerClient("test")
    client.drain_output()
    client.close()


@pytest.mark.require_alsa_seq
def test_client_drop_output_nothing():
    client = SequencerClient("test")
    client.drop_output()
    client.close()


def test_client_info():

    # test defaults
    info = SequencerClientInfo(client_id=11,
                               name="client_info_test")

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
    info = SequencerClientInfo(client_id=15,
                               name="client_info_test2",
                               broadcast_filter=True,
                               error_bounce=True,
                               type=SequencerClientType.KERNEL,
                               card_id=8,
                               pid=100,
                               num_ports=5,
                               event_lost=7)

    assert info.client_id == 15
    assert info.name == "client_info_test2"
    assert info.broadcast_filter is True
    assert info.error_bounce is True
    assert info.type == SequencerClientType.KERNEL
    assert info.card_id == 8
    assert info.pid == 100
    assert info.num_ports == 5
    assert info.event_lost == 7

    # test _to_alsa (only some values are writable to the ALSA struct)
    info = SequencerClientInfo(client_id=17,
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
    alsa_info = info_p[0]
    alsa.snd_seq_client_info_set_client(alsa_info, 44)
    alsa.snd_seq_client_info_set_name(alsa_info, b"client_info_test4")
    alsa.snd_seq_client_info_set_broadcast_filter(alsa_info, 1)
    alsa.snd_seq_client_info_set_error_bounce(alsa_info, 1)
    info = SequencerClientInfo._from_alsa(alsa_info)

    assert info.client_id == 44
    assert info.name == "client_info_test4"
    assert info.broadcast_filter is True
    assert info.error_bounce is True
    assert info.type == SequencerClientType._UNSET


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
def test_query_next_port(alsa_seq_state):
    client = SequencerClient("test")
    alsa_seq_state.load()

    # let's test it on the 'System' ports. They should always be there.
    client_id = 0

    first_port_id = min(port_id for port_id in alsa_seq_state.clients[client_id].ports)
    last_port_id = max(port_id for port_id in alsa_seq_state.clients[client_id].ports)

    all_infos = []

    info = client.query_next_port(client_id)
    assert info is not None
    assert info.port_id == first_port_id

    port_id = -1

    while info is not None:
        all_infos.append(info)
        port_id = info.port_id
        alsa_port = alsa_seq_state.clients[client_id].ports[port_id]

        assert info.client_id == alsa_port.client_id
        assert info.name == alsa_port.name

        assert (SequencerPortCaps.WRITE in info.capability) == ("w" in alsa_port.flags.lower())
        assert (SequencerPortCaps.SUBS_WRITE in info.capability) == ("W" in alsa_port.flags)
        assert (SequencerPortCaps.READ in info.capability) == ("r" in alsa_port.flags.lower())
        assert (SequencerPortCaps.SUBS_READ in info.capability) == ("R" in alsa_port.flags)

        assert info.read_use == len(alsa_port.connected_to)
        assert info.write_use == len(alsa_port.connected_from)

        info = client.query_next_port(client_id, info)

    assert port_id == last_port_id

    assert len(all_infos) == len(alsa_seq_state.clients[client_id].ports)

    client.close()


@pytest.mark.require_alsa_seq
def test_list_ports(alsa_seq_state):

    client = SequencerClient("test")

    # test defaults
    alsa_seq_state.load()
    alsa_client_names = [client.name for client in alsa_seq_state.clients.values()]
    ports = client.list_ports()

    for port in ports:
        assert isinstance(port, SequencerPortInfo)

    alsa_ports = []
    for alsa_port in alsa_seq_state.ports.values():
        if alsa_port.client_id == 0:
            # exclude system ports
            continue
        if "W" not in alsa_port.flags and "R" not in alsa_port.flags:
            # exclude unconnectable
            continue
        alsa_ports.append(alsa_port)

    assert len(ports) == len(alsa_ports)

    port_addrs = {(p.client_id, p.port_id) for p in ports}
    alsa_ports_addrs = {(p.client_id, p.port_id) for p in alsa_ports}

    assert port_addrs == alsa_ports_addrs

    # a client with a set of connectable ports
    other_c1 = SequencerClient("other_client1")
    input_port = other_c1.create_port(
            "in",
            SequencerPortCaps.READ | SequencerPortCaps.SUBS_READ)
    input_port_a = (input_port.client_id, input_port.port_id)
    output_port = other_c1.create_port(
            "out",
            SequencerPortCaps.WRITE | SequencerPortCaps.SUBS_WRITE)
    output_port_a = (output_port.client_id, output_port.port_id)
    inout_port = other_c1.create_port(
            "inout",
            SequencerPortCaps.READ | SequencerPortCaps.SUBS_READ
            | SequencerPortCaps.WRITE | SequencerPortCaps.SUBS_WRITE)
    inout_port_a = (inout_port.client_id, inout_port.port_id)

    # a client with a set of unconnectable or noexport ports
    other_c2 = SequencerClient("other_client2")
    input_port_nc = other_c2.create_port(
            "in",
            SequencerPortCaps.READ)
    input_port_nc_a = (input_port_nc.client_id, input_port_nc.port_id)
    output_port_nc = other_c2.create_port(
            "out",
            SequencerPortCaps.WRITE)
    output_port_nc_a = (output_port_nc.client_id, output_port_nc.port_id)
    inout_port_nc = other_c2.create_port(
            "inout",
            SequencerPortCaps.READ | SequencerPortCaps.WRITE)
    inout_port_nc_a = (inout_port_nc.client_id, inout_port_nc.port_id)
    inout_port_ne = other_c2.create_port(
            "inout",
            SequencerPortCaps.READ | SequencerPortCaps.SUBS_READ
            | SequencerPortCaps.WRITE | SequencerPortCaps.SUBS_WRITE
            | SequencerPortCaps.NO_EXPORT)
    inout_port_ne_a = (inout_port_ne.client_id, inout_port_ne.port_id)

    # test input=True
    ports = client.list_ports(input=True)
    port_addrs = {(p.client_id, p.port_id) for p in ports}
    assert input_port_a in port_addrs
    assert output_port_a not in port_addrs
    assert inout_port_a in port_addrs
    assert input_port_nc_a not in port_addrs
    assert output_port_nc_a not in port_addrs
    assert inout_port_nc_a not in port_addrs
    assert inout_port_ne_a in port_addrs

    # test output=True
    ports = client.list_ports(output=True)
    port_addrs = {(p.client_id, p.port_id) for p in ports}
    assert (0, 0) not in port_addrs
    assert (0, 1) not in port_addrs
    assert input_port_a not in port_addrs
    assert output_port_a in port_addrs
    assert inout_port_a in port_addrs
    assert input_port_nc_a not in port_addrs
    assert output_port_nc_a not in port_addrs
    assert inout_port_nc_a not in port_addrs
    assert inout_port_ne_a in port_addrs

    # test input=True output=True
    ports = client.list_ports(input=True, output=True)
    port_addrs = {(p.client_id, p.port_id) for p in ports}
    assert (0, 0) not in port_addrs
    assert (0, 1) not in port_addrs
    assert input_port_a not in port_addrs
    assert output_port_a not in port_addrs
    assert inout_port_a in port_addrs
    assert input_port_nc_a not in port_addrs
    assert output_port_nc_a not in port_addrs
    assert inout_port_nc_a not in port_addrs
    assert inout_port_ne_a in port_addrs

    # test include_system=True
    ports = client.list_ports(include_system=True)
    port_addrs = {(p.client_id, p.port_id) for p in ports}
    client_names = {p.client_name for p in ports}
    if "Midi Through" in alsa_client_names:
        assert "Midi Through" in client_names
    assert (0, 0) in port_addrs
    assert (0, 1) in port_addrs
    assert input_port_a in port_addrs
    assert output_port_a in port_addrs
    assert inout_port_a in port_addrs
    assert input_port_nc_a not in port_addrs
    assert output_port_nc_a not in port_addrs
    assert inout_port_nc_a not in port_addrs
    assert inout_port_ne_a in port_addrs

    # test include_system=False
    ports = client.list_ports(include_system=False)
    port_addrs = {(p.client_id, p.port_id) for p in ports}
    client_names = {p.client_name for p in ports}
    if "Midi Through" in alsa_client_names:
        assert "Midi Through" in client_names
    assert (0, 0) not in port_addrs
    assert (0, 1) not in port_addrs
    assert input_port_a in port_addrs
    assert output_port_a in port_addrs
    assert inout_port_a in port_addrs
    assert input_port_nc_a not in port_addrs
    assert output_port_nc_a not in port_addrs
    assert inout_port_nc_a not in port_addrs
    assert inout_port_ne_a in port_addrs

    # test include_midi_through=True
    ports = client.list_ports(include_midi_through=True)
    port_addrs = {(p.client_id, p.port_id) for p in ports}
    client_names = {p.client_name for p in ports}
    if "Midi Through" in alsa_client_names:
        assert "Midi Through" in client_names
    assert (0, 0) not in port_addrs
    assert (0, 1) not in port_addrs
    assert input_port_a in port_addrs
    assert output_port_a in port_addrs
    assert inout_port_a in port_addrs
    assert input_port_nc_a not in port_addrs
    assert output_port_nc_a not in port_addrs
    assert inout_port_nc_a not in port_addrs
    assert inout_port_ne_a in port_addrs

    # test include_midi_through=False
    ports = client.list_ports(include_midi_through=False)
    port_addrs = {(p.client_id, p.port_id) for p in ports}
    client_names = {p.client_name for p in ports}
    assert "Midi Through" not in client_names
    assert (0, 0) not in port_addrs
    assert (0, 1) not in port_addrs
    assert input_port_a in port_addrs
    assert output_port_a in port_addrs
    assert inout_port_a in port_addrs
    assert input_port_nc_a not in port_addrs
    assert output_port_nc_a not in port_addrs
    assert inout_port_nc_a not in port_addrs
    assert inout_port_ne_a in port_addrs

    # test include_no_export=True
    ports = client.list_ports(include_no_export=True)
    port_addrs = {(p.client_id, p.port_id) for p in ports}
    client_names = {p.client_name for p in ports}
    assert input_port_a in port_addrs
    assert output_port_a in port_addrs
    assert inout_port_a in port_addrs
    assert input_port_nc_a not in port_addrs
    assert output_port_nc_a not in port_addrs
    assert inout_port_nc_a not in port_addrs
    assert inout_port_ne_a in port_addrs

    # test include_no_export=False
    ports = client.list_ports(include_no_export=False)
    port_addrs = {(p.client_id, p.port_id) for p in ports}
    client_names = {p.client_name for p in ports}
    assert input_port_a in port_addrs
    assert output_port_a in port_addrs
    assert inout_port_a in port_addrs
    assert input_port_nc_a not in port_addrs
    assert output_port_nc_a not in port_addrs
    assert inout_port_nc_a not in port_addrs
    assert inout_port_ne_a not in port_addrs

    # test only_connectable=True
    ports = client.list_ports(only_connectable=True)
    port_addrs = {(p.client_id, p.port_id) for p in ports}
    client_names = {p.client_name for p in ports}
    assert input_port_a in port_addrs
    assert output_port_a in port_addrs
    assert inout_port_a in port_addrs
    assert input_port_nc_a not in port_addrs
    assert output_port_nc_a not in port_addrs
    assert inout_port_nc_a not in port_addrs
    assert inout_port_ne_a in port_addrs

    # test only_connectable=False
    ports = client.list_ports(only_connectable=False)
    port_addrs = {(p.client_id, p.port_id) for p in ports}
    client_names = {p.client_name for p in ports}
    assert input_port_a in port_addrs
    assert output_port_a in port_addrs
    assert inout_port_a in port_addrs
    assert input_port_nc_a in port_addrs
    assert output_port_nc_a in port_addrs
    assert inout_port_nc_a in port_addrs
    assert inout_port_ne_a in port_addrs

    other_c2.close()
    other_c1.close()
    client.close()
