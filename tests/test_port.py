
import errno
from typing import Any

import pytest

from alsa_midi import (Address, ALSAError, Port, PortCaps, PortInfo, PortType, SequencerClient,
                       alsa, ffi)
from alsa_midi.port import get_port_info_sort_key


@pytest.mark.require_alsa_seq
def test_port_create_close():
    client = SequencerClient("test_c")
    port = client.create_port("test_p")

    assert isinstance(port, Port)
    assert port.client is client

    port.close()

    assert port.client is None

    # should do nothing now
    del port


@pytest.mark.require_alsa_seq
def test_port_create_del():
    client = SequencerClient("test_c")
    port = client.create_port("test_p")

    assert isinstance(port, Port)
    assert port.client is client

    del port


@pytest.mark.require_alsa_seq
def test_port_create_close_alsa(alsa_seq_state):
    client = SequencerClient("test_c")
    port = client.create_port("test_p")

    alsa_seq_state.load()
    assert (port.client_id, port.port_id) in alsa_seq_state.ports
    alsa_port = alsa_seq_state.ports[port.client_id, port.port_id]

    assert alsa_port.name == "test_p"
    assert "RWe" in alsa_port.flags

    port.close()

    alsa_seq_state.load()
    assert (port.client_id, port.port_id) not in alsa_seq_state.ports


@pytest.mark.require_alsa_seq
def test_port_create_del_alsa(alsa_seq_state):
    client = SequencerClient("test_c")
    port = client.create_port("test_p")

    client_id, port_id = port.client_id, port.port_id

    alsa_seq_state.load()
    assert (client_id, port_id) in alsa_seq_state.ports
    alsa_port = alsa_seq_state.ports[client_id, port_id]

    assert alsa_port.name == "test_p"
    assert "RWe" in alsa_port.flags

    del port

    alsa_seq_state.load()
    assert (client_id, port_id) not in alsa_seq_state.ports


@pytest.mark.require_alsa_seq
def test_port_connect_disconnect(alsa_seq_state):
    c1 = SequencerClient("c1")
    p11 = c1.create_port("p11")
    c2 = SequencerClient("c1")
    p21 = c2.create_port("p21")
    p22 = c2.create_port("p22")

    try:
        p11.connect_to(p21)
        p11.connect_from(p22)

        with pytest.raises(ALSAError) as err:
            p11.connect_from(p22)
        assert err.value.errnum == -errno.EBUSY

        alsa_seq_state.load()
        ap11 = alsa_seq_state.ports[p11.client_id, p11.port_id]
        ap22 = alsa_seq_state.ports[p22.client_id, p22.port_id]

        assert (p21.client_id, p21.port_id) in ap11.connected_to
        assert (p22.client_id, p22.port_id) in ap11.connected_from
        assert (p11.client_id, p11.port_id) in ap22.connected_to

        p22.disconnect_to((p11.client_id, p11.port_id))

        with pytest.raises(ALSAError) as err:
            p22.disconnect_to((p11.client_id, p11.port_id))
        assert err.value.errnum == -errno.ENOENT

        alsa_seq_state.load()
        ap11 = alsa_seq_state.ports[p11.client_id, p11.port_id]
        ap22 = alsa_seq_state.ports[p22.client_id, p22.port_id]

        assert (p21.client_id, p21.port_id) in ap11.connected_to
        assert (p22.client_id, p22.port_id) not in ap11.connected_from
    finally:
        c1.close()
        c2.close()


def test_port_as_address():
    class ClientMock:
        def __init__(self, client_id):
            self.client_id = client_id
            self.handle = None

    client: Any = ClientMock(129)
    port = Port(client, 3)

    assert port.client_id == 129
    assert port.port_id == 3

    addr = Address(port)
    assert addr == Address(129, 3)


def test_port_info():

    # test defaults
    info = PortInfo(client_id=11)

    assert info.client_id == 11
    assert info.port_id is None
    assert info.name == ""
    assert info.capability == PortCaps._NONE
    assert info.type == PortType.ANY
    assert info.midi_channels == 0
    assert info.midi_voices == 0
    assert info.synth_voices == 0
    assert info.read_use == 0
    assert info.write_use == 0
    assert info.timestamping is False
    assert info.timestamp_real is False
    assert info.timestamp_queue_id == 0
    assert Address(info) == Address(11, 0)

    # test initializing all attributes
    info = PortInfo(client_id=15,
                    port_id=17,
                    name="port_info_test2",
                    capability=PortCaps.WRITE | PortCaps.SUBS_WRITE,
                    type=PortType.MIDI_GENERIC | PortType.SYNTHESIZER,
                    midi_channels=1,
                    midi_voices=2,
                    synth_voices=3,
                    read_use=4,
                    write_use=5,
                    timestamping=True,
                    timestamp_real=True,
                    timestamp_queue_id=6)

    assert info.client_id == 15
    assert info.port_id == 17
    assert info.name == "port_info_test2"
    assert info.capability == PortCaps.WRITE | PortCaps.SUBS_WRITE
    assert info.type == PortType.MIDI_GENERIC | PortType.SYNTHESIZER
    assert info.midi_channels == 1
    assert info.midi_voices == 2
    assert info.synth_voices == 3
    assert info.read_use == 4
    assert info.write_use == 5
    assert info.timestamping is True
    assert info.timestamp_real is True
    assert info.timestamp_queue_id == 6
    assert Address(info) == Address(15, 17)

    # test _to_alsa (only some values are writable to the ALSA struct)
    alsa_info = info._to_alsa()

    assert alsa.snd_seq_port_info_get_client(alsa_info) == 15
    assert alsa.snd_seq_port_info_get_port(alsa_info) == 17
    assert ffi.string(alsa.snd_seq_port_info_get_name(alsa_info)) == b"port_info_test2"
    assert alsa.snd_seq_port_info_get_capability(alsa_info) == (
            alsa.SND_SEQ_PORT_CAP_WRITE | alsa.SND_SEQ_PORT_CAP_SUBS_WRITE)
    assert alsa.snd_seq_port_info_get_type(alsa_info) == (
            alsa.SND_SEQ_PORT_TYPE_MIDI_GENERIC | alsa.SND_SEQ_PORT_TYPE_SYNTHESIZER)
    assert alsa.snd_seq_port_info_get_midi_channels(alsa_info) == 1
    assert alsa.snd_seq_port_info_get_midi_voices(alsa_info) == 2
    assert alsa.snd_seq_port_info_get_synth_voices(alsa_info) == 3
    assert alsa.snd_seq_port_info_get_port_specified(alsa_info) == 1
    assert alsa.snd_seq_port_info_get_timestamping(alsa_info) == 1
    assert alsa.snd_seq_port_info_get_timestamp_real(alsa_info) == 1
    assert alsa.snd_seq_port_info_get_timestamp_queue(alsa_info) == 6

    # test _from_alsa (only the attributes we can set)
    info_p = ffi.new("snd_seq_port_info_t **")
    err = alsa.snd_seq_port_info_malloc(info_p)
    assert err >= 0
    alsa_info = ffi.gc(info_p[0], alsa.snd_seq_port_info_free)

    alsa.snd_seq_port_info_set_client(alsa_info, 115)
    alsa.snd_seq_port_info_set_port(alsa_info, 117)
    alsa.snd_seq_port_info_set_name(alsa_info, b"port_info_test3")
    alsa.snd_seq_port_info_set_capability(
            alsa_info,
            alsa.SND_SEQ_PORT_CAP_WRITE | alsa.SND_SEQ_PORT_CAP_SUBS_WRITE)
    alsa.snd_seq_port_info_set_type(
            alsa_info,
            alsa.SND_SEQ_PORT_TYPE_MIDI_GENERIC | alsa.SND_SEQ_PORT_TYPE_SYNTHESIZER)
    alsa.snd_seq_port_info_set_midi_channels(alsa_info, 11)
    alsa.snd_seq_port_info_set_midi_voices(alsa_info, 12)
    alsa.snd_seq_port_info_set_synth_voices(alsa_info, 13)
    alsa.snd_seq_port_info_set_port_specified(alsa_info, 1)
    alsa.snd_seq_port_info_set_timestamping(alsa_info, 1)
    alsa.snd_seq_port_info_set_timestamp_real(alsa_info, 1)
    alsa.snd_seq_port_info_set_timestamp_queue(alsa_info, 16)

    info = PortInfo._from_alsa(alsa_info)

    assert info.client_id == 115
    assert info.port_id == 117
    assert info.name == "port_info_test3"
    assert info.capability == PortCaps.WRITE | PortCaps.SUBS_WRITE
    assert info.type == PortType.MIDI_GENERIC | PortType.SYNTHESIZER
    assert info.midi_channels == 11
    assert info.midi_voices == 12
    assert info.synth_voices == 13
    assert info.timestamping is True
    assert info.timestamp_real is True
    assert info.timestamp_queue_id == 16


def test_port_info_sort_key():
    p0 = PortInfo(client_id=128, port_id=0, name="p0",
                  type=PortType.MIDI_GENERIC)
    p1 = PortInfo(client_id=128, port_id=1, name="p1",
                  type=PortType.SPECIFIC)
    p2 = PortInfo(client_id=128, port_id=2, name="p2",
                  type=PortType.MIDI_GENERIC | PortType.MIDI_GM)
    p3 = PortInfo(client_id=128, port_id=3, name="p3",
                  type=PortType.SPECIFIC)
    p4 = PortInfo(client_id=128, port_id=4, name="p4",
                  type=PortType.MIDI_GENERIC)
    p4.client_name = "Midi Through"

    p10 = PortInfo(client_id=129, port_id=0, name="p10",
                   type=PortType.MIDI_GENERIC)
    p11 = PortInfo(client_id=129, port_id=1, name="p11",
                   type=PortType.MIDI_GENERIC | PortType.SYNTHESIZER)

    k = get_port_info_sort_key([])
    assert k(p0) < k(p1)
    assert k(p1) < k(p2)
    assert k(p2) < k(p3)
    assert k(p3) < k(p4)
    assert k(p4) > k(p0)  # midi through always last

    assert k(p10) > k(p0)
    assert k(p10) > k(p1)
    assert k(p10) > k(p3)
    assert k(p11) > k(p10)
    assert k(p10) < k(p4)  # midi through always last
    assert k(p11) < k(p4)  # midi through always last

    k = get_port_info_sort_key([PortType.MIDI_GENERIC | PortType.SYNTHESIZER,
                                PortType.MIDI_GENERIC])
    assert k(p0) < k(p1)
    assert k(p1) > k(p2)
    assert k(p2) < k(p3)
    assert k(p3) < k(p4)  # midi through always last
    assert k(p4) > k(p0)  # midi through always last

    assert k(p10) > k(p0)
    assert k(p10) < k(p1)
    assert k(p10) < k(p3)
    assert k(p11) < k(p10)
    assert k(p10) < k(p4)  # midi through always last
    assert k(p11) < k(p4)  # midi through always last
