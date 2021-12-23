
import os
import subprocess
import time

import pytest

from alsa_midi import (WRITE_PORT, Address, ALSAError, Event, EventType, MidiBytesEvent,
                       SequencerClient)
from alsa_midi.client import SequencerClientBase
from alsa_midi.event import PortSubscribedEvent, PortUnsubscribedEvent

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(TESTS_DIR, "data")


@pytest.mark.require_tool("aplaymidi")
@pytest.mark.require_alsa_seq
def test_event_input():
    client = SequencerClient("test")
    port = client.create_port("input", WRITE_PORT)

    # flush any 'port connect' events that could been emitted by some session
    # managers auto-connecting stuff
    time.sleep(0.2)
    client.drop_input()

    # should fail with EAGAIN
    with pytest.raises(ALSAError):
        SequencerClientBase.event_input(client)

    # should block for 0.5s
    start = time.monotonic()
    event = client.event_input(timeout=0.5)
    assert event is None
    assert time.monotonic() - start >= 0.5

    # play a midi file to our port
    filename = os.path.join(DATA_DIR, "c_major.mid")
    cmd = ["aplaymidi", "-p", str(Address(port)), "-d", "0", filename]
    player = subprocess.Popen(cmd)

    events = []
    for _ in range(18):
        event = client.event_input(timeout=1)
        assert isinstance(event, Event)
        events.append(event)

    # should block for 0.5s (no more events)
    start = time.monotonic()
    event = client.event_input(timeout=0.5)
    assert event is None
    assert time.monotonic() - start >= 0.5

    player.wait()


@pytest.mark.require_tool("aplaymidi")
@pytest.mark.require_alsa_seq
def test_event_input_bytes():
    client = SequencerClient("test")
    port = client.create_port("input", WRITE_PORT)

    # flush any 'port connect' events that could been emitted by some session
    # managers auto-connecting stuff
    time.sleep(0.2)
    client.drop_input()

    # should fail with EAGAIN
    with pytest.raises(ALSAError):
        SequencerClientBase.event_input(client)

    # should block for 0.5s
    start = time.monotonic()
    event = client.event_input(timeout=0.5)
    assert event is None
    assert time.monotonic() - start >= 0.5

    # play a midi file to our port
    filename = os.path.join(DATA_DIR, "c_major.mid")
    cmd = ["aplaymidi", "-p", str(Address(port)), "-d", "0", filename]
    player = subprocess.Popen(cmd)

    event = client.event_input(timeout=1, prefer_bytes=True)
    assert isinstance(event, PortSubscribedEvent)

    for _ in range(8):
        event = client.event_input(timeout=1, prefer_bytes=True)
        assert isinstance(event, MidiBytesEvent)
        assert event.type == EventType.NOTEON
        assert len(event.midi_bytes) == 3
        assert event.midi_bytes[0] == 0x90

        event = client.event_input(timeout=1, prefer_bytes=True)
        assert isinstance(event, MidiBytesEvent)
        assert event.type == EventType.NOTEOFF
        assert event.midi_bytes[0] == 0x80

    event = client.event_input(timeout=1, prefer_bytes=True)
    assert isinstance(event, PortUnsubscribedEvent)

    # should block for 0.5s (no more events)
    start = time.monotonic()
    event = client.event_input(timeout=0.5)
    assert event is None
    assert time.monotonic() - start >= 0.5

    player.wait()
