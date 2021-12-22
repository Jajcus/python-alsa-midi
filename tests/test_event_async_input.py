
import asyncio
import os
import subprocess
import time

import pytest

from alsa_midi import WRITE_PORT, Address, ALSAError, AsyncSequencerClient, Event
from alsa_midi.client import SequencerClientBase

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(TESTS_DIR, "data")


@pytest.mark.require_tool("aplaymidi")
@pytest.mark.require_alsa_seq
@pytest.mark.asyncio
async def test_event_input(asyncio_latency_check):
    client = AsyncSequencerClient("test")
    port = client.create_port("input", WRITE_PORT)

    # flush any 'port connect' events that could been emitted by some session
    # managers auto-connecting stuff
    await asyncio.sleep(0.2)
    client.drop_input()

    # should fail with EAGAIN
    with pytest.raises(ALSAError):
        SequencerClientBase.event_input(client)

    # should block for 0.5s
    start = time.monotonic()
    event = await client.event_input(timeout=0.5)
    assert event is None
    assert time.monotonic() - start >= 0.5

    # play a midi file to our port
    await asyncio_latency_check.stop()
    filename = os.path.join(DATA_DIR, "c_major.mid")
    cmd = ["aplaymidi", "-p", str(Address(port)), "-d", "0", filename]
    player = subprocess.Popen(cmd)
    await asyncio_latency_check.cont()

    events = []
    # 1 port subscribe, 8 note-on,  8 note-off, 1 port unsubscribe
    for _ in range(18):
        event = await client.event_input(timeout=2)
        assert isinstance(event, Event)
        events.append(event)

    # should block for 0.5s (no more events)
    start = time.monotonic()
    event = await client.event_input(timeout=0.5)
    assert event is None
    assert time.monotonic() - start >= 0.5

    await asyncio_latency_check.stop()
    player.wait()
    await asyncio_latency_check.cont()

    assert (await asyncio_latency_check.get_max()) < 0.4
