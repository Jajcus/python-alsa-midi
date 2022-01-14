
import errno

import pytest

from alsa_midi import ALSAError, Queue, QueueInfo, SequencerClient


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


@pytest.mark.require_alsa_seq
def test_queue_create_info(alsa_seq_state):
    client = SequencerClient("test_c")

    info = QueueInfo(name="queue name")
    queue = client.create_queue(info=info)

    alsa_seq_state.load()
    assert queue.queue_id in alsa_seq_state.queues
    alsa_queue = alsa_seq_state.queues[queue.queue_id]

    assert alsa_queue.client_id == client.client_id
    assert alsa_queue.name == "queue name"

    client.close()


@pytest.mark.require_alsa_seq
def test_queue_info(alsa_seq_state):
    client1 = SequencerClient("test_c1")
    client2 = SequencerClient("test_c2")
    queue1 = client1.create_queue("c1 queue")
    queue2 = client2.create_queue("c2 queue")

    info1 = queue1.get_info()

    assert isinstance(info1, QueueInfo)
    assert info1.queue_id == queue1.queue_id
    assert info1.name == "c1 queue"
    assert info1.owner == client1.client_id
    assert info1.locked is True
    assert isinstance(info1.flags, int)

    # information about queue owned by another client
    info2 = client1.get_queue_info(queue2.queue_id)
    assert info2.queue_id == queue2.queue_id
    assert info2.name == "c2 queue"
    assert info2.owner == client2.client_id
    assert info2.locked is True
    assert isinstance(info2.flags, int)

    info1_new = QueueInfo(name="new name 1", locked=False)
    queue1.set_info(info1_new)

    alsa_seq_state.load()
    alsa_queue = alsa_seq_state.queues[queue1.queue_id]
    assert alsa_queue.name == "new name 1"

    info2_new = QueueInfo(name="new name 2")
    with pytest.raises(ALSAError) as exc:
        client1.set_queue_info(queue2.queue_id, info2_new)
    assert exc.value.errnum == -errno.EPERM

    client1.close()
    client2.close()


@pytest.mark.require_alsa_seq
def test_query_named_queue():
    client1 = SequencerClient("test_c1")
    client2 = SequencerClient("test_c2")
    queue1 = client1.create_queue("c1 queue")
    queue2 = client2.create_queue("c2 queue")

    queue_id = client1.query_named_queue("c2 queue")
    assert queue_id == queue2.queue_id

    queue_id = client2.query_named_queue("c1 queue")
    assert queue_id == queue1.queue_id

    with pytest.raises(ALSAError) as exc:
        queue_id = client1.query_named_queue("no such queue")
    assert exc.value.errnum == -errno.EINVAL

    client1.close()
    client2.close()
