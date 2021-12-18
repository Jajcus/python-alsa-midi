

import pytest

from alsa_midi import Queue, SequencerClient


@pytest.mark.require_alsa_seq
def test_queue_create_close():
    client = SequencerClient("test_c")
    queue = client.create_queue()

    assert isinstance(queue, Queue)
    assert queue.client is client

    queue.close()

    assert queue.client is None

    # should do nothing now
    del queue


@pytest.mark.require_alsa_seq
def test_queue_create_del():
    client = SequencerClient("test_c")
    queue = client.create_queue()

    assert isinstance(queue, Queue)
    assert queue.client is client

    del queue


@pytest.mark.require_alsa_seq
def test_queue_create_close_alsa(alsa_seq_state):
    client = SequencerClient("test_c")
    queue = client.create_queue()

    alsa_seq_state.load()
    assert queue.queue_id in alsa_seq_state.queues
    alsa_queue = alsa_seq_state.queues[queue.queue_id]

    assert alsa_queue.client_id == client.client_id

    queue.close()

    alsa_seq_state.load()
    assert queue.queue_id not in alsa_seq_state.queues


@pytest.mark.require_alsa_seq
def test_queue_create_del_alsa(alsa_seq_state):
    client = SequencerClient("test_c")
    queue = client.create_queue()

    queue_id = queue.queue_id

    alsa_seq_state.load()
    assert queue_id in alsa_seq_state.queues
    alsa_queue = alsa_seq_state.queues[queue_id]

    assert alsa_queue.client_id == client.client_id

    del queue

    alsa_seq_state.load()
    assert queue_id not in alsa_seq_state.queues


@pytest.mark.require_alsa_seq
def test_queue_create_named_alsa(alsa_seq_state):
    client = SequencerClient("test_c")
    queue = client.create_queue("queue name")

    alsa_seq_state.load()
    assert queue.queue_id in alsa_seq_state.queues
    alsa_queue = alsa_seq_state.queues[queue.queue_id]

    assert alsa_queue.client_id == client.client_id
    assert alsa_queue.name == "queue name"

    queue.close()

    alsa_seq_state.load()
    assert queue.queue_id not in alsa_seq_state.queues
