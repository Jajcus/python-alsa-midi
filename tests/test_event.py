
import pytest

from alsa_midi import Address, Event, EventFlags, EventType, RealTime, alsa, ffi


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
