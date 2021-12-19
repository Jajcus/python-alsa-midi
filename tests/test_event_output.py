
import time

import pytest

from alsa_midi import READ_PORT, Address, NoteOffEvent, NoteOnEvent, SequencerClient


@pytest.mark.require_alsa_seq
def test_client_drain_output_nothing():
    client = SequencerClient("test")
    client.drain_output()
    client.close()


@pytest.mark.require_alsa_seq
def test_client_drop_output_nothing():
    client = SequencerClient("test")
    client.drop_output()
    client.close()


@pytest.mark.require_alsa_seq
def test_event_output(aseqdump):

    # prepare the client and port
    client = SequencerClient("test")
    port = client.create_port("output", READ_PORT)
    port.connect_to(aseqdump.port)

    e1 = NoteOnEvent(note=64)
    e2 = NoteOffEvent(note=64)

    # send events to the buffer, check if buffer grows as expected
    r1 = client.event_output(e1)
    assert r1 > 0
    r2 = client.event_output(e2)
    assert r2 > r1

    # should not be delivered yet
    our_events = [line for addr, line in aseqdump.output if addr == Address(port)]
    assert len(our_events) == 0

    # deliver now
    client.drain_output()

    # wait until aseqdump catches them
    for _ in range(10):
        our_events = [line for addr, line in aseqdump.output if addr == Address(port)]
        if len(our_events) >= 2:
            break
        time.sleep(0.1)

    # verify output
    assert len(our_events) == 2

    assert "Note on" in our_events[0]
    assert "Note off" in our_events[1]

    aseqdump.close()
    client.close()
