
import pytest

from alsa_midi import READ_PORT, PortCaps, PortType, SequencerClient
from alsa_midi.port import PortInfo


@pytest.mark.require_alsa_seq
def test_get_port_info(alsa_seq_state):
    client = SequencerClient("test")
    alsa_seq_state.load()

    # let's test it on the 'System' ports. They should always be there.

    for (client_id, port_id), alsa_port in alsa_seq_state.ports.items():
        info = client.get_port_info((client_id, port_id))

        assert info.client_id == alsa_port.client_id
        assert info.name == alsa_port.name

        assert (PortCaps.WRITE in info.capability) == ("w" in alsa_port.flags.lower())
        assert (PortCaps.SUBS_WRITE in info.capability) == ("W" in alsa_port.flags)
        assert (PortCaps.READ in info.capability) == ("r" in alsa_port.flags.lower())
        assert (PortCaps.SUBS_READ in info.capability) == ("R" in alsa_port.flags)

        assert info.read_use == len(alsa_port.connected_to)
        assert info.write_use == len(alsa_port.connected_from)


def test_get_own_port_info():
    client = SequencerClient("test")

    p1 = client.create_port("p1")
    p2 = client.create_port("p2")

    info1 = client.get_port_info(p1)
    info2 = client.get_port_info(p2.port_id)
    info1a = p1.get_info()

    assert info1.client_id == client.client_id
    assert info1.port_id == p1.port_id
    assert info1.name == "p1"

    assert info2.client_id == client.client_id
    assert info2.port_id == p2.port_id
    assert info2.name == "p2"

    assert info1a.client_id == client.client_id
    assert info1a.port_id == p1.port_id
    assert info1a.name == "p1"


@pytest.mark.require_alsa_seq
def test_set_port_info(alsa_seq_state):
    client = SequencerClient("test")

    p1 = client.create_port("p1")

    info = PortInfo(name="p1 changed",
                    capability=READ_PORT,
                    type=PortType.SPECIFIC,
                    midi_channels=5,
                    midi_voices=6,
                    synth_voices=7,
                    timestamping=True,
                    timestamp_real=True)

    p1.set_info(info)

    alsa_seq_state.load()

    alsa_port = alsa_seq_state.ports[client.client_id, p1.port_id]

    assert alsa_port.name == "p1 changed"

    assert "w" not in alsa_port.flags.lower()
    assert "W" not in alsa_port.flags
    assert "r" in alsa_port.flags.lower()
    assert "R" in alsa_port.flags


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

        assert (PortCaps.WRITE in info.capability) == ("w" in alsa_port.flags.lower())
        assert (PortCaps.SUBS_WRITE in info.capability) == ("W" in alsa_port.flags)
        assert (PortCaps.READ in info.capability) == ("r" in alsa_port.flags.lower())
        assert (PortCaps.SUBS_READ in info.capability) == ("R" in alsa_port.flags)

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
        assert isinstance(port, PortInfo)

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
            PortCaps.READ | PortCaps.SUBS_READ)
    input_port_a = (input_port.client_id, input_port.port_id)
    output_port = other_c1.create_port(
            "out",
            PortCaps.WRITE | PortCaps.SUBS_WRITE)
    output_port_a = (output_port.client_id, output_port.port_id)
    inout_port = other_c1.create_port(
            "inout",
            PortCaps.READ | PortCaps.SUBS_READ
            | PortCaps.WRITE | PortCaps.SUBS_WRITE)
    inout_port_a = (inout_port.client_id, inout_port.port_id)
    s_inout_port = other_c1.create_port(
            "inout",
            PortCaps.READ | PortCaps.SUBS_READ
            | PortCaps.WRITE | PortCaps.SUBS_WRITE,
            PortType.SPECIFIC)
    s_inout_port_a = (s_inout_port.client_id, s_inout_port.port_id)

    # a client with a set of unconnectable or noexport ports
    other_c2 = SequencerClient("other_client2")
    input_port_nc = other_c2.create_port(
            "in",
            PortCaps.READ)
    input_port_nc_a = (input_port_nc.client_id, input_port_nc.port_id)
    output_port_nc = other_c2.create_port(
            "out",
            PortCaps.WRITE)
    output_port_nc_a = (output_port_nc.client_id, output_port_nc.port_id)
    inout_port_nc = other_c2.create_port(
            "inout",
            PortCaps.READ | PortCaps.WRITE)
    inout_port_nc_a = (inout_port_nc.client_id, inout_port_nc.port_id)
    inout_port_ne = other_c2.create_port(
            "inout",
            PortCaps.READ | PortCaps.SUBS_READ
            | PortCaps.WRITE | PortCaps.SUBS_WRITE
            | PortCaps.NO_EXPORT)
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
    assert s_inout_port_a not in port_addrs

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
    assert s_inout_port_a not in port_addrs

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
    assert s_inout_port_a not in port_addrs

    # test include_system=True
    ports = client.list_ports(include_system=True, type=PortType.ANY)
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
    ports = client.list_ports(include_system=False, type=PortType.ANY)
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
    assert s_inout_port_a not in port_addrs

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
    assert s_inout_port_a not in port_addrs

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
    assert s_inout_port_a not in port_addrs

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
    assert s_inout_port_a not in port_addrs

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
    assert s_inout_port_a not in port_addrs

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
    assert s_inout_port_a not in port_addrs

    # test type=PortType.SPECIFIC
    ports = client.list_ports(type=PortType.SPECIFIC)
    port_addrs = {(p.client_id, p.port_id) for p in ports}
    assert input_port_a not in port_addrs
    assert output_port_a not in port_addrs
    assert inout_port_a not in port_addrs
    assert input_port_nc_a not in port_addrs
    assert output_port_nc_a not in port_addrs
    assert inout_port_nc_a not in port_addrs
    assert inout_port_ne_a not in port_addrs
    assert s_inout_port_a in port_addrs

    other_c2.close()
    other_c1.close()
    client.close()


@pytest.mark.require_alsa_seq
def test_list_ports_sorting(alsa_seq_state):

    client = SequencerClient("test")

    # test defaults
    alsa_seq_state.load()
    alsa_client_names = [client.name for client in alsa_seq_state.clients.values()]
    ports = client.list_ports(type=PortType.ANY)

    for port in ports:
        assert isinstance(port, PortInfo)

    # MIDI Through goes last
    if "Midi Through" in alsa_client_names:
        assert ports[-1].client_name == "Midi Through"

    other_c1 = SequencerClient("other_client1")
    specific_inout = other_c1.create_port(
            "spec inout",
            PortCaps.READ | PortCaps.SUBS_READ
            | PortCaps.WRITE | PortCaps.SUBS_WRITE,
            PortType.SPECIFIC)
    specific_inout_a = (specific_inout.client_id, specific_inout.port_id)
    midi_generic_input = other_c1.create_port(
            "in",
            PortCaps.READ | PortCaps.SUBS_READ,
            PortType.MIDI_GENERIC)
    midi_generic_input_a = (midi_generic_input.client_id, midi_generic_input.port_id)
    midi_generic_output = other_c1.create_port(
            "out",
            PortCaps.WRITE | PortCaps.SUBS_WRITE,
            PortType.MIDI_GENERIC)
    midi_generic_output_a = (midi_generic_output.client_id, midi_generic_output.port_id)
    midi_generic_inout = other_c1.create_port(
            "inout",
            PortCaps.READ | PortCaps.SUBS_READ
            | PortCaps.WRITE | PortCaps.SUBS_WRITE,
            PortType.MIDI_GENERIC)
    midi_generic_inout_a = (midi_generic_inout.client_id, midi_generic_inout.port_id)

    other_c2 = SequencerClient("other_client2")
    midi_gm_input = other_c2.create_port(
            "GM in",
            PortCaps.READ | PortCaps.SUBS_READ,
            PortType.MIDI_GENERIC | PortType.MIDI_GM)
    midi_gm_input_a = (midi_gm_input.client_id, midi_gm_input.port_id)
    midi_gm_output = other_c2.create_port(
            "GM out",
            PortCaps.WRITE | PortCaps.SUBS_WRITE,
            PortType.MIDI_GENERIC | PortType.MIDI_GM)
    midi_gm_output_a = (midi_gm_output.client_id, midi_gm_output.port_id)
    midi_gm_inout = other_c2.create_port(
            "GM inout",
            PortCaps.READ | PortCaps.SUBS_READ
            | PortCaps.WRITE | PortCaps.SUBS_WRITE,
            PortType.MIDI_GENERIC | PortType.MIDI_GM)
    midi_gm_inout_a = (midi_gm_inout.client_id, midi_gm_inout.port_id)
    midi_synth_out = other_c2.create_port(
            "GM Synth out",
            PortCaps.WRITE | PortCaps.SUBS_WRITE,
            PortType.MIDI_GENERIC | PortType.MIDI_GM
            | PortType.SYNTHESIZER)
    midi_synth_out_a = (midi_synth_out.client_id, midi_synth_out.port_id)

    # no sorting -> order by client_id, port_id
    ports = client.list_ports(only_connectable=False, include_system=True, sort=False,
                              type=PortType.ANY)
    port_addrs = [(p.client_id, p.port_id) for p in ports]
    for i in range(0, len(port_addrs) - 1):
        assert port_addrs[i] < port_addrs[i + 1]

    # default sorting
    ports = client.list_ports(only_connectable=False, include_system=True,
                              type=PortType.ANY)
    pa = [(p.client_id, p.port_id) for p in ports]

    assert pa.index(specific_inout_a) > pa.index(midi_generic_input_a)
    assert pa.index(midi_generic_input_a) < pa.index(midi_generic_output_a)
    assert pa.index(midi_generic_output_a) < pa.index(midi_generic_inout_a)
    assert pa.index(midi_generic_inout_a) < pa.index(midi_gm_input_a)
    assert pa.index(midi_gm_input_a) < pa.index(midi_gm_output_a)
    assert pa.index(midi_gm_output_a) < pa.index(midi_gm_inout_a)
    assert pa.index(midi_gm_inout_a) < pa.index(midi_synth_out_a)
    assert pa.index(specific_inout_a) > pa.index(midi_gm_inout_a)
    if "Midi Through" in alsa_client_names:
        assert ports[-1].client_name == "Midi Through"

    # default input port sorting
    ports = client.list_ports(only_connectable=False, include_system=True, input=True,
                              type=PortType.ANY)
    pa = [(p.client_id, p.port_id) for p in ports]

    assert pa.index(specific_inout_a) > pa.index(midi_generic_input_a)
    assert pa.index(midi_generic_input_a) < pa.index(midi_generic_inout_a)
    assert pa.index(midi_generic_inout_a) < pa.index(midi_gm_input_a)
    assert pa.index(midi_gm_input_a) < pa.index(midi_gm_inout_a)
    assert pa.index(specific_inout_a) > pa.index(midi_gm_inout_a)
    if "Midi Through" in alsa_client_names:
        assert ports[-1].client_name == "Midi Through"

    # default output port sorting
    ports = client.list_ports(only_connectable=False, include_system=True, output=True,
                              type=PortType.ANY)
    pa = [(p.client_id, p.port_id) for p in ports]

    assert pa.index(specific_inout_a) > pa.index(midi_generic_output_a)
    assert pa.index(midi_generic_output_a) < pa.index(midi_generic_inout_a)
    assert pa.index(midi_generic_inout_a) > pa.index(midi_gm_output_a)
    assert pa.index(midi_gm_output_a) < pa.index(midi_gm_inout_a)
    assert pa.index(midi_gm_inout_a) > pa.index(midi_synth_out_a)
    assert pa.index(midi_synth_out_a) < pa.index(midi_generic_output_a)
    assert pa.index(specific_inout_a) > pa.index(midi_synth_out_a)
    if "Midi Through" in alsa_client_names:
        assert ports[-1].client_name == "Midi Through"

    other_c2.close()
    other_c1.close()
    client.close()
