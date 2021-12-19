
from enum import IntEnum
from typing import TYPE_CHECKING, Any, NewType, Optional, Tuple, Union

from ._ffi import alsa, ffi
from .address import Address, AddressType
from .util import _ensure_4bit, _ensure_7bit

if TYPE_CHECKING:
    from .port import Port
    from .queue import Queue


class EventType(IntEnum):
    SYSTEM = alsa.SND_SEQ_EVENT_SYSTEM
    RESULT = alsa.SND_SEQ_EVENT_RESULT
    NOTE = alsa.SND_SEQ_EVENT_NOTE
    NOTEON = alsa.SND_SEQ_EVENT_NOTEON
    NOTEOFF = alsa.SND_SEQ_EVENT_NOTEOFF
    KEYPRESS = alsa.SND_SEQ_EVENT_KEYPRESS
    CONTROLLER = alsa.SND_SEQ_EVENT_CONTROLLER
    PGMCHANGE = alsa.SND_SEQ_EVENT_PGMCHANGE
    CHANPRESS = alsa.SND_SEQ_EVENT_CHANPRESS
    PITCHBEND = alsa.SND_SEQ_EVENT_PITCHBEND
    CONTROL14 = alsa.SND_SEQ_EVENT_CONTROL14
    NONREGPARAM = alsa.SND_SEQ_EVENT_NONREGPARAM
    REGPARAM = alsa.SND_SEQ_EVENT_REGPARAM
    SONGPOS = alsa.SND_SEQ_EVENT_SONGPOS
    SONGSEL = alsa.SND_SEQ_EVENT_SONGSEL
    QFRAME = alsa.SND_SEQ_EVENT_QFRAME
    TIMESIGN = alsa.SND_SEQ_EVENT_TIMESIGN
    KEYSIGN = alsa.SND_SEQ_EVENT_KEYSIGN
    START = alsa.SND_SEQ_EVENT_START
    CONTINUE = alsa.SND_SEQ_EVENT_CONTINUE
    STOP = alsa.SND_SEQ_EVENT_STOP
    SETPOS_TICK = alsa.SND_SEQ_EVENT_SETPOS_TICK
    SETPOS_TIME = alsa.SND_SEQ_EVENT_SETPOS_TIME
    TEMPO = alsa.SND_SEQ_EVENT_TEMPO
    CLOCK = alsa.SND_SEQ_EVENT_CLOCK
    TICK = alsa.SND_SEQ_EVENT_TICK
    QUEUE_SKEW = alsa.SND_SEQ_EVENT_QUEUE_SKEW
    SYNC_POS = alsa.SND_SEQ_EVENT_SYNC_POS
    TUNE_REQUEST = alsa.SND_SEQ_EVENT_TUNE_REQUEST
    RESET = alsa.SND_SEQ_EVENT_RESET
    SENSING = alsa.SND_SEQ_EVENT_SENSING
    ECHO = alsa.SND_SEQ_EVENT_ECHO
    OSS = alsa.SND_SEQ_EVENT_OSS
    CLIENT_START = alsa.SND_SEQ_EVENT_CLIENT_START
    CLIENT_EXIT = alsa.SND_SEQ_EVENT_CLIENT_EXIT
    CLIENT_CHANGE = alsa.SND_SEQ_EVENT_CLIENT_CHANGE
    PORT_START = alsa.SND_SEQ_EVENT_PORT_START
    PORT_EXIT = alsa.SND_SEQ_EVENT_PORT_EXIT
    PORT_CHANGE = alsa.SND_SEQ_EVENT_PORT_CHANGE
    PORT_SUBSCRIBED = alsa.SND_SEQ_EVENT_PORT_SUBSCRIBED
    PORT_UNSUBSCRIBED = alsa.SND_SEQ_EVENT_PORT_UNSUBSCRIBED
    USR0 = alsa.SND_SEQ_EVENT_USR0
    USR1 = alsa.SND_SEQ_EVENT_USR1
    USR2 = alsa.SND_SEQ_EVENT_USR2
    USR3 = alsa.SND_SEQ_EVENT_USR3
    USR4 = alsa.SND_SEQ_EVENT_USR4
    USR5 = alsa.SND_SEQ_EVENT_USR5
    USR6 = alsa.SND_SEQ_EVENT_USR6
    USR7 = alsa.SND_SEQ_EVENT_USR7
    USR8 = alsa.SND_SEQ_EVENT_USR8
    USR9 = alsa.SND_SEQ_EVENT_USR9
    SYSEX = alsa.SND_SEQ_EVENT_SYSEX
    BOUNCE = alsa.SND_SEQ_EVENT_BOUNCE
    USR_VAR0 = alsa.SND_SEQ_EVENT_USR_VAR0
    USR_VAR1 = alsa.SND_SEQ_EVENT_USR_VAR1
    USR_VAR2 = alsa.SND_SEQ_EVENT_USR_VAR2
    USR_VAR3 = alsa.SND_SEQ_EVENT_USR_VAR3
    USR_VAR4 = alsa.SND_SEQ_EVENT_USR_VAR4
    NONE = alsa.SND_SEQ_EVENT_NONE

    @classmethod
    def _missing_(cls, value):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj._name_ = f"UNKNOWN_{value}"
        return obj


_snd_seq_event_t = NewType("_snd_seq_event_t", Any)


class Event:
    _specialized = {}
    type = None

    def __init__(self,
                 type: EventType,
                 *,
                 flags: Optional[int] = 0,
                 tag: int = 0,
                 queue: Optional[int] = None,
                 time: Optional[float] = None,
                 tick: Optional[int] = None,
                 source: Optional[Tuple[int, int]] = None,
                 dest: Optional[Tuple[int, int]] = None,
                 relative: Optional[bool] = None,
                 raw_data: bytes = None,
                 ):

        self.type = type
        self.flags = flags
        self.tag = tag

        self.queue = queue

        if time is not None and tick is not None:
            raise ValueError("Either 'time' or 'tick' may be set, not both")

        self.time = time
        self.tick = tick

        self.relative = relative

        if source is not None:
            self.source = Address(*source)
        else:
            self.source = None
        if dest is not None:
            self.dest = Address(*dest)
        else:
            self.dest = None

        self.raw_data = raw_data

    def __repr__(self):
        if self.type is None:
            type_s = " unknown"
        elif self.type == self.__class__.type:
            type_s = ""
        else:
            type_s = " " + self.type.name
        return f"<{self.__class__.__name__}{type_s}>"

    @classmethod
    def _from_alsa(cls, event: _snd_seq_event_t, **kwargs):
        flags = event.flags
        if (flags & alsa.SND_SEQ_TIME_STAMP_MASK) == alsa.SND_SEQ_TIME_STAMP_REAL:
            ev_time = event.time.time.tv_sec + 0.000000001 * event.time.tim.tv_nsec
        else:
            ev_time = None
        if (flags & alsa.SND_SEQ_TIME_STAMP_MASK) == alsa.SND_SEQ_TIME_STAMP_TICK:
            ev_tick = event.time.tick
        else:
            ev_tick = None
        relative = (flags & alsa.SND_SEQ_TIME_MODE_MASK) == alsa.SND_SEQ_TIME_MODE_REL
        raw_data = bytes(ffi.buffer(ffi.addressof(event.data)))
        if cls.type is None:
            kwargs["type"] = EventType(event.type)
        return cls(flags=flags,
                   tag=event.flags,
                   queue=event.queue,
                   time=ev_time,
                   tick=ev_tick,
                   relative=relative,
                   source=Address(event.source.client, event.source.port),
                   dest=Address(event.dest.client, event.dest.port),
                   raw_data=raw_data,
                   **kwargs)

    def _to_alsa(self, *,
                 queue: Union['Queue', int] = None,
                 port: Union['Port', int] = None,
                 dest: AddressType = None
                 ) -> _snd_seq_event_t:
        event: _snd_seq_event_t = ffi.new("snd_seq_event_t *")
        assert self.type is not None
        event.type = int(self.type)
        if self.flags is not None:
            flags = self.flags
        else:
            flags = 0
        event.tag = self.tag
        if queue is not None:
            if isinstance(queue, int):
                event.queue = queue
            else:
                event.queue = queue.queue_id
        elif self.queue is not None:
            event.queue = self.queue
        else:
            event.queue = alsa.SND_SEQ_QUEUE_DIRECT
        assert self.time is None or self.tick is None
        if self.time is not None:
            sec = int(self.time)
            nsec = int((self.time - sec) * 1000000000)
            event.time.time.tv_sec = sec
            event.time.time.tv_nsec = nsec
            flags &= ~(alsa.SND_SEQ_TIME_STAMP_MASK | alsa.SND_SEQ_TIME_STAMP_REAL)
        if self.tick is not None:
            event.time.tick = self.tick
            flags &= ~(alsa.SND_SEQ_TIME_STAMP_MASK | alsa.SND_SEQ_TIME_STAMP_TICK)
        if self.relative is not None:
            rel = alsa.SND_SEQ_TIME_MODE_REL if self.relative else alsa.SND_SEQ_TIME_MODE_ABS
            flags &= ~(alsa.SND_SEQ_TIME_MODE_MASK | rel)
        if port is not None:
            if isinstance(port, int):
                event.source.port = port
            else:
                event.source.port = port.port_id
        elif self.source is not None:
            event.source.client = self.source.client_id
            event.source.port = self.source.port_id
        if dest is not None:
            client_id, port_id = Address(dest)
            event.dest.client = client_id
            event.dest.port = port_id
        elif self.dest is not None:
            event.dest.client = self.dest.client_id
            event.dest.port = self.dest.port_id
        else:
            event.dest.client = alsa.SND_SEQ_ADDRESS_SUBSCRIBERS

        if self.__class__ == Event and self.raw_data is not None:
            # not for subclasses:
            # set raw data
            buf = ffi.buffer(ffi.addressof(event.data))
            buf[:min(len(self.raw_data), 12)] = self.raw_data[:12]

        event.flags = flags

        return event


def _specialized_event_class(event_type):
    def decorator(cls):
        cls.type = event_type
        Event._specialized[event_type.value] = cls
        return cls
    return decorator


class ResultEventBase(Event):
    def __init__(self,
                 event: int,
                 result: int,
                 **kwargs):
        assert self.type is not None
        super().__init__(self.type, **kwargs)
        self.event = event
        self.result = result

    def __repr__(self):
        return (f"<{self.__class__.__name__} event={self.event} result={self.result}>")

    @classmethod
    def _from_alsa(cls, event: _snd_seq_event_t, **kwargs):
        kwargs["event"] = event.data.result.event
        kwargs["result"] = event.data.result.result
        return super()._from_alsa(event, **kwargs)

    def _to_alsa(self, **kwargs):
        event: _snd_seq_event_t = super()._to_alsa(**kwargs)
        event.data.result.event = self.event
        event.data.result.result = self.result
        return event


class NoteEventBase(Event):
    def __init__(self,
                 note: int,
                 channel: int = 0,
                 velocity: int = 127,
                 **kwargs):
        assert self.type is not None
        super().__init__(self.type, **kwargs)
        self.channel = _ensure_4bit(channel)
        self.note = _ensure_7bit(note)
        self.velocity = _ensure_7bit(velocity)

    def __repr__(self):
        return (f"<{self.__class__.__name__} channel={self.channel} note={self.note}"
                f" velocity={self.velocity}>")

    @classmethod
    def _from_alsa(cls, event: _snd_seq_event_t, **kwargs):
        kwargs["note"] = event.data.note.note
        kwargs["channel"] = event.data.note.channel
        kwargs["velocity"] = event.data.note.velocity
        return super()._from_alsa(event, **kwargs)

    def _to_alsa(self, **kwargs):
        event: _snd_seq_event_t = super()._to_alsa(**kwargs)
        event.data.note.note = self.note
        event.data.note.channel = self.channel
        event.data.note.velocity = self.velocity
        return event


class ControlChangeEventBase(Event):
    def __init__(self,
                 channel: int,
                 param: int,
                 value: int,
                 **kwargs):
        assert self.type is not None
        super().__init__(self.type, **kwargs)
        self.channel = channel
        self.param = param
        self.value = value

    def __repr__(self):
        return (f"<{self.__class__.__name__} channel={self.channel}"
                f" param={self.param} value={self.value}>")

    @classmethod
    def _from_alsa(cls, event: _snd_seq_event_t, **kwargs):
        kwargs["channel"] = event.data.control.channel
        kwargs["param"] = event.data.control.param
        kwargs["value"] = event.data.control.value
        return super()._from_alsa(event, **kwargs)

    def _to_alsa(self, **kwargs):
        event: _snd_seq_event_t = super()._to_alsa(**kwargs)
        event.data.result.channel = self.channel
        event.data.result.param = self.param
        event.data.result.value = self.value
        return event


class ParamChangeEventBase(Event):
    def __init__(self,
                 channel: int,
                 value: int,
                 **kwargs):
        assert self.type is not None
        super().__init__(self.type, **kwargs)
        self.channel = channel
        self.value = value

    def __repr__(self):
        return (f"<{self.__class__.__name__} channel={self.channel} value={self.value}>")

    @classmethod
    def _from_alsa(cls, event: _snd_seq_event_t, **kwargs):
        kwargs["channel"] = event.data.control.channel
        kwargs["value"] = event.data.control.value
        return super()._from_alsa(event, **kwargs)

    def _to_alsa(self, **kwargs):
        event: _snd_seq_event_t = super()._to_alsa(**kwargs)
        event.data.result.channel = self.channel
        event.data.result.value = self.value
        return event


class QueueControlEventBase(Event):
    def __init__(self,
                 control_queue: Optional[Union[int, 'Queue']] = None,
                 **kwargs):
        assert self.type is not None
        super().__init__(self.type, **kwargs)
        if isinstance(control_queue, int):
            self.control_queue = control_queue
        elif control_queue is not None:
            self.control_queue = control_queue.queue_id
        else:
            self.control_queue = None

    def __repr__(self):
        if self.control_queue is not None:
            return (f"<{self.__class__.__name__} queue={self.queue}>")
        else:
            return (f"<{self.__class__.__name__}>")

    @classmethod
    def _from_alsa(cls, event: _snd_seq_event_t, **kwargs):
        kwargs["control_queue"] = event.data.queue.queue
        return super()._from_alsa(event, **kwargs)

    def _to_alsa(self, **kwargs):
        event: _snd_seq_event_t = super()._to_alsa(**kwargs)
        queue = self.control_queue
        if queue is not None:
            event.data.queue.queue_id = queue
        return event


@_specialized_event_class(EventType.SYSTEM)
class SystemEvent(ResultEventBase):
    pass


@_specialized_event_class(EventType.RESULT)
class ResultEvent(ResultEventBase):
    pass


@_specialized_event_class(EventType.NOTE)
class NoteEvent(NoteEventBase):
    def __init__(self,
                 note: int,
                 channel: int = 0,
                 velocity: int = 127,
                 off_velocity: int = 0,
                 duration: int = 0,
                 **kwargs):
        super().__init__(note, channel, velocity, **kwargs)
        self.off_velocity = _ensure_7bit(off_velocity)
        self.duration = duration

    def __repr__(self):
        return (f"<{self.__class__.__name__} channel={self.channel} note={self.note}"
                f" velocity={self.velocity} duration={self.duration}"
                f" off_velocity={self.off_velocity}>")

    @classmethod
    def _from_alsa(cls, event: _snd_seq_event_t, **kwargs):
        kwargs["off_velocity"] = event.data.note.off_velocity
        kwargs["duration"] = event.data.note.duration
        return super()._from_alsa(event, **kwargs)

    def _to_alsa(self, **kwargs):
        event: _snd_seq_event_t = super()._to_alsa(**kwargs)
        event.data.note.off_velocity = self.off_velocity
        event.data.note.duration = self.duration
        return event


@_specialized_event_class(EventType.NOTEON)
class NoteOnEvent(NoteEventBase):
    pass


@_specialized_event_class(EventType.NOTEOFF)
class NoteOffEvent(NoteEventBase):
    pass


@_specialized_event_class(EventType.KEYPRESS)
class KeyPressEvent(NoteEventBase):
    pass


@_specialized_event_class(EventType.CONTROLLER)
class ControlChangeEvent(ControlChangeEventBase):
    pass


@_specialized_event_class(EventType.PGMCHANGE)
class ProgramChangeEvent(ParamChangeEventBase):
    pass


@_specialized_event_class(EventType.CHANPRESS)
class ChannelPressureEvent(ParamChangeEventBase):
    pass


@_specialized_event_class(EventType.PITCHBEND)
class PitchBendEvent(ParamChangeEventBase):
    pass


@_specialized_event_class(EventType.CONTROL14)
class Control14BitChangeEvent(ControlChangeEventBase):
    pass


@_specialized_event_class(EventType.NONREGPARAM)
class NonRegisteredParameterChangeEvent(ControlChangeEventBase):
    pass


@_specialized_event_class(EventType.REGPARAM)
class RegisteredParameterChangeEvent(ControlChangeEventBase):
    pass


@_specialized_event_class(EventType.SONGPOS)
class SongPositionPointerEvent(ParamChangeEventBase):
    pass


@_specialized_event_class(EventType.SONGSEL)
class SongSelectEvent(ParamChangeEventBase):
    pass

# TODO: TIMESIGN

# TODO: KEYSIGN


@_specialized_event_class(EventType.START)
class StartEvent(QueueControlEventBase):
    pass


@_specialized_event_class(EventType.CONTINUE)
class ContinueEvent(QueueControlEventBase):
    pass


@_specialized_event_class(EventType.STOP)
class StopEvent(QueueControlEventBase):
    pass


@_specialized_event_class(EventType.SETPOS_TICK)
class SetQueuePositionTick(QueueControlEventBase):
    def __init__(self,
                 tick: int,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tick = tick

    def __repr__(self):
        if self.control_queue is not None:
            return (f"<{self.__class__.__name__} queue={self.queue} tick={self.tick}>")
        else:
            return (f"<{self.__class__.__name__} tick={self.tick}>")

    @classmethod
    def _from_alsa(cls, event: _snd_seq_event_t, **kwargs):
        kwargs["tick"] = event.data.queue.time.tick
        return super()._from_alsa(event, **kwargs)

    def _to_alsa(self, **kwargs):
        event: _snd_seq_event_t = super()._to_alsa(**kwargs)
        event.data.queue.time.tick = self.tick
        return event


@_specialized_event_class(EventType.SETPOS_TIME)
class SetQueuePositionTime(QueueControlEventBase):
    def __init__(self,
                 time: float,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.time = float(time)

    def __repr__(self):
        if self.control_queue is not None:
            return (f"<{self.__class__.__name__} queue={self.queue} time={self.time}>")
        else:
            return (f"<{self.__class__.__name__} time={self.time}>")

    @classmethod
    def _from_alsa(cls, event: _snd_seq_event_t, **kwargs):
        kwargs["time"] = (event.data.queue.time.time.tv_sec
                          + 0.000000001 * event.data.queue.time.time.tv_nsec)
        return super()._from_alsa(event, **kwargs)

    def _to_alsa(self, **kwargs):
        event: _snd_seq_event_t = super()._to_alsa(**kwargs)
        sec = int(self.time)
        nsec = int((self.time - sec) * 1000000000)
        event.data.queue.time.time.tv_sec = sec
        event.data.queue.time.time.tv_nsec = nsec
        return event


__all__ = [
        "EventType", "Event",
        "NoteEventBase",
        "NoteOnEvent", "NoteOffEvent"
        ]
