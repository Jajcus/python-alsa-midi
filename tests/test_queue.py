
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
        client1.query_named_queue("no such queue")
    assert exc.value.errnum == -errno.EINVAL

    client1.close()
    client2.close()


@pytest.mark.require_alsa_seq
def test_usage():
    client1 = SequencerClient("test_c1")
    client2 = SequencerClient("test_c2")
    queue1 = client1.create_queue("c1 queue")

    assert queue1.get_usage() is True

    queue1_c2 = Queue(client2, queue1.queue_id)

    assert queue1_c2.get_usage() is False

    queue1_c2.set_usage(True)

    assert queue1_c2.get_usage() is True

    queue1_c2.set_usage(False)

    assert queue1_c2.get_usage() is False

    client1.close()
    client2.close()


@pytest.mark.require_alsa_seq
def test_ownership(alsa_seq_state):
    client1 = SequencerClient("test_c1")
    client2 = SequencerClient("test_c2")
    queue1 = client1.create_queue("c1 queue1")
    queue2 = client1.create_queue("c1 queue2")
    queue3 = client2.create_queue("c2 queue3")

    assert queue1._own is True
    assert queue2._own is True
    assert queue3._own is True

    alsa_seq_state.load()
    assert queue1.queue_id in alsa_seq_state.queues
    assert queue2.queue_id in alsa_seq_state.queues
    assert queue3.queue_id in alsa_seq_state.queues

    queue1_c1 = client1.get_queue(queue1.queue_id)
    assert queue1_c1 is queue1
    assert queue1_c1._own is True
    assert queue1_c1.get_usage() is True

    queue1_c2 = client2.get_queue(queue1.queue_id)
    assert queue1_c2 is not queue1
    assert queue1_c2.queue_id == queue1.queue_id
    assert queue1_c2._own is False
    assert queue1_c2.get_usage() is True

    queue2_c1 = client1.get_named_queue("c1 queue2")
    assert queue2_c1 is queue2
    assert queue2_c1._own is True
    assert queue2_c1.get_usage() is True

    queue2_c2 = client2.get_named_queue("c1 queue2")
    assert queue2_c2 is not queue2
    assert queue2_c2.queue_id == queue2.queue_id
    assert queue2_c2._own is False
    assert queue2_c2.get_usage() is True

    queue2_c1_not_managed = Queue(client1, queue2.queue_id)
    assert queue2_c1_not_managed is not queue2
    assert queue2_c1_not_managed._own is None
    assert queue2_c2.get_usage() is True

    queue2_c2_not_managed = Queue(client2, queue2.queue_id)
    assert queue2_c2_not_managed is not queue2
    assert queue2_c2_not_managed.queue_id == queue2.queue_id
    assert queue2_c2_not_managed._own is None
    assert queue2_c2.get_usage() is True

    queue3_c1_not_managed = Queue(client1, queue3.queue_id)
    assert queue3_c1_not_managed is not queue3
    assert queue3_c1_not_managed._own is None
    assert queue3_c1_not_managed.get_usage() is False

    queue3_c2_not_managed = Queue(client2, queue3.queue_id)
    assert queue3_c2_not_managed is not queue3
    assert queue3_c2_not_managed.queue_id == queue3.queue_id
    assert queue3_c2_not_managed._own is None
    assert queue3_c2_not_managed.get_usage() is True

    # should not affect the queues
    queue3_c1_not_managed.close()
    del queue3_c2_not_managed
    alsa_seq_state.load()
    assert queue1.queue_id in alsa_seq_state.queues
    assert queue2.queue_id in alsa_seq_state.queues
    assert queue3.queue_id in alsa_seq_state.queues

    # destroys queue3
    queue3.close()
    alsa_seq_state.load()
    assert queue1.queue_id in alsa_seq_state.queues
    assert queue2.queue_id in alsa_seq_state.queues

    # no queue deleted
    del queue2_c1_not_managed
    alsa_seq_state.load()
    assert queue1.queue_id in alsa_seq_state.queues
    assert queue2.queue_id in alsa_seq_state.queues

    # still no queue deleted - reference held by queue2_c1
    queue2_id = queue2.queue_id
    del queue2
    alsa_seq_state.load()
    assert queue1.queue_id in alsa_seq_state.queues
    assert queue2_id in alsa_seq_state.queues

    # finally deleted - no more references
    del queue2_c1
    alsa_seq_state.load()
    assert queue1.queue_id in alsa_seq_state.queues
    assert queue2_id not in alsa_seq_state.queues

    # queue2_c2 now points to deleted queue
    with pytest.raises(ALSAError):
        queue2_c2.get_info()

    queue2_c2.close()

    # not deleting – it is owned by c1
    queue1_c2.close()
    alsa_seq_state.load()
    assert queue1.queue_id in alsa_seq_state.queues

    # now delete
    queue1.close()
    alsa_seq_state.load()
    assert queue1.queue_id not in alsa_seq_state.queues

    client1.close()
    client2.close()
