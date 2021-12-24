
import pytest

from alsa_midi import (ActiveSensingEvent, Address, BounceEvent, ChannelPressureEvent,
                       ClientChangeEvent, ClientExitEvent, ClientStartEvent, ClockEvent,
                       ContinueEvent, Control14BitChangeEvent, ControlChangeEvent, EchoEvent,
                       Event, EventFlags, EventType, KeyPressureEvent, KeySignatureEvent,
                       MidiBytesEvent, NonRegisteredParameterChangeEvent, NoteEvent, NoteOffEvent,
                       NoteOnEvent, OSSEvent, PitchBendEvent, PortChangeEvent, PortExitEvent,
                       PortStartEvent, PortSubscribedEvent, PortUnsubscribedEvent,
                       ProgramChangeEvent, QueueSkewEvent, RealTime,
                       RegisteredParameterChangeEvent, ResetEvent, ResultEvent,
                       SetQueuePositionTickEvent, SetQueuePositionTimeEvent, SetQueueTempoEvent,
                       SongPositionPointerEvent, SongSelectEvent, StartEvent, StopEvent,
                       SyncPositionChangedEvent, SysExEvent, SystemEvent, TickEvent,
                       TimeSignatureEvent, TuneRequestEvent, UserVar0Event, UserVar1Event,
                       UserVar2Event, UserVar3Event, alsa, ffi)
from alsa_midi.event import ExternalDataEventBase


def test_event():
    event = Event()
    assert event.type is None
    assert event.flags == 0
    assert event.tag == 0
    assert event.queue_id is None
    assert event.time is None
    assert event.tick is None
    assert event.source is None
    assert event.dest is None
    assert event.relative is None
    assert event.raw_data is None
    assert repr(event) == "<Event unknown>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == 0
    assert alsa_event.flags == 0
    assert alsa_event.tag == 0
    assert alsa_event.queue == alsa.SND_SEQ_QUEUE_DIRECT
    assert alsa_event.time.tick == 0
    assert alsa_event.time.time.tv_sec == 0
    assert alsa_event.time.time.tv_nsec == 0
    assert alsa_event.source.client == 0
    assert alsa_event.source.port == 0
    assert alsa_event.dest.client == alsa.SND_SEQ_ADDRESS_SUBSCRIBERS
    assert alsa_event.dest.port == 0
    assert bytes(ffi.buffer(alsa_event.data.raw8.d)) == b"\x00" * ffi.sizeof(alsa_event.data)
    assert repr(event) == "<Event unknown>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event,
                            queue=11,
                            port=12,
                            dest=Address(13, 14))
    assert result is alsa_event
    assert alsa_event.type == 0
    assert alsa_event.flags == 0
    assert alsa_event.tag == 0
    assert alsa_event.queue == 11
    assert alsa_event.time.tick == 0
    assert alsa_event.time.time.tv_sec == 0
    assert alsa_event.time.time.tv_nsec == 0
    assert alsa_event.source.client == 0
    assert alsa_event.source.port == 12
    assert alsa_event.dest.client == 13
    assert alsa_event.dest.port == 14
    assert repr(event) == "<Event unknown>"

    event = Event(type=EventType.NOTEON,
                  flags=EventFlags.PRIORITY_HIGH,
                  tag=1,
                  queue_id=2,
                  time=RealTime(3, 4),
                  source=(5, 6),
                  dest=(7, 8),
                  relative=True,
                  raw_data=b"abcde"
                  )
    assert event.type == EventType.NOTEON
    assert event.flags == EventFlags.PRIORITY_HIGH
    assert event.tag == 1
    assert event.queue_id == 2
    assert event.time == RealTime(3, 4)
    assert event.tick is None
    assert event.source == Address(5, 6)
    assert event.dest == Address(7, 8)
    assert event.relative is True
    assert event.raw_data == b"abcde"
    assert repr(event) == "<Event NOTEON>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_NOTEON
    assert EventFlags(alsa_event.flags) == (EventFlags.PRIORITY_HIGH | EventFlags.TIME_MODE_REL
                                            | EventFlags.TIME_STAMP_REAL)
    assert alsa_event.tag == 1
    assert alsa_event.queue == 2
    assert alsa_event.time.time.tv_sec == 3
    assert alsa_event.time.time.tv_nsec == 4
    assert alsa_event.source.client == 5
    assert alsa_event.source.port == 6
    assert alsa_event.dest.client == 7
    assert alsa_event.dest.port == 8

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event,
                            queue=11,
                            port=12,
                            dest=Address(13, 14))
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_NOTEON
    assert EventFlags(alsa_event.flags) == (EventFlags.PRIORITY_HIGH | EventFlags.TIME_MODE_REL
                                            | EventFlags.TIME_STAMP_REAL)
    assert alsa_event.tag == 1
    assert alsa_event.queue == 11
    assert alsa_event.time.time.tv_sec == 3
    assert alsa_event.time.time.tv_nsec == 4
    assert alsa_event.source.client == 0
    assert alsa_event.source.port == 12
    assert alsa_event.dest.client == 13
    assert alsa_event.dest.port == 14

    with pytest.raises(ValueError):
        event = Event(type=EventType.NOTEOFF,
                      time=0.1,
                      tick=17,
                      )


def test_event_from_alsa():
    alsa_event = ffi.new("snd_seq_event_t *")
    event = Event._from_alsa(alsa_event)
    assert event.type == 0
    assert event.flags == 0
    assert event.tag == 0
    assert event.queue_id == 0
    assert event.time is None
    assert event.tick == 0
    assert event.source == Address(0, 0)
    assert event.dest == Address(0, 0)
    assert event.relative is False
    assert event.raw_data == b"\x00" * ffi.sizeof(alsa_event.data)
    assert repr(event) == "<Event SYSTEM>"

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_NOTEOFF
    alsa_event.flags = alsa.SND_SEQ_TIME_STAMP_REAL | alsa.SND_SEQ_TIME_MODE_REL
    alsa_event.tag = 5
    alsa_event.queue = 6
    alsa_event.time.time.tv_sec = 7
    alsa_event.time.time.tv_nsec = 8
    alsa_event.source.client = 9
    alsa_event.source.port = 10
    alsa_event.dest.client = 11
    alsa_event.dest.port = 12
    ffi.buffer(alsa_event.data.raw8.d)[:] = b"x" * ffi.sizeof(alsa_event.data)

    event = Event._from_alsa(alsa_event)
    assert event.type == EventType.NOTEOFF
    assert event.flags == alsa.SND_SEQ_TIME_STAMP_REAL | alsa.SND_SEQ_TIME_MODE_REL
    assert event.tag == 5
    assert event.queue_id == 6
    assert event.time == RealTime(7, 8)
    assert event.tick is None
    assert event.source == Address(9, 10)
    assert event.dest == Address(11, 12)
    assert event.relative is True
    assert event.raw_data == b"x" * ffi.sizeof(alsa_event.data)
    assert repr(event) == "<Event NOTEOFF>"


def test_midi_bytest_event():
    event = MidiBytesEvent(b"abcde", tag=5)
    assert isinstance(event, Event)
    assert event.tag == 5
    assert event.midi_bytes == b"abcde"
    assert repr(event) == "<MidiBytesEvent 61 62 63 64 65>"

    event = MidiBytesEvent([0x00, 0x01], tag=6)
    assert isinstance(event, Event)
    assert event.tag == 6
    assert event.midi_bytes == b"\x00\x01"
    assert repr(event) == "<MidiBytesEvent 00 01>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == 0
    assert alsa_event.tag == 6

    # that is to be filled separately
    assert bytes(ffi.buffer(alsa_event.data.raw8.d)) == b"\x00" * ffi.sizeof(alsa_event.data)

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_NOTEOFF
    alsa_event.flags = alsa.SND_SEQ_TIME_STAMP_REAL | alsa.SND_SEQ_TIME_MODE_REL
    alsa_event.tag = 5
    alsa_event.queue = 6
    alsa_event.time.time.tv_sec = 7
    alsa_event.time.time.tv_nsec = 8
    alsa_event.source.client = 9
    alsa_event.source.port = 10
    alsa_event.dest.client = 11
    alsa_event.dest.port = 12
    ffi.buffer(alsa_event.data.raw8.d)[:] = b"x" * ffi.sizeof(alsa_event.data)

    event = MidiBytesEvent._from_alsa(alsa_event, midi_bytes=b"abcd")
    assert isinstance(event, MidiBytesEvent)
    assert event.type == EventType.NOTEOFF
    assert event.flags == alsa.SND_SEQ_TIME_STAMP_REAL | alsa.SND_SEQ_TIME_MODE_REL
    assert event.tag == 5
    assert event.queue_id == 6
    assert event.time == RealTime(7, 8)
    assert event.tick is None
    assert event.source == Address(9, 10)
    assert event.dest == Address(11, 12)
    assert event.relative is True
    assert event.raw_data == b"x" * ffi.sizeof(alsa_event.data)
    assert repr(event) == "<MidiBytesEvent 61 62 63 64>"


def test_system_event():
    event = SystemEvent(event=1, result=2, tag=3)
    assert isinstance(event, SystemEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.SYSTEM
    assert event.event == 1
    assert event.result == 2
    assert event.tag == 3
    assert repr(event) == "<SystemEvent event=1 result=2>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_SYSTEM
    assert alsa_event.data.result.event == 1
    assert alsa_event.data.result.result == 2
    assert alsa_event.tag == 3

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_SYSTEM
    alsa_event.tag = 5
    alsa_event.data.result.event = 6
    alsa_event.data.result.result = 7

    event = SystemEvent._from_alsa(alsa_event)
    assert isinstance(event, SystemEvent)
    assert event.type == EventType.SYSTEM
    assert event.tag == 5
    assert event.event == 6
    assert event.result == 7
    assert repr(event) == "<SystemEvent event=6 result=7>"


def test_result_event():
    event = ResultEvent(event=1, result=2, tag=3)
    assert isinstance(event, ResultEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.RESULT
    assert event.event == 1
    assert event.result == 2
    assert event.tag == 3
    assert repr(event) == "<ResultEvent event=1 result=2>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_RESULT
    assert alsa_event.data.result.event == 1
    assert alsa_event.data.result.result == 2
    assert alsa_event.tag == 3

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_RESULT
    alsa_event.tag = 5
    alsa_event.data.result.event = 6
    alsa_event.data.result.result = 7

    event = ResultEvent._from_alsa(alsa_event)
    assert isinstance(event, ResultEvent)
    assert event.type == EventType.RESULT

    assert event.tag == 5
    assert event.event == 6
    assert event.result == 7
    assert repr(event) == "<ResultEvent event=6 result=7>"


def test_note_event():
    event = NoteEvent(note=61, tag=3)
    assert isinstance(event, NoteEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.NOTE
    assert event.note == 61
    assert event.channel == 0
    assert event.velocity == 127
    assert event.off_velocity == 0
    assert event.duration == 0
    assert repr(event) == "<NoteEvent channel=0 note=61 velocity=127 duration=0 off_velocity=0>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_NOTE
    assert alsa_event.data.note.note == 61
    assert alsa_event.data.note.channel == 0
    assert alsa_event.data.note.velocity == 127
    assert alsa_event.data.note.off_velocity == 0
    assert alsa_event.data.note.duration == 0
    assert alsa_event.tag == 3

    event = NoteEvent(note=62, channel=5, velocity=6, duration=7, off_velocity=8, tag=9)
    assert isinstance(event, NoteEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.NOTE
    assert event.note == 62
    assert event.channel == 5
    assert event.velocity == 6
    assert event.duration == 7
    assert event.off_velocity == 8
    assert repr(event) == "<NoteEvent channel=5 note=62 velocity=6 duration=7 off_velocity=8>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_NOTE
    assert alsa_event.data.note.note == 62
    assert alsa_event.data.note.channel == 5
    assert alsa_event.data.note.velocity == 6
    assert alsa_event.data.note.duration == 7
    assert alsa_event.data.note.off_velocity == 8
    assert alsa_event.tag == 9

    event = NoteEvent(62, 5, 6, 7, 8, tag=9)
    assert isinstance(event, NoteEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.NOTE
    assert event.note == 62
    assert event.channel == 5
    assert event.velocity == 6
    assert event.duration == 7
    assert event.off_velocity == 8
    assert repr(event) == "<NoteEvent channel=5 note=62 velocity=6 duration=7 off_velocity=8>"

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_NOTE
    alsa_event.tag = 5
    alsa_event.data.note.note = 63
    alsa_event.data.note.channel = 5
    alsa_event.data.note.velocity = 6
    alsa_event.data.note.duration = 7
    alsa_event.data.note.off_velocity = 8

    event = NoteEvent._from_alsa(alsa_event)
    assert isinstance(event, NoteEvent)
    assert event.type == EventType.NOTE
    assert event.tag == 5
    assert event.note == 63
    assert event.channel == 5
    assert event.velocity == 6
    assert event.duration == 7
    assert event.off_velocity == 8
    assert repr(event) == "<NoteEvent channel=5 note=63 velocity=6 duration=7 off_velocity=8>"


def test_note_on_event():
    event = NoteOnEvent(note=61, tag=3)
    assert isinstance(event, NoteOnEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.NOTEON
    assert event.note == 61
    assert event.channel == 0
    assert event.velocity == 127
    assert repr(event) == "<NoteOnEvent channel=0 note=61 velocity=127>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_NOTEON
    assert alsa_event.data.note.note == 61
    assert alsa_event.data.note.channel == 0
    assert alsa_event.data.note.velocity == 127
    assert alsa_event.tag == 3

    event = NoteOnEvent(note=62, channel=5, velocity=6, tag=9)
    assert isinstance(event, NoteOnEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.NOTEON
    assert event.note == 62
    assert event.channel == 5
    assert event.velocity == 6
    assert repr(event) == "<NoteOnEvent channel=5 note=62 velocity=6>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_NOTEON
    assert alsa_event.data.note.note == 62
    assert alsa_event.data.note.channel == 5
    assert alsa_event.data.note.velocity == 6
    assert alsa_event.tag == 9

    event = NoteOnEvent(62, 5, 6, tag=9)
    assert isinstance(event, NoteOnEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.NOTEON
    assert event.note == 62
    assert event.channel == 5
    assert event.velocity == 6
    assert repr(event) == "<NoteOnEvent channel=5 note=62 velocity=6>"

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_NOTEON
    alsa_event.tag = 5
    alsa_event.data.note.note = 63
    alsa_event.data.note.channel = 5
    alsa_event.data.note.velocity = 6

    event = NoteOnEvent._from_alsa(alsa_event)
    assert isinstance(event, NoteOnEvent)
    assert event.type == EventType.NOTEON
    assert event.tag == 5
    assert event.note == 63
    assert event.channel == 5
    assert event.velocity == 6
    assert repr(event) == "<NoteOnEvent channel=5 note=63 velocity=6>"


def test_note_off_event():
    event = NoteOffEvent(note=61, tag=3)
    assert isinstance(event, NoteOffEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.NOTEOFF
    assert event.note == 61
    assert event.channel == 0
    assert event.velocity == 127
    assert repr(event) == "<NoteOffEvent channel=0 note=61 velocity=127>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_NOTEOFF
    assert alsa_event.data.note.note == 61
    assert alsa_event.data.note.channel == 0
    assert alsa_event.data.note.velocity == 127
    assert alsa_event.tag == 3

    event = NoteOffEvent(note=62, channel=5, velocity=6, tag=9)
    assert isinstance(event, NoteOffEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.NOTEOFF
    assert event.note == 62
    assert event.channel == 5
    assert event.velocity == 6
    assert repr(event) == "<NoteOffEvent channel=5 note=62 velocity=6>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_NOTEOFF
    assert alsa_event.data.note.note == 62
    assert alsa_event.data.note.channel == 5
    assert alsa_event.data.note.velocity == 6
    assert alsa_event.tag == 9

    event = NoteOffEvent(62, 5, 6, tag=9)
    assert isinstance(event, NoteOffEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.NOTEOFF
    assert event.note == 62
    assert event.channel == 5
    assert event.velocity == 6
    assert repr(event) == "<NoteOffEvent channel=5 note=62 velocity=6>"

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_NOTEOFF
    alsa_event.tag = 5
    alsa_event.data.note.note = 63
    alsa_event.data.note.channel = 5
    alsa_event.data.note.velocity = 6

    event = NoteOffEvent._from_alsa(alsa_event)
    assert isinstance(event, NoteOffEvent)
    assert event.type == EventType.NOTEOFF
    assert event.tag == 5
    assert event.note == 63
    assert event.channel == 5
    assert event.velocity == 6
    assert repr(event) == "<NoteOffEvent channel=5 note=63 velocity=6>"


def test_key_pressure_event():
    event = KeyPressureEvent(note=61, tag=3)
    assert isinstance(event, KeyPressureEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.KEYPRESS
    assert event.note == 61
    assert event.channel == 0
    assert event.velocity == 127
    assert repr(event) == "<KeyPressureEvent channel=0 note=61 velocity=127>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_KEYPRESS
    assert alsa_event.data.note.note == 61
    assert alsa_event.data.note.channel == 0
    assert alsa_event.data.note.velocity == 127
    assert alsa_event.tag == 3

    event = KeyPressureEvent(note=62, channel=5, velocity=6, tag=9)
    assert isinstance(event, KeyPressureEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.KEYPRESS
    assert event.note == 62
    assert event.channel == 5
    assert event.velocity == 6
    assert repr(event) == "<KeyPressureEvent channel=5 note=62 velocity=6>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_KEYPRESS
    assert alsa_event.data.note.note == 62
    assert alsa_event.data.note.channel == 5
    assert alsa_event.data.note.velocity == 6
    assert alsa_event.tag == 9

    event = KeyPressureEvent(62, 5, 6, tag=9)
    assert isinstance(event, KeyPressureEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.KEYPRESS
    assert event.note == 62
    assert event.channel == 5
    assert event.velocity == 6
    assert repr(event) == "<KeyPressureEvent channel=5 note=62 velocity=6>"

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_KEYPRESS
    alsa_event.tag = 5
    alsa_event.data.note.note = 63
    alsa_event.data.note.channel = 5
    alsa_event.data.note.velocity = 6

    event = KeyPressureEvent._from_alsa(alsa_event)
    assert isinstance(event, KeyPressureEvent)
    assert event.type == EventType.KEYPRESS
    assert event.tag == 5
    assert event.note == 63
    assert event.channel == 5
    assert event.velocity == 6
    assert repr(event) == "<KeyPressureEvent channel=5 note=63 velocity=6>"


def test_control_change_event():
    event = ControlChangeEvent(channel=1, param=2, value=3, tag=4)
    assert isinstance(event, ControlChangeEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.CONTROLLER
    assert event.channel == 1
    assert event.param == 2
    assert event.value == 3
    assert event.tag == 4
    assert repr(event) == "<ControlChangeEvent channel=1 param=2 value=3>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_CONTROLLER
    assert alsa_event.data.control.channel == 1
    assert alsa_event.data.control.param == 2
    assert alsa_event.data.control.value == 3
    assert alsa_event.tag == 4

    event = ControlChangeEvent(5, 6, 7, tag=8)
    assert isinstance(event, ControlChangeEvent)
    assert isinstance(event, Event)

    assert event.type == EventType.CONTROLLER
    assert event.channel == 5
    assert event.param == 6
    assert event.value == 7
    assert event.tag == 8
    assert repr(event) == "<ControlChangeEvent channel=5 param=6 value=7>"

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_CONTROLLER
    alsa_event.tag = 9
    alsa_event.data.control.channel = 10
    alsa_event.data.control.param = 11
    alsa_event.data.control.value = 12

    event = ControlChangeEvent._from_alsa(alsa_event)
    assert isinstance(event, ControlChangeEvent)
    assert event.type == EventType.CONTROLLER
    assert event.tag == 9
    assert event.channel == 10
    assert event.param == 11
    assert event.value == 12
    assert repr(event) == "<ControlChangeEvent channel=10 param=11 value=12>"


def test_program_change_event():
    event = ProgramChangeEvent(channel=1, value=3, tag=4)
    assert isinstance(event, ProgramChangeEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.PGMCHANGE
    assert event.channel == 1
    assert event.value == 3
    assert event.tag == 4
    assert repr(event) == "<ProgramChangeEvent channel=1 value=3>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_PGMCHANGE
    assert alsa_event.data.control.channel == 1
    assert alsa_event.data.control.value == 3
    assert alsa_event.tag == 4

    event = ProgramChangeEvent(5, 6, tag=8)
    assert isinstance(event, ProgramChangeEvent)
    assert isinstance(event, Event)

    assert event.type == EventType.PGMCHANGE
    assert event.channel == 5
    assert event.value == 6
    assert event.tag == 8
    assert repr(event) == "<ProgramChangeEvent channel=5 value=6>"

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_PGMCHANGE
    alsa_event.tag = 9
    alsa_event.data.control.channel = 10
    alsa_event.data.control.value = 12

    event = ProgramChangeEvent._from_alsa(alsa_event)
    assert isinstance(event, ProgramChangeEvent)
    assert event.type == EventType.PGMCHANGE
    assert event.tag == 9
    assert event.channel == 10
    assert event.value == 12
    assert repr(event) == "<ProgramChangeEvent channel=10 value=12>"


def test_channel_pressure_event():
    event = ChannelPressureEvent(channel=1, value=3, tag=4)
    assert isinstance(event, ChannelPressureEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.CHANPRESS
    assert event.channel == 1
    assert event.value == 3
    assert event.tag == 4
    assert repr(event) == "<ChannelPressureEvent channel=1 value=3>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_CHANPRESS
    assert alsa_event.data.control.channel == 1
    assert alsa_event.data.control.value == 3
    assert alsa_event.tag == 4

    event = ChannelPressureEvent(5, 6, tag=8)
    assert isinstance(event, ChannelPressureEvent)
    assert isinstance(event, Event)

    assert event.type == EventType.CHANPRESS
    assert event.channel == 5
    assert event.value == 6
    assert event.tag == 8
    assert repr(event) == "<ChannelPressureEvent channel=5 value=6>"

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_CHANPRESS
    alsa_event.tag = 9
    alsa_event.data.control.channel = 10
    alsa_event.data.control.value = 12

    event = ChannelPressureEvent._from_alsa(alsa_event)
    assert isinstance(event, ChannelPressureEvent)
    assert event.type == EventType.CHANPRESS
    assert event.tag == 9
    assert event.channel == 10
    assert event.value == 12
    assert repr(event) == "<ChannelPressureEvent channel=10 value=12>"


def test_pitch_bend_event():
    event = PitchBendEvent(channel=1, value=3, tag=4)
    assert isinstance(event, PitchBendEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.PITCHBEND
    assert event.channel == 1
    assert event.value == 3
    assert event.tag == 4
    assert repr(event) == "<PitchBendEvent channel=1 value=3>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_PITCHBEND
    assert alsa_event.data.control.channel == 1
    assert alsa_event.data.control.value == 3
    assert alsa_event.tag == 4

    event = PitchBendEvent(5, 6, tag=8)
    assert isinstance(event, PitchBendEvent)
    assert isinstance(event, Event)

    assert event.type == EventType.PITCHBEND
    assert event.channel == 5
    assert event.value == 6
    assert event.tag == 8
    assert repr(event) == "<PitchBendEvent channel=5 value=6>"

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_PITCHBEND
    alsa_event.tag = 9
    alsa_event.data.control.channel = 10
    alsa_event.data.control.value = 12

    event = PitchBendEvent._from_alsa(alsa_event)
    assert isinstance(event, PitchBendEvent)
    assert event.type == EventType.PITCHBEND
    assert event.tag == 9
    assert event.channel == 10
    assert event.value == 12
    assert repr(event) == "<PitchBendEvent channel=10 value=12>"


def test_control_14bit_change_event():
    event = Control14BitChangeEvent(channel=1, param=2, value=3, tag=4)
    assert isinstance(event, Control14BitChangeEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.CONTROL14
    assert event.channel == 1
    assert event.param == 2
    assert event.value == 3
    assert event.tag == 4
    assert repr(event) == "<Control14BitChangeEvent channel=1 param=2 value=3>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_CONTROL14
    assert alsa_event.data.control.channel == 1
    assert alsa_event.data.control.param == 2
    assert alsa_event.data.control.value == 3
    assert alsa_event.tag == 4

    event = Control14BitChangeEvent(5, 6, 7, tag=8)
    assert isinstance(event, Control14BitChangeEvent)
    assert isinstance(event, Event)

    assert event.type == EventType.CONTROL14
    assert event.channel == 5
    assert event.param == 6
    assert event.value == 7
    assert event.tag == 8
    assert repr(event) == "<Control14BitChangeEvent channel=5 param=6 value=7>"

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_CONTROL14
    alsa_event.tag = 9
    alsa_event.data.control.channel = 10
    alsa_event.data.control.param = 11
    alsa_event.data.control.value = 12

    event = Control14BitChangeEvent._from_alsa(alsa_event)
    assert isinstance(event, Control14BitChangeEvent)
    assert event.type == EventType.CONTROL14
    assert event.tag == 9
    assert event.channel == 10
    assert event.param == 11
    assert event.value == 12
    assert repr(event) == "<Control14BitChangeEvent channel=10 param=11 value=12>"


def test_non_registered_parameter_change_event():
    event = NonRegisteredParameterChangeEvent(channel=1, param=2, value=3, tag=4)
    assert isinstance(event, NonRegisteredParameterChangeEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.NONREGPARAM
    assert event.channel == 1
    assert event.param == 2
    assert event.value == 3
    assert event.tag == 4
    assert repr(event) == "<NonRegisteredParameterChangeEvent channel=1 param=2 value=3>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_NONREGPARAM
    assert alsa_event.data.control.channel == 1
    assert alsa_event.data.control.param == 2
    assert alsa_event.data.control.value == 3
    assert alsa_event.tag == 4

    event = NonRegisteredParameterChangeEvent(5, 6, 7, tag=8)
    assert isinstance(event, NonRegisteredParameterChangeEvent)
    assert isinstance(event, Event)

    assert event.type == EventType.NONREGPARAM
    assert event.channel == 5
    assert event.param == 6
    assert event.value == 7
    assert event.tag == 8
    assert repr(event) == "<NonRegisteredParameterChangeEvent channel=5 param=6 value=7>"

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_NONREGPARAM
    alsa_event.tag = 9
    alsa_event.data.control.channel = 10
    alsa_event.data.control.param = 11
    alsa_event.data.control.value = 12

    event = NonRegisteredParameterChangeEvent._from_alsa(alsa_event)
    assert isinstance(event, NonRegisteredParameterChangeEvent)
    assert event.type == EventType.NONREGPARAM
    assert event.tag == 9
    assert event.channel == 10
    assert event.param == 11
    assert event.value == 12
    assert repr(event) == "<NonRegisteredParameterChangeEvent channel=10 param=11 value=12>"


def test_registered_parameter_change_event():
    event = RegisteredParameterChangeEvent(channel=1, param=2, value=3, tag=4)
    assert isinstance(event, RegisteredParameterChangeEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.REGPARAM
    assert event.channel == 1
    assert event.param == 2
    assert event.value == 3
    assert event.tag == 4
    assert repr(event) == "<RegisteredParameterChangeEvent channel=1 param=2 value=3>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_REGPARAM
    assert alsa_event.data.control.channel == 1
    assert alsa_event.data.control.param == 2
    assert alsa_event.data.control.value == 3
    assert alsa_event.tag == 4

    event = RegisteredParameterChangeEvent(5, 6, 7, tag=8)
    assert isinstance(event, RegisteredParameterChangeEvent)
    assert isinstance(event, Event)

    assert event.type == EventType.REGPARAM
    assert event.channel == 5
    assert event.param == 6
    assert event.value == 7
    assert event.tag == 8
    assert repr(event) == "<RegisteredParameterChangeEvent channel=5 param=6 value=7>"

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_REGPARAM
    alsa_event.tag = 9
    alsa_event.data.control.channel = 10
    alsa_event.data.control.param = 11
    alsa_event.data.control.value = 12

    event = RegisteredParameterChangeEvent._from_alsa(alsa_event)
    assert isinstance(event, RegisteredParameterChangeEvent)
    assert event.type == EventType.REGPARAM
    assert event.tag == 9
    assert event.channel == 10
    assert event.param == 11
    assert event.value == 12
    assert repr(event) == "<RegisteredParameterChangeEvent channel=10 param=11 value=12>"


def test_song_position_pointer_event():
    event = SongPositionPointerEvent(channel=1, value=3, tag=4)
    assert isinstance(event, SongPositionPointerEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.SONGPOS
    assert event.channel == 1
    assert event.value == 3
    assert event.tag == 4
    assert repr(event) == "<SongPositionPointerEvent channel=1 value=3>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_SONGPOS
    assert alsa_event.data.control.channel == 1
    assert alsa_event.data.control.value == 3
    assert alsa_event.tag == 4

    event = SongPositionPointerEvent(5, 6, tag=8)
    assert isinstance(event, SongPositionPointerEvent)
    assert isinstance(event, Event)

    assert event.type == EventType.SONGPOS
    assert event.channel == 5
    assert event.value == 6
    assert event.tag == 8
    assert repr(event) == "<SongPositionPointerEvent channel=5 value=6>"

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_SONGPOS
    alsa_event.tag = 9
    alsa_event.data.control.channel = 10
    alsa_event.data.control.value = 12

    event = SongPositionPointerEvent._from_alsa(alsa_event)
    assert isinstance(event, SongPositionPointerEvent)
    assert event.type == EventType.SONGPOS
    assert event.tag == 9
    assert event.channel == 10
    assert event.value == 12
    assert repr(event) == "<SongPositionPointerEvent channel=10 value=12>"


def test_song_select_event():
    event = SongSelectEvent(channel=1, value=3, tag=4)
    assert isinstance(event, SongSelectEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.SONGSEL
    assert event.channel == 1
    assert event.value == 3
    assert event.tag == 4
    assert repr(event) == "<SongSelectEvent channel=1 value=3>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_SONGSEL
    assert alsa_event.data.control.channel == 1
    assert alsa_event.data.control.value == 3
    assert alsa_event.tag == 4

    event = SongSelectEvent(5, 6, tag=8)
    assert isinstance(event, SongSelectEvent)
    assert isinstance(event, Event)

    assert event.type == EventType.SONGSEL
    assert event.channel == 5
    assert event.value == 6
    assert event.tag == 8
    assert repr(event) == "<SongSelectEvent channel=5 value=6>"

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_SONGSEL
    alsa_event.tag = 9
    alsa_event.data.control.channel = 10
    alsa_event.data.control.value = 12

    event = SongSelectEvent._from_alsa(alsa_event)
    assert isinstance(event, SongSelectEvent)
    assert event.type == EventType.SONGSEL
    assert event.tag == 9
    assert event.channel == 10
    assert event.value == 12
    assert repr(event) == "<SongSelectEvent channel=10 value=12>"


def test_time_signature_event():
    event = TimeSignatureEvent(channel=1, value=3, tag=4)
    assert isinstance(event, TimeSignatureEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.TIMESIGN
    assert event.channel == 1
    assert event.value == 3
    assert event.tag == 4
    assert repr(event) == "<TimeSignatureEvent channel=1 value=3>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_TIMESIGN
    assert alsa_event.data.control.channel == 1
    assert alsa_event.data.control.value == 3
    assert alsa_event.tag == 4

    event = TimeSignatureEvent(5, 6, tag=8)
    assert isinstance(event, TimeSignatureEvent)
    assert isinstance(event, Event)

    assert event.type == EventType.TIMESIGN
    assert event.channel == 5
    assert event.value == 6
    assert event.tag == 8
    assert repr(event) == "<TimeSignatureEvent channel=5 value=6>"

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_TIMESIGN
    alsa_event.tag = 9
    alsa_event.data.control.channel = 10
    alsa_event.data.control.value = 12

    event = TimeSignatureEvent._from_alsa(alsa_event)
    assert isinstance(event, TimeSignatureEvent)
    assert event.type == EventType.TIMESIGN
    assert event.tag == 9
    assert event.channel == 10
    assert event.value == 12
    assert repr(event) == "<TimeSignatureEvent channel=10 value=12>"


def test_key_signature_event():
    event = KeySignatureEvent(channel=1, value=3, tag=4)
    assert isinstance(event, KeySignatureEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.KEYSIGN
    assert event.channel == 1
    assert event.value == 3
    assert event.tag == 4
    assert repr(event) == "<KeySignatureEvent channel=1 value=3>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_KEYSIGN
    assert alsa_event.data.control.channel == 1
    assert alsa_event.data.control.value == 3
    assert alsa_event.tag == 4

    event = KeySignatureEvent(5, 6, tag=8)
    assert isinstance(event, KeySignatureEvent)
    assert isinstance(event, Event)

    assert event.type == EventType.KEYSIGN
    assert event.channel == 5
    assert event.value == 6
    assert event.tag == 8
    assert repr(event) == "<KeySignatureEvent channel=5 value=6>"

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_KEYSIGN
    alsa_event.tag = 9
    alsa_event.data.control.channel = 10
    alsa_event.data.control.value = 12

    event = KeySignatureEvent._from_alsa(alsa_event)
    assert isinstance(event, KeySignatureEvent)
    assert event.type == EventType.KEYSIGN
    assert event.tag == 9
    assert event.channel == 10
    assert event.value == 12
    assert repr(event) == "<KeySignatureEvent channel=10 value=12>"


def test_start_event():
    event = StartEvent()
    assert isinstance(event, StartEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.START
    assert event.control_queue is None
    assert repr(event) == "<StartEvent>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_START
    assert alsa_event.data.queue.queue == 0
    assert alsa_event.tag == 0

    event = StartEvent(control_queue=2, tag=3)
    assert isinstance(event, StartEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.START
    assert event.control_queue == 2
    assert event.tag == 3
    assert repr(event) == "<StartEvent queue=2>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_START
    assert alsa_event.data.queue.queue == 2
    assert alsa_event.tag == 3

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_START
    alsa_event.tag = 9
    alsa_event.data.queue.queue = 10

    event = StartEvent._from_alsa(alsa_event)
    assert isinstance(event, StartEvent)
    assert event.type == EventType.START
    assert event.tag == 9
    assert event.control_queue == 10
    assert repr(event) == "<StartEvent queue=10>"


def test_continue_event():
    event = ContinueEvent()
    assert isinstance(event, ContinueEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.CONTINUE
    assert event.control_queue is None
    assert repr(event) == "<ContinueEvent>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_CONTINUE
    assert alsa_event.data.queue.queue == 0
    assert alsa_event.tag == 0

    event = ContinueEvent(control_queue=2, tag=3)
    assert isinstance(event, ContinueEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.CONTINUE
    assert event.control_queue == 2
    assert event.tag == 3
    assert repr(event) == "<ContinueEvent queue=2>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_CONTINUE
    assert alsa_event.data.queue.queue == 2
    assert alsa_event.tag == 3

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_CONTINUE
    alsa_event.tag = 9
    alsa_event.data.queue.queue = 10

    event = ContinueEvent._from_alsa(alsa_event)
    assert isinstance(event, ContinueEvent)
    assert event.type == EventType.CONTINUE
    assert event.tag == 9
    assert event.control_queue == 10
    assert repr(event) == "<ContinueEvent queue=10>"


def test_stop_event():
    event = StopEvent()
    assert isinstance(event, StopEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.STOP
    assert event.control_queue is None
    assert repr(event) == "<StopEvent>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_STOP
    assert alsa_event.data.queue.queue == 0
    assert alsa_event.tag == 0

    event = StopEvent(control_queue=2, tag=3)
    assert isinstance(event, StopEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.STOP
    assert event.control_queue == 2
    assert event.tag == 3
    assert repr(event) == "<StopEvent queue=2>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_STOP
    assert alsa_event.data.queue.queue == 2
    assert alsa_event.tag == 3

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_STOP
    alsa_event.tag = 9
    alsa_event.data.queue.queue = 10

    event = StopEvent._from_alsa(alsa_event)
    assert isinstance(event, StopEvent)
    assert event.type == EventType.STOP
    assert event.tag == 9
    assert event.control_queue == 10
    assert repr(event) == "<StopEvent queue=10>"


def test_set_queue_position_tick_event():
    event = SetQueuePositionTickEvent(position=10)
    assert isinstance(event, SetQueuePositionTickEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.SETPOS_TICK
    assert event.control_queue is None
    assert event.position == 10
    assert repr(event) == "<SetQueuePositionTickEvent position=10>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_SETPOS_TICK
    assert alsa_event.data.queue.queue == 0
    assert alsa_event.data.queue.param.time.tick == 10
    assert alsa_event.tag == 0

    event = SetQueuePositionTickEvent(control_queue=2, position=3, tag=4)
    assert isinstance(event, SetQueuePositionTickEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.SETPOS_TICK
    assert event.control_queue == 2
    assert event.position == 3
    assert event.tag == 4
    assert repr(event) == "<SetQueuePositionTickEvent queue=2 position=3>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_SETPOS_TICK
    assert alsa_event.data.queue.queue == 2
    assert alsa_event.data.queue.param.time.tick == 3
    assert alsa_event.tag == 4

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_SETPOS_TICK
    alsa_event.tag = 9
    alsa_event.data.queue.queue = 10
    alsa_event.data.queue.param.time.tick = 11

    event = SetQueuePositionTickEvent._from_alsa(alsa_event)
    assert isinstance(event, SetQueuePositionTickEvent)
    assert event.type == EventType.SETPOS_TICK
    assert event.tag == 9
    assert event.control_queue == 10
    assert event.position == 11
    assert repr(event) == "<SetQueuePositionTickEvent queue=10 position=11>"


def test_set_queue_position_time_event():
    event = SetQueuePositionTimeEvent(position=10.0)
    assert isinstance(event, SetQueuePositionTimeEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.SETPOS_TIME
    assert event.control_queue is None
    assert event.position == RealTime(10, 0)
    assert repr(event) == "<SetQueuePositionTimeEvent position=10.000000000>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_SETPOS_TIME
    assert alsa_event.data.queue.queue == 0
    assert alsa_event.data.queue.param.time.time.tv_sec == 10
    assert alsa_event.data.queue.param.time.time.tv_nsec == 0
    assert alsa_event.tag == 0

    event = SetQueuePositionTimeEvent(control_queue=2, position=RealTime(3, 3), tag=4)
    assert isinstance(event, SetQueuePositionTimeEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.SETPOS_TIME
    assert event.control_queue == 2
    assert event.position == RealTime(3, 3)
    assert event.tag == 4
    assert repr(event) == "<SetQueuePositionTimeEvent queue=2 position=3.000000003>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_SETPOS_TIME
    assert alsa_event.data.queue.queue == 2
    assert alsa_event.data.queue.param.time.time.tv_sec == 3
    assert alsa_event.data.queue.param.time.time.tv_nsec == 3
    assert alsa_event.tag == 4

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_SETPOS_TIME
    alsa_event.tag = 9
    alsa_event.data.queue.queue = 10
    alsa_event.data.queue.param.time.time.tv_sec = 11
    alsa_event.data.queue.param.time.time.tv_nsec = 12

    event = SetQueuePositionTimeEvent._from_alsa(alsa_event)
    assert isinstance(event, SetQueuePositionTimeEvent)
    assert event.type == EventType.SETPOS_TIME
    assert event.tag == 9
    assert event.control_queue == 10
    assert event.position == RealTime(11, 12)
    assert repr(event) == "<SetQueuePositionTimeEvent queue=10 position=11.000000012>"


def test_set_queue_tempo_event():
    with pytest.raises(ValueError):
        SetQueueTempoEvent()

    event = SetQueueTempoEvent(midi_tempo=500000)
    assert isinstance(event, SetQueueTempoEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.TEMPO
    assert event.control_queue is None
    assert event.midi_tempo == 500000
    assert event.bpm == pytest.approx(120.0)
    assert repr(event) == "<SetQueueTempoEvent tempo=500000 (120.0 bpm)>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_TEMPO
    assert alsa_event.data.queue.queue == 0
    assert alsa_event.data.queue.param.value == 500000
    assert alsa_event.tag == 0

    event = SetQueueTempoEvent(control_queue=2, bpm=90, tag=4)
    assert isinstance(event, SetQueueTempoEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.TEMPO
    assert event.control_queue == 2
    assert event.midi_tempo == 666667
    assert event.bpm == pytest.approx(90.0)
    assert event.tag == 4
    assert repr(event) == "<SetQueueTempoEvent queue=2 tempo=666667 (90.0 bpm)>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_TEMPO
    assert alsa_event.data.queue.queue == 2
    assert alsa_event.data.queue.param.value == 666667
    assert alsa_event.tag == 4

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_TEMPO
    alsa_event.tag = 9
    alsa_event.data.queue.queue = 10
    alsa_event.data.queue.param.value = 1000000

    event = SetQueueTempoEvent._from_alsa(alsa_event)
    assert isinstance(event, SetQueueTempoEvent)
    assert event.type == EventType.TEMPO
    assert event.tag == 9
    assert event.control_queue == 10
    assert event.midi_tempo == 1000000
    assert event.bpm == pytest.approx(60.0)
    assert repr(event) == "<SetQueueTempoEvent queue=10 tempo=1000000 (60.0 bpm)>"


def test_clock_event():
    event = ClockEvent()
    assert isinstance(event, ClockEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.CLOCK
    assert event.control_queue is None
    assert repr(event) == "<ClockEvent>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_CLOCK
    assert alsa_event.data.queue.queue == 0
    assert alsa_event.tag == 0

    event = ClockEvent(control_queue=2, tag=3)
    assert isinstance(event, ClockEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.CLOCK
    assert event.control_queue == 2
    assert event.tag == 3
    assert repr(event) == "<ClockEvent queue=2>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_CLOCK
    assert alsa_event.data.queue.queue == 2
    assert alsa_event.tag == 3

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_CLOCK
    alsa_event.tag = 9
    alsa_event.data.queue.queue = 10

    event = ClockEvent._from_alsa(alsa_event)
    assert isinstance(event, ClockEvent)
    assert event.type == EventType.CLOCK
    assert event.tag == 9
    assert event.control_queue == 10
    assert repr(event) == "<ClockEvent queue=10>"


def test_tick_event():
    event = TickEvent()
    assert isinstance(event, TickEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.TICK
    assert event.control_queue is None
    assert repr(event) == "<TickEvent>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_TICK
    assert alsa_event.data.queue.queue == 0
    assert alsa_event.tag == 0

    event = TickEvent(control_queue=2, tag=3)
    assert isinstance(event, TickEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.TICK
    assert event.control_queue == 2
    assert event.tag == 3
    assert repr(event) == "<TickEvent queue=2>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_TICK
    assert alsa_event.data.queue.queue == 2
    assert alsa_event.tag == 3

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_TICK
    alsa_event.tag = 9
    alsa_event.data.queue.queue = 10

    event = TickEvent._from_alsa(alsa_event)
    assert isinstance(event, TickEvent)
    assert event.type == EventType.TICK
    assert event.tag == 9
    assert event.control_queue == 10
    assert repr(event) == "<TickEvent queue=10>"


def test_set_queue_skew_event():
    event = QueueSkewEvent(value=1, base=2)
    assert isinstance(event, QueueSkewEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.QUEUE_SKEW
    assert event.control_queue is None
    assert event.value == 1
    assert event.base == 2
    assert repr(event) == "<QueueSkewEvent value=1 base=2>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_QUEUE_SKEW
    assert alsa_event.data.queue.queue == 0
    assert alsa_event.data.queue.param.skew.value == 1
    assert alsa_event.data.queue.param.skew.base == 2
    assert alsa_event.tag == 0

    event = QueueSkewEvent(2, 3, control_queue=4, tag=5)
    assert isinstance(event, QueueSkewEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.QUEUE_SKEW
    assert event.control_queue == 4
    assert event.value == 2
    assert event.base == 3
    assert event.tag == 5
    assert repr(event) == "<QueueSkewEvent queue=4 value=2 base=3>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_QUEUE_SKEW
    assert alsa_event.data.queue.queue == 4
    assert alsa_event.data.queue.param.skew.value == 2
    assert alsa_event.data.queue.param.skew.base == 3
    assert alsa_event.tag == 5

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_QUEUE_SKEW
    alsa_event.tag = 9
    alsa_event.data.queue.queue = 10
    alsa_event.data.queue.param.skew.value = 11
    alsa_event.data.queue.param.skew.base = 12

    event = QueueSkewEvent._from_alsa(alsa_event)
    assert isinstance(event, QueueSkewEvent)
    assert event.type == EventType.QUEUE_SKEW
    assert event.tag == 9
    assert event.control_queue == 10
    assert event.value == 11
    assert event.base == 12
    assert repr(event) == "<QueueSkewEvent queue=10 value=11 base=12>"


def test_sync_position_changed_event():
    event = SyncPositionChangedEvent(position=10)
    assert isinstance(event, SyncPositionChangedEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.SYNC_POS
    assert event.control_queue is None
    assert event.position == 10
    assert repr(event) == "<SyncPositionChangedEvent position=10>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_SYNC_POS
    assert alsa_event.data.queue.queue == 0
    assert alsa_event.data.queue.param.position == 10
    assert alsa_event.tag == 0

    event = SyncPositionChangedEvent(control_queue=2, position=3, tag=4)
    assert isinstance(event, SyncPositionChangedEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.SYNC_POS
    assert event.control_queue == 2
    assert event.position == 3
    assert event.tag == 4
    assert repr(event) == "<SyncPositionChangedEvent queue=2 position=3>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_SYNC_POS
    assert alsa_event.data.queue.queue == 2
    assert alsa_event.data.queue.param.position == 3
    assert alsa_event.tag == 4

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_SYNC_POS
    alsa_event.tag = 9
    alsa_event.data.queue.queue = 10
    alsa_event.data.queue.param.position = 11

    event = SyncPositionChangedEvent._from_alsa(alsa_event)
    assert isinstance(event, SyncPositionChangedEvent)
    assert event.type == EventType.SYNC_POS
    assert event.tag == 9
    assert event.control_queue == 10
    assert event.position == 11
    assert repr(event) == "<SyncPositionChangedEvent queue=10 position=11>"


def test_tune_request_event():
    event = TuneRequestEvent()
    assert isinstance(event, TuneRequestEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.TUNE_REQUEST
    assert repr(event) == "<TuneRequestEvent>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_TUNE_REQUEST
    assert alsa_event.tag == 0

    event = TuneRequestEvent(tag=3)
    assert isinstance(event, TuneRequestEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.TUNE_REQUEST
    assert event.tag == 3
    assert repr(event) == "<TuneRequestEvent>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_TUNE_REQUEST
    assert alsa_event.tag == 3

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_TUNE_REQUEST
    alsa_event.tag = 9

    event = TuneRequestEvent._from_alsa(alsa_event)
    assert isinstance(event, TuneRequestEvent)
    assert event.type == EventType.TUNE_REQUEST
    assert event.tag == 9
    assert repr(event) == "<TuneRequestEvent>"


def test_reset_event():
    event = ResetEvent()
    assert isinstance(event, ResetEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.RESET
    assert repr(event) == "<ResetEvent>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_RESET
    assert alsa_event.tag == 0

    event = ResetEvent(tag=3)
    assert isinstance(event, ResetEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.RESET
    assert event.tag == 3
    assert repr(event) == "<ResetEvent>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_RESET
    assert alsa_event.tag == 3

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_RESET
    alsa_event.tag = 9

    event = ResetEvent._from_alsa(alsa_event)
    assert isinstance(event, ResetEvent)
    assert event.type == EventType.RESET
    assert event.tag == 9
    assert repr(event) == "<ResetEvent>"


def test_active_sensing_event():
    event = ActiveSensingEvent()
    assert isinstance(event, ActiveSensingEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.SENSING
    assert repr(event) == "<ActiveSensingEvent>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_SENSING
    assert alsa_event.tag == 0

    event = ActiveSensingEvent(tag=3)
    assert isinstance(event, ActiveSensingEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.SENSING
    assert event.tag == 3
    assert repr(event) == "<ActiveSensingEvent>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_SENSING
    assert alsa_event.tag == 3

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_SENSING
    alsa_event.tag = 9

    event = ActiveSensingEvent._from_alsa(alsa_event)
    assert isinstance(event, ActiveSensingEvent)
    assert event.type == EventType.SENSING
    assert event.tag == 9
    assert repr(event) == "<ActiveSensingEvent>"


def test_echo_event():
    event = EchoEvent()
    assert isinstance(event, EchoEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.ECHO
    assert repr(event) == "<EchoEvent data=None>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_ECHO
    assert alsa_event.tag == 0
    empty = b"\x00" * ffi.sizeof("snd_seq_ev_raw8_t")
    assert bytes(ffi.buffer(alsa_event.data.raw8.d)) == empty

    event = EchoEvent(tag=3, raw_data=b"abcd")
    assert isinstance(event, EchoEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.ECHO
    assert event.tag == 3
    assert repr(event).startswith("<EchoEvent data=b'abcd")

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_ECHO
    assert alsa_event.tag == 3
    assert ffi.buffer(alsa_event.data.raw8.d)[:4] == b"abcd"

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_ECHO
    alsa_event.tag = 9
    ffi.buffer(alsa_event.data.raw8.d)[:5] = b"12345"

    event = EchoEvent._from_alsa(alsa_event)
    assert isinstance(event, EchoEvent)
    assert event.type == EventType.ECHO
    assert event.tag == 9
    assert repr(event).startswith("<EchoEvent data=b'12345")


def test_oss_event():
    event = OSSEvent()
    assert isinstance(event, OSSEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.OSS
    assert repr(event) == "<OSSEvent data=None>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_OSS
    assert alsa_event.tag == 0
    empty = b"\x00" * ffi.sizeof("snd_seq_ev_raw8_t")
    assert bytes(ffi.buffer(alsa_event.data.raw8.d)) == empty

    event = OSSEvent(tag=3, raw_data=b"abcd")
    assert isinstance(event, OSSEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.OSS
    assert event.tag == 3
    assert repr(event).startswith("<OSSEvent data=b'abcd")

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_OSS
    assert alsa_event.tag == 3
    assert ffi.buffer(alsa_event.data.raw8.d)[:4] == b"abcd"

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_OSS
    alsa_event.tag = 9
    ffi.buffer(alsa_event.data.raw8.d)[:5] = b"12345"

    event = OSSEvent._from_alsa(alsa_event)
    assert isinstance(event, OSSEvent)
    assert event.type == EventType.OSS
    assert event.tag == 9
    assert repr(event).startswith("<OSSEvent data=b'12345")


def test_client_start_event():
    event = ClientStartEvent(addr=Address(1, 2))
    assert isinstance(event, ClientStartEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.CLIENT_START
    assert event.addr == Address(1, 2)
    assert repr(event) == "<ClientStartEvent 1:2>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_CLIENT_START
    assert alsa_event.data.addr.client == 1
    assert alsa_event.data.addr.port == 2
    assert alsa_event.tag == 0

    event = ClientStartEvent((3, 4), tag=5)
    assert isinstance(event, ClientStartEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.CLIENT_START
    assert event.addr == Address(3, 4)
    assert event.tag == 5
    assert repr(event) == "<ClientStartEvent 3:4>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_CLIENT_START
    assert alsa_event.data.addr.client == 3
    assert alsa_event.data.addr.port == 4
    assert alsa_event.tag == 5

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_CLIENT_START
    alsa_event.tag = 9
    alsa_event.data.addr.client = 10
    alsa_event.data.addr.port = 11

    event = ClientStartEvent._from_alsa(alsa_event)
    assert isinstance(event, ClientStartEvent)
    assert event.type == EventType.CLIENT_START
    assert event.tag == 9
    assert event.addr == Address(10, 11)
    assert repr(event) == "<ClientStartEvent 10:11>"


def test_client_exit_event():
    event = ClientExitEvent(addr=Address(1, 2))
    assert isinstance(event, ClientExitEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.CLIENT_EXIT
    assert event.addr == Address(1, 2)
    assert repr(event) == "<ClientExitEvent 1:2>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_CLIENT_EXIT
    assert alsa_event.data.addr.client == 1
    assert alsa_event.data.addr.port == 2
    assert alsa_event.tag == 0

    event = ClientExitEvent((3, 4), tag=5)
    assert isinstance(event, ClientExitEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.CLIENT_EXIT
    assert event.addr == Address(3, 4)
    assert event.tag == 5
    assert repr(event) == "<ClientExitEvent 3:4>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_CLIENT_EXIT
    assert alsa_event.data.addr.client == 3
    assert alsa_event.data.addr.port == 4
    assert alsa_event.tag == 5

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_CLIENT_EXIT
    alsa_event.tag = 9
    alsa_event.data.addr.client = 10
    alsa_event.data.addr.port = 11

    event = ClientExitEvent._from_alsa(alsa_event)
    assert isinstance(event, ClientExitEvent)
    assert event.type == EventType.CLIENT_EXIT
    assert event.tag == 9
    assert event.addr == Address(10, 11)
    assert repr(event) == "<ClientExitEvent 10:11>"


def test_client_change_event():
    event = ClientChangeEvent(addr=Address(1, 2))
    assert isinstance(event, ClientChangeEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.CLIENT_CHANGE
    assert event.addr == Address(1, 2)
    assert repr(event) == "<ClientChangeEvent 1:2>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_CLIENT_CHANGE
    assert alsa_event.data.addr.client == 1
    assert alsa_event.data.addr.port == 2
    assert alsa_event.tag == 0

    event = ClientChangeEvent((3, 4), tag=5)
    assert isinstance(event, ClientChangeEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.CLIENT_CHANGE
    assert event.addr == Address(3, 4)
    assert event.tag == 5
    assert repr(event) == "<ClientChangeEvent 3:4>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_CLIENT_CHANGE
    assert alsa_event.data.addr.client == 3
    assert alsa_event.data.addr.port == 4
    assert alsa_event.tag == 5

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_CLIENT_CHANGE
    alsa_event.tag = 9
    alsa_event.data.addr.client = 10
    alsa_event.data.addr.port = 11

    event = ClientChangeEvent._from_alsa(alsa_event)
    assert isinstance(event, ClientChangeEvent)
    assert event.type == EventType.CLIENT_CHANGE
    assert event.tag == 9
    assert event.addr == Address(10, 11)
    assert repr(event) == "<ClientChangeEvent 10:11>"


def test_port_start_event():
    event = PortStartEvent(addr=Address(1, 2))
    assert isinstance(event, PortStartEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.PORT_START
    assert event.addr == Address(1, 2)
    assert repr(event) == "<PortStartEvent 1:2>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_PORT_START
    assert alsa_event.data.addr.client == 1
    assert alsa_event.data.addr.port == 2
    assert alsa_event.tag == 0

    event = PortStartEvent((3, 4), tag=5)
    assert isinstance(event, PortStartEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.PORT_START
    assert event.addr == Address(3, 4)
    assert event.tag == 5
    assert repr(event) == "<PortStartEvent 3:4>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_PORT_START
    assert alsa_event.data.addr.client == 3
    assert alsa_event.data.addr.port == 4
    assert alsa_event.tag == 5

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_PORT_START
    alsa_event.tag = 9
    alsa_event.data.addr.client = 10
    alsa_event.data.addr.port = 11

    event = PortStartEvent._from_alsa(alsa_event)
    assert isinstance(event, PortStartEvent)
    assert event.type == EventType.PORT_START
    assert event.tag == 9
    assert event.addr == Address(10, 11)
    assert repr(event) == "<PortStartEvent 10:11>"


def test_port_exit_event():
    event = PortExitEvent(addr=Address(1, 2))
    assert isinstance(event, PortExitEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.PORT_EXIT
    assert event.addr == Address(1, 2)
    assert repr(event) == "<PortExitEvent 1:2>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_PORT_EXIT
    assert alsa_event.data.addr.client == 1
    assert alsa_event.data.addr.port == 2
    assert alsa_event.tag == 0

    event = PortExitEvent((3, 4), tag=5)
    assert isinstance(event, PortExitEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.PORT_EXIT
    assert event.addr == Address(3, 4)
    assert event.tag == 5
    assert repr(event) == "<PortExitEvent 3:4>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_PORT_EXIT
    assert alsa_event.data.addr.client == 3
    assert alsa_event.data.addr.port == 4
    assert alsa_event.tag == 5

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_PORT_EXIT
    alsa_event.tag = 9
    alsa_event.data.addr.client = 10
    alsa_event.data.addr.port = 11

    event = PortExitEvent._from_alsa(alsa_event)
    assert isinstance(event, PortExitEvent)
    assert event.type == EventType.PORT_EXIT
    assert event.tag == 9
    assert event.addr == Address(10, 11)
    assert repr(event) == "<PortExitEvent 10:11>"


def test_port_change_event():
    event = PortChangeEvent(addr=Address(1, 2))
    assert isinstance(event, PortChangeEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.PORT_CHANGE
    assert event.addr == Address(1, 2)
    assert repr(event) == "<PortChangeEvent 1:2>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_PORT_CHANGE
    assert alsa_event.data.addr.client == 1
    assert alsa_event.data.addr.port == 2
    assert alsa_event.tag == 0

    event = PortChangeEvent((3, 4), tag=5)
    assert isinstance(event, PortChangeEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.PORT_CHANGE
    assert event.addr == Address(3, 4)
    assert event.tag == 5
    assert repr(event) == "<PortChangeEvent 3:4>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_PORT_CHANGE
    assert alsa_event.data.addr.client == 3
    assert alsa_event.data.addr.port == 4
    assert alsa_event.tag == 5

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_PORT_CHANGE
    alsa_event.tag = 9
    alsa_event.data.addr.client = 10
    alsa_event.data.addr.port = 11

    event = PortChangeEvent._from_alsa(alsa_event)
    assert isinstance(event, PortChangeEvent)
    assert event.type == EventType.PORT_CHANGE
    assert event.tag == 9
    assert event.addr == Address(10, 11)
    assert repr(event) == "<PortChangeEvent 10:11>"


def test_port_subscribed_event():
    event = PortSubscribedEvent(connect_sender=Address(1, 2), connect_dest=Address(3, 4))
    assert isinstance(event, PortSubscribedEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.PORT_SUBSCRIBED
    assert event.connect_sender == Address(1, 2)
    assert event.connect_dest == Address(3, 4)
    assert repr(event) == "<PortSubscribedEvent from 1:2 to 3:4>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_PORT_SUBSCRIBED
    assert alsa_event.data.connect.sender.client == 1
    assert alsa_event.data.connect.sender.port == 2
    assert alsa_event.data.connect.dest.client == 3
    assert alsa_event.data.connect.dest.port == 4
    assert alsa_event.tag == 0

    event = PortSubscribedEvent((3, 4), (5, 6), tag=7)
    assert isinstance(event, PortSubscribedEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.PORT_SUBSCRIBED
    assert event.connect_sender == Address(3, 4)
    assert event.connect_dest == Address(5, 6)
    assert event.tag == 7
    assert repr(event) == "<PortSubscribedEvent from 3:4 to 5:6>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_PORT_SUBSCRIBED
    assert alsa_event.data.connect.sender.client == 3
    assert alsa_event.data.connect.sender.port == 4
    assert alsa_event.data.connect.dest.client == 5
    assert alsa_event.data.connect.dest.port == 6
    assert alsa_event.tag == 7

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_PORT_SUBSCRIBED
    alsa_event.tag = 9
    alsa_event.data.connect.sender.client = 10
    alsa_event.data.connect.sender.port = 11
    alsa_event.data.connect.dest.client = 12
    alsa_event.data.connect.dest.port = 13

    event = PortSubscribedEvent._from_alsa(alsa_event)
    assert isinstance(event, PortSubscribedEvent)
    assert event.type == EventType.PORT_SUBSCRIBED
    assert event.tag == 9
    assert event.connect_sender == Address(10, 11)
    assert event.connect_dest == Address(12, 13)
    assert repr(event) == "<PortSubscribedEvent from 10:11 to 12:13>"


def test_port_unsubscribed_event():
    event = PortUnsubscribedEvent(connect_sender=Address(1, 2), connect_dest=Address(3, 4))
    assert isinstance(event, PortUnsubscribedEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.PORT_UNSUBSCRIBED
    assert event.connect_sender == Address(1, 2)
    assert event.connect_dest == Address(3, 4)
    assert repr(event) == "<PortUnsubscribedEvent from 1:2 to 3:4>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_PORT_UNSUBSCRIBED
    assert alsa_event.data.connect.sender.client == 1
    assert alsa_event.data.connect.sender.port == 2
    assert alsa_event.data.connect.dest.client == 3
    assert alsa_event.data.connect.dest.port == 4
    assert alsa_event.tag == 0

    event = PortUnsubscribedEvent((3, 4), (5, 6), tag=7)
    assert isinstance(event, PortUnsubscribedEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.PORT_UNSUBSCRIBED
    assert event.connect_sender == Address(3, 4)
    assert event.connect_dest == Address(5, 6)
    assert event.tag == 7
    assert repr(event) == "<PortUnsubscribedEvent from 3:4 to 5:6>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_PORT_UNSUBSCRIBED
    assert alsa_event.data.connect.sender.client == 3
    assert alsa_event.data.connect.sender.port == 4
    assert alsa_event.data.connect.dest.client == 5
    assert alsa_event.data.connect.dest.port == 6
    assert alsa_event.tag == 7

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_PORT_UNSUBSCRIBED
    alsa_event.tag = 9
    alsa_event.data.connect.sender.client = 10
    alsa_event.data.connect.sender.port = 11
    alsa_event.data.connect.dest.client = 12
    alsa_event.data.connect.dest.port = 13

    event = PortUnsubscribedEvent._from_alsa(alsa_event)
    assert isinstance(event, PortUnsubscribedEvent)
    assert event.type == EventType.PORT_UNSUBSCRIBED
    assert event.tag == 9
    assert event.connect_sender == Address(10, 11)
    assert event.connect_dest == Address(12, 13)
    assert repr(event) == "<PortUnsubscribedEvent from 10:11 to 12:13>"


def test_sysex_event():
    event = SysExEvent(data=b"\xf012345\xf7")
    assert isinstance(event, SysExEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.SYSEX
    event.data == b"\xf012345\xf7"
    assert repr(event) == "<SysExEvent data=b'\\xf012345\\xf7'>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_SYSEX
    assert alsa_event.tag == 0
    assert alsa_event.data.ext.len == 7
    assert EventFlags.EVENT_LENGTH_VARIABLE in EventFlags(alsa_event.flags)
    assert ffi.buffer(alsa_event.data.ext.ptr, 7)[:] == b"\xf012345\xf7"

    event = SysExEvent(b"abcd", tag=3)
    assert isinstance(event, SysExEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.SYSEX
    assert event.tag == 3
    assert repr(event) == "<SysExEvent data=b'abcd'>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_SYSEX
    assert alsa_event.tag == 3
    assert alsa_event.data.ext.len == 4
    assert ffi.buffer(alsa_event.data.ext.ptr, 4)[:] == b"abcd"

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_SYSEX
    alsa_event.flags = EventFlags.EVENT_LENGTH_VARIABLE
    alsa_event.tag = 9
    alsa_event.data.ext.len = 10
    data_bytes = b"0123456789"
    alsa_event.data.ext.ptr = ffi.from_buffer(data_bytes)

    event = SysExEvent._from_alsa(alsa_event)
    assert isinstance(event, SysExEvent)
    assert event.type == EventType.SYSEX
    assert event.tag == 9
    assert event.data == b"0123456789"
    assert repr(event) == "<SysExEvent data=b'0123456789'>"


def test_bounce_event():
    event = BounceEvent(data=b"\xf012345\xf7")
    assert isinstance(event, BounceEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.BOUNCE
    event.data == b"\xf012345\xf7"
    assert repr(event) == "<BounceEvent data=b'\\xf012345\\xf7'>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_BOUNCE
    assert alsa_event.tag == 0
    assert alsa_event.data.ext.len == 7
    assert EventFlags.EVENT_LENGTH_VARIABLE in EventFlags(alsa_event.flags)
    assert ffi.buffer(alsa_event.data.ext.ptr, 7)[:] == b"\xf012345\xf7"

    event = BounceEvent(b"abcd", tag=3)
    assert isinstance(event, BounceEvent)
    assert isinstance(event, Event)
    assert event.type == EventType.BOUNCE
    assert event.tag == 3
    assert repr(event) == "<BounceEvent data=b'abcd'>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == alsa.SND_SEQ_EVENT_BOUNCE
    assert alsa_event.tag == 3
    assert alsa_event.data.ext.len == 4
    assert ffi.buffer(alsa_event.data.ext.ptr, 4)[:] == b"abcd"

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = alsa.SND_SEQ_EVENT_BOUNCE
    alsa_event.flags = EventFlags.EVENT_LENGTH_VARIABLE
    alsa_event.tag = 9
    alsa_event.data.ext.len = 10
    data_bytes = b"0123456789"
    alsa_event.data.ext.ptr = ffi.from_buffer(data_bytes)

    event = BounceEvent._from_alsa(alsa_event)
    assert isinstance(event, BounceEvent)
    assert event.type == EventType.BOUNCE

    assert event.tag == 9
    assert event.data == b"0123456789"
    assert repr(event) == "<BounceEvent data=b'0123456789'>"


@pytest.mark.parametrize("event_class,event_type",
                         [(UserVar0Event, EventType.USR_VAR0),
                          (UserVar1Event, EventType.USR_VAR1),
                          (UserVar2Event, EventType.USR_VAR2),
                          (UserVar3Event, EventType.USR_VAR3)])
def test_user_var_event(event_class, event_type):
    event = event_class(data=b"\xf012345\xf7")
    assert isinstance(event, event_class)
    assert isinstance(event, Event)
    assert isinstance(event, ExternalDataEventBase)
    assert event.type == event_type
    event.data == b"\xf012345\xf7"
    assert repr(event) == f"<{event_class.__name__} data=b'\\xf012345\\xf7'>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == event_type
    assert alsa_event.tag == 0
    assert alsa_event.data.ext.len == 7
    assert EventFlags.EVENT_LENGTH_VARIABLE in EventFlags(alsa_event.flags)
    assert ffi.buffer(alsa_event.data.ext.ptr, 7)[:] == b"\xf012345\xf7"

    event = event_class(b"abcd", tag=3)
    assert isinstance(event, event_class)
    assert isinstance(event, Event)
    assert event.type == event_type
    assert event.tag == 3
    assert repr(event) == f"<{event_class.__name__} data=b'abcd'>"

    alsa_event = ffi.new("snd_seq_event_t *")
    result = event._to_alsa(alsa_event)
    assert result is alsa_event
    assert alsa_event.type == event_type
    assert alsa_event.tag == 3
    assert alsa_event.data.ext.len == 4
    assert ffi.buffer(alsa_event.data.ext.ptr, 4)[:] == b"abcd"

    alsa_event = ffi.new("snd_seq_event_t *")
    alsa_event.type = event_type
    alsa_event.flags = EventFlags.EVENT_LENGTH_VARIABLE
    alsa_event.tag = 9
    alsa_event.data.ext.len = 10
    data_bytes = b"0123456789"
    alsa_event.data.ext.ptr = ffi.from_buffer(data_bytes)

    event = event_class._from_alsa(alsa_event)
    assert isinstance(event, event_class)
    assert event.type == event_type

    assert event.tag == 9
    assert event.data == b"0123456789"
    assert repr(event) == f"<{event_class.__name__} data=b'0123456789'>"
