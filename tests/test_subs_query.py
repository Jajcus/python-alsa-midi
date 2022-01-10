
import errno

import pytest

from alsa_midi import Address, ALSAError, SequencerClient, SubscriptionQuery, SubscriptionQueryType


@pytest.mark.require_alsa_seq
def test_query_port_subscribers_bad_addr(alsa_seq_state):
    client = SequencerClient("test")
    alsa_seq_state.load()

    assert (99, 99) not in alsa_seq_state.ports

    query = SubscriptionQuery(Address(99, 99), SubscriptionQueryType.READ)

    with pytest.raises(ALSAError) as err:
        client.query_port_subscribers(query)

    assert err.value.errnum == -errno.ENXIO

    client.close()


@pytest.mark.require_alsa_seq
def test_query_port_subscribers():
    client = SequencerClient("test")
    p1 = client.create_port("p1")
    p2 = client.create_port("p2")
    other_client = SequencerClient("other")
    other_p1 = other_client.create_port("p1")
    other_p2 = other_client.create_port("p2")

    p1.connect_to(other_p1)
    p1.connect_from(other_p2)
    p2.connect_from(other_p1)
    p2.connect_from(other_p2)

    query = SubscriptionQuery(p1, SubscriptionQueryType.READ)
    sub = client.query_port_subscribers(query)
    assert sub.root == Address(p1)
    assert sub.type == SubscriptionQueryType.READ
    assert sub.index == 0
    assert sub.addr == Address(other_p1)
    assert sub.num_subs == 1
    assert sub.queue_id == 0
    assert sub.exlusive is False
    assert sub.time_update is False
    assert sub.time_real is False
    query.index += 1
    with pytest.raises(ALSAError) as exc:
        client.query_port_subscribers(query)
    assert exc.value.errnum == -errno.ENOENT

    query = SubscriptionQuery(p1, SubscriptionQueryType.WRITE)
    sub = client.query_port_subscribers(query)
    assert sub.root == Address(p1)
    assert sub.type == SubscriptionQueryType.WRITE
    assert sub.index == 0
    assert sub.addr == Address(other_p2)
    assert sub.num_subs == 1
    assert sub.queue_id == 0
    assert sub.exlusive is False
    assert sub.time_update is False
    assert sub.time_real is False
    query.index += 1
    with pytest.raises(ALSAError) as exc:
        client.query_port_subscribers(query)
    assert exc.value.errnum == -errno.ENOENT

    query = SubscriptionQuery(p2, SubscriptionQueryType.READ)
    with pytest.raises(ALSAError) as exc:
        client.query_port_subscribers(query)
    assert exc.value.errnum == -errno.ENOENT

    query = SubscriptionQuery(p2, SubscriptionQueryType.WRITE)
    sub = client.query_port_subscribers(query)
    assert sub.root == Address(p2)
    assert sub.type == SubscriptionQueryType.WRITE
    assert sub.index == 0
    assert sub.addr == Address(other_p1)
    assert sub.num_subs == 2
    assert sub.queue_id == 0
    assert sub.exlusive is False
    assert sub.time_update is False
    assert sub.time_real is False
    query.index += 1
    sub = client.query_port_subscribers(query)
    assert sub.root == Address(p2)
    assert sub.type == SubscriptionQueryType.WRITE
    assert sub.index == 1
    assert sub.addr == Address(other_p2)
    assert sub.num_subs == 2
    assert sub.queue_id == 0
    assert sub.exlusive is False
    assert sub.time_update is False
    assert sub.time_real is False
    query.index += 1
    with pytest.raises(ALSAError) as exc:
        client.query_port_subscribers(query)
    assert exc.value.errnum == -errno.ENOENT

    client.close()
    other_client.close()


@pytest.mark.require_alsa_seq
def test_list_port_subscribers_bad_addr(alsa_seq_state):
    client = SequencerClient("test")
    alsa_seq_state.load()

    assert (99, 99) not in alsa_seq_state.ports

    assert client.list_port_subscribers(Address(99, 99)) == []

    client.close()


@pytest.mark.require_alsa_seq
def test_list_port_subscribers():
    client = SequencerClient("test")
    p1 = client.create_port("p1")
    p2 = client.create_port("p2")
    other_client = SequencerClient("other")
    other_p1 = other_client.create_port("p1")
    other_p2 = other_client.create_port("p2")

    p1.connect_to(other_p1)
    p1.connect_from(other_p2)
    p2.connect_from(other_p1)
    p2.connect_from(other_p2)

    subs = client.list_port_subscribers(p1)

    assert len(subs) == 2

    sub = subs[0]
    assert sub.root == Address(p1)
    assert sub.type == SubscriptionQueryType.READ
    assert sub.addr == Address(other_p1)
    assert sub.queue_id == 0
    assert sub.exlusive is False
    assert sub.time_update is False
    assert sub.time_real is False

    sub = subs[1]
    assert sub.root == Address(p1)
    assert sub.type == SubscriptionQueryType.WRITE
    assert sub.index == 0
    assert sub.addr == Address(other_p2)
    assert sub.num_subs == 1
    assert sub.queue_id == 0
    assert sub.exlusive is False
    assert sub.time_update is False
    assert sub.time_real is False

    subs = p2.list_subscribers(SubscriptionQueryType.READ)
    assert subs == []

    subs = p2.list_subscribers(SubscriptionQueryType.WRITE)
    assert len(subs) == 2
    sub = subs[0]
    assert sub.root == Address(p2)
    assert sub.type == SubscriptionQueryType.WRITE
    assert sub.addr == Address(other_p1)
    assert sub.queue_id == 0
    assert sub.exlusive is False
    assert sub.time_update is False
    assert sub.time_real is False
    sub = subs[1]
    assert sub.root == Address(p2)
    assert sub.type == SubscriptionQueryType.WRITE
    assert sub.addr == Address(other_p2)
    assert sub.queue_id == 0
    assert sub.exlusive is False
    assert sub.time_update is False
    assert sub.time_real is False

    client.close()
    other_client.close()
