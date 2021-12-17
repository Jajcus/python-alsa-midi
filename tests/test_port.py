
from typing import Any

import pytest

from alsa_midi import (SequencerAddress, SequencerClient, SequencerPort, SequencerPortCaps,
                       SequencerPortInfo, SequencerPortType, alsa, ffi)


@pytest.mark.require_alsa_seq
def test_port_create_close():
    client = SequencerClient("test_c")
    port = client.create_port("test_p")

    assert isinstance(port, SequencerPort)
    assert port.client is client

    port.close()

    assert port.client is None

    # should do nothing now
    del port


@pytest.mark.require_alsa_seq
def test_port_create_del():
    client = SequencerClient("test_c")
    port = client.create_port("test_p")

    assert isinstance(port, SequencerPort)
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


def test_port_as_address():
    class ClientMock:
        def __init__(self, client_id):
            self.client_id = client_id
            self.handle = None

    client: Any = ClientMock(129)
    port = SequencerPort(client, 3)

    assert port.client_id == 129
    assert port.port_id == 3

    addr = SequencerAddress(port)
    assert addr == SequencerAddress(129, 3)


def test_port_info():

    # test defaults
    info = SequencerPortInfo(client_id=11)

    assert info.client_id == 11
    assert info.port_id == 0
    assert info.name == ""
    assert info.capability == SequencerPortCaps._NONE
    assert info.type == SequencerPortType._NONE
    assert info.midi_channels == 0
    assert info.midi_voices == 0
    assert info.synth_voices == 0
    assert info.read_use == 0
    assert info.write_use == 0
    assert info.port_specified is False
    assert info.timestamping is False
    assert info.timestamp_real is False
    assert info.timestamp_queue_id == 0
    assert SequencerAddress(info) == SequencerAddress(11, 0)

    # test initializing all attributes
    info = SequencerPortInfo(client_id=15,
                             port_id=17,
                             name="port_info_test2",
                             capability=SequencerPortCaps.WRITE | SequencerPortCaps.SUBS_WRITE,
                             type=SequencerPortType.MIDI_GENERIC | SequencerPortType.SYNTHESIZER,
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
    assert info.capability == SequencerPortCaps.WRITE | SequencerPortCaps.SUBS_WRITE
    assert info.type == SequencerPortType.MIDI_GENERIC | SequencerPortType.SYNTHESIZER
    assert info.midi_channels == 1
    assert info.midi_voices == 2
    assert info.synth_voices == 3
    assert info.read_use == 4
    assert info.write_use == 5
    assert info.port_specified is True
    assert info.timestamping is True
    assert info.timestamp_real is True
    assert info.timestamp_queue_id == 6
    assert SequencerAddress(info) == SequencerAddress(15, 17)

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
    alsa_info = info_p[0]

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

    info = SequencerPortInfo._from_alsa(alsa_info)

    assert info.client_id == 115
    assert info.port_id == 117
    assert info.name == "port_info_test3"
    assert info.capability == SequencerPortCaps.WRITE | SequencerPortCaps.SUBS_WRITE
    assert info.type == SequencerPortType.MIDI_GENERIC | SequencerPortType.SYNTHESIZER
    assert info.midi_channels == 11
    assert info.midi_voices == 12
    assert info.synth_voices == 13
    assert info.port_specified is True
    assert info.timestamping is True
    assert info.timestamp_real is True
    assert info.timestamp_queue_id == 16
