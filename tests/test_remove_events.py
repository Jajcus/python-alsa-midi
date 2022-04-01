
import pytest

from alsa_midi import (READ_PORT, NoteOffEvent, NoteOnEvent, RemoveCondition, RemoveEvents,
                       SequencerClient)


@pytest.mark.require_alsa_seq
def test_remove_events_defaults():
    client = SequencerClient("test")
    client.create_port("output", READ_PORT)

    pending1 = client.event_output_pending()
    assert pending1 == 0

    e1 = NoteOnEvent(note=64)
    e2 = NoteOffEvent(note=64)
    client.event_output(e1)
    client.event_output(e2)

    pending2 = client.event_output_pending()
    assert pending2 > 0

    # should do nothing – neither input or output to be removed
    client.remove_events()

    pending3 = client.event_output_pending()
    assert pending3 == pending2

    client.close()


@pytest.mark.require_alsa_seq
def test_remove_events_object_defaults():
    client = SequencerClient("test")
    client.create_port("output", READ_PORT)

    pending1 = client.event_output_pending()
    assert pending1 == 0

    e1 = NoteOnEvent(note=64)
    e2 = NoteOffEvent(note=64)
    client.event_output(e1)
    client.event_output(e2)

    pending2 = client.event_output_pending()
    assert pending2 > 0

    # should do nothing – neither input or output to be removed
    client.remove_events(RemoveEvents())

    pending3 = client.event_output_pending()
    assert pending3 == pending2

    client.close()


@pytest.mark.require_alsa_seq
def test_remove_outpu_events():
    client = SequencerClient("test")
    client.create_port("output", READ_PORT)

    pending1 = client.event_output_pending()
    assert pending1 == 0

    e1 = NoteOnEvent(note=64)
    e2 = NoteOffEvent(note=64)
    client.event_output(e1)
    client.event_output(e2)

    pending2 = client.event_output_pending()
    assert pending2 > 0

    client.remove_events(RemoveCondition.OUTPUT)

    pending3 = client.event_output_pending()
    assert pending3 == 0

    client.close()


@pytest.mark.require_alsa_seq
def test_remove_output_events_object():
    client = SequencerClient("test")
    client.create_port("output", READ_PORT)

    pending1 = client.event_output_pending()
    assert pending1 == 0

    e1 = NoteOnEvent(note=64)
    e2 = NoteOffEvent(note=64)
    client.event_output(e1)
    client.event_output(e2)

    pending2 = client.event_output_pending()
    assert pending2 > 0

    re = RemoveEvents(condition=RemoveCondition.OUTPUT)
    client.remove_events(re)

    pending3 = client.event_output_pending()
    assert pending3 == 0

    client.close()

# TODO: more tests, to test all the scenarios actually supported by ALSA
