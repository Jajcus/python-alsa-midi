
import asyncio

import pytest

from alsa_midi import READ_PORT, Address, AsyncSequencerClient, NoteOffEvent, NoteOnEvent


@pytest.mark.require_alsa_seq
@pytest.mark.asyncio
async def test_client_drain_output_nothing(asyncio_latency_check):
    client = AsyncSequencerClient("test")
    await client.drain_output()
    await client.aclose()
    assert (await asyncio_latency_check.get_max() < 0.5)


@pytest.mark.require_alsa_seq
@pytest.mark.asyncio
async def test_client_drop_output_nothing(asyncio_latency_check):
    client = AsyncSequencerClient("test")
    client.drop_output()
    await client.aclose()
    assert (await asyncio_latency_check.get_max() < 0.5)


@pytest.mark.require_alsa_seq
@pytest.mark.asyncio
async def test_event_output(aseqdump, asyncio_latency_check):

    # prepare the client and port
    client = AsyncSequencerClient("test")
    port = client.create_port("output", READ_PORT)
    port.connect_to(aseqdump.port)

    e1 = NoteOnEvent(note=64)
    e2 = NoteOffEvent(note=64)

    # send events to the buffer, check if buffer grows as expected
    r1 = await client.event_output(e1)
    assert r1 > 0
    r2 = await client.event_output(e2)
    assert r2 > r1

    # should not be delivered yet
    our_events = [line for addr, line in aseqdump.output if addr == Address(port)]
    assert len(our_events) == 0

    # deliver now
    await client.drain_output()

    # wait until aseqdump catches them
    for _ in range(10):
        our_events = [line for addr, line in aseqdump.output if addr == Address(port)]
        if len(our_events) >= 2:
            break
        await asyncio.sleep(0.1)

    # verify output
    assert len(our_events) == 2

    assert "Note on" in our_events[0]
    assert "Note off" in our_events[1]

    aseqdump.close()
    await client.aclose()

    assert (await asyncio_latency_check.get_max() < 1)
