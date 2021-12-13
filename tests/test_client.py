
import pytest

from alsa_midi import SequencerALSAError, SequencerClient, SequencerStateError


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


def test_client_drain_output_nothing():
    client = SequencerClient("test")
    client.drain_output()
    client.close()


def test_client_drop_output_nothing():
    client = SequencerClient("test")
    client.drop_output()
    client.close()
