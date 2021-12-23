
from enum import IntEnum, IntFlag
from typing import TYPE_CHECKING, Any, Iterable, NewType, Optional, Union

from ._ffi import alsa, ffi
from .address import Address, AddressType
from .exceptions import StateError
from .util import _ensure_4bit, _ensure_7bit

if TYPE_CHECKING:
    from .port import Port
    from .queue import Queue


class RealTime:
    __slots__ = ('seconds', 'nanoseconds')

    seconds: int
    nanoseconds: int

    def __init__(self, seconds: Union[float, int, str, 'RealTime'], nanoseconds: int = 0):
        if isinstance(seconds, RealTime):
            self.seconds = seconds.seconds
            self.nanoseconds = seconds.nanoseconds + nanoseconds
        else:
            if isinstance(seconds, str):
                if "." in seconds:
                    seconds = float(seconds)
                else:
                    seconds = int(seconds)
            if isinstance(seconds, float):
                self.seconds = int(seconds)
                self.nanoseconds = int(nanoseconds + 1000000000 * (seconds - self.seconds))
            else:
                self.seconds = seconds
                self.nanoseconds = nanoseconds
        if self.nanoseconds >= 1000000000:
            self.seconds += self.nanoseconds // 1000000000
            self.nanoseconds = self.nanoseconds % 1000000000
        if self.seconds < 0 or self.nanoseconds < 0:
            raise ValueError("Negative RealTime is not allowed")

    def __repr__(self):
        return f"RealTime(seconds={self.seconds}, nanoseconds={self.nanoseconds})"

    def __str__(self):
        return f"{self.seconds}.{self.nanoseconds:09d}"

    def __int__(self):
        return self.seconds

    def __float__(self):
        return float(self.seconds) + self.nanoseconds / 1000000000


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


class EventFlags(IntFlag):
    TIME_STAMP_TICK = alsa.SND_SEQ_TIME_STAMP_TICK
    TIME_STAMP_REAL = alsa.SND_SEQ_TIME_STAMP_REAL
    TIME_STAMP_MASK = alsa.SND_SEQ_TIME_STAMP_MASK

    TIME_MODE_ABS = alsa.SND_SEQ_TIME_MODE_ABS
    TIME_MODE_REL = alsa.SND_SEQ_TIME_MODE_REL
    TIME_MODE_MASK = alsa.SND_SEQ_TIME_MODE_MASK

    EVENT_LENGTH_FIXED = alsa.SND_SEQ_EVENT_LENGTH_FIXED
    EVENT_LENGTH_VARIABLE = alsa.SND_SEQ_EVENT_LENGTH_VARIABLE
    EVENT_LENGTH_VARUSR = alsa.SND_SEQ_EVENT_LENGTH_VARUSR
    EVENT_LENGTH_MASK = alsa.SND_SEQ_EVENT_LENGTH_MASK

    PRIORITY_NORMAL = alsa.SND_SEQ_PRIORITY_NORMAL
    PRIORITY_HIGH = alsa.SND_SEQ_PRIORITY_HIGH
    PRIORITY_MASK = alsa.SND_SEQ_PRIORITY_MASK


_snd_seq_event_t = NewType("_snd_seq_event_t", Any)


class Event:
    _specialized = {}
    type = None

    flags: Optional[EventFlags]
    tag: int
    queue_id: Optional[int]
    time: Optional[RealTime]
    tick: Optional[int]
    source: Optional[Address]
    dest: Optional[Address]
    relative: Optional[bool]
    raw_data: Optional[bytes]

    def __init__(self,
                 type: Optional[EventType],
                 *,
                 flags: Optional[Union[EventFlags, int]] = 0,
                 tag: int = 0,
                 queue_id: Optional[int] = None,
                 time: Optional[RealTime] = None,
                 tick: Optional[int] = None,
                 source: Optional[AddressType] = None,
                 dest: Optional[AddressType] = None,
                 relative: Optional[bool] = None,
                 raw_data: bytes = None,
                 ):

        self.type = type
        if flags is not None:
            self.flags = EventFlags(flags)
        else:
            flags = None
        self.tag = tag

        self.queue_id = queue_id

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
        if (flags & EventFlags.TIME_STAMP_MASK) == EventFlags.TIME_STAMP_REAL:
            ev_time = RealTime(event.time.time.tv_sec, event.time.time.tv_nsec)
        else:
            ev_time = None
        if (flags & EventFlags.TIME_STAMP_MASK) == EventFlags.TIME_STAMP_TICK:
            ev_tick = event.time.tick
        else:
            ev_tick = None
        relative = (flags & EventFlags.TIME_MODE_MASK) == EventFlags.TIME_MODE_REL
        raw_data = bytes(ffi.buffer(ffi.addressof(event.data)))
        if cls.type is None:
            kwargs["type"] = EventType(event.type)
        return cls(flags=flags,
                   tag=event.flags,
                   queue_id=event.queue,
                   time=ev_time,
                   tick=ev_tick,
                   relative=relative,
                   source=Address(event.source.client, event.source.port),
                   dest=Address(event.dest.client, event.dest.port),
                   raw_data=raw_data,
                   **kwargs)

    def _to_alsa(self, event: _snd_seq_event_t, *,
                 queue: Union['Queue', int] = None,
                 port: Union['Port', int] = None,
                 dest: AddressType = None
                 ) -> _snd_seq_event_t:
        if self.type is not None:
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
        elif self.queue_id is not None:
            event.queue = self.queue_id
        else:
            event.queue = alsa.SND_SEQ_QUEUE_DIRECT
        assert self.time is None or self.tick is None
        if self.time is not None:
            event.time.time.tv_sec = self.time.seconds
            event.time.time.tv_nsec = self.time.nanoseconds
            flags &= ~(EventFlags.TIME_STAMP_MASK | EventFlags.TIME_STAMP_REAL)
        if self.tick is not None:
            event.time.tick = self.tick
            flags &= ~(EventFlags.TIME_STAMP_MASK | EventFlags.TIME_STAMP_TICK)
        if self.relative is not None:
            rel = EventFlags.TIME_MODE_REL if self.relative else EventFlags.TIME_MODE_ABS
            flags &= ~(EventFlags.TIME_MODE_MASK | rel)
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

        if self.raw_data is not None:
            # set raw data
            # may be overwritten by structured data in a specialized class
            buf = ffi.buffer(ffi.addressof(event.data))
            buf[:min(len(self.raw_data), 12)] = self.raw_data[:12]

        event.flags = int(flags)

        return event


class MidiBytesEvent(Event):
    midi_bytes: bytes

    def __init__(self,
                 midi_bytes: Union[bytes, Iterable[int]],
                 **kwargs):
        super().__init__(None, **kwargs)
        self.midi_bytes = bytes(midi_bytes)

    def __repr__(self):
        length = self.midi_bytes
        if len(length) < 32:
            hex_bytes = " ".join(f"{b:02X}" for b in self.midi_bytes)
        else:
            hex_bytes = " ".join(f"{b:02X}" for b in self.midi_bytes[:2])
            hex_bytes += " .. <{length - 4} more> .. "
            hex_bytes = " ".join(f"{b:02X}" for b in self.midi_bytes[-2:])
        return (f"<{self.__class__.__name__} {hex_bytes}>")


def _specialized_event_class(event_type):
    def decorator(cls):
        cls.type = event_type
        Event._specialized[event_type.value] = cls
        return cls
    return decorator


class ResultEventBase(Event):
    event: int
    result: int

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

    def _to_alsa(self, event: _snd_seq_event_t, **kwargs):
        super()._to_alsa(event, **kwargs)
        event.data.result.event = self.event
        event.data.result.result = self.result
        return event


class NoteEventBase(Event):
    note: int
    channel: int
    velocity: int

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

    def _to_alsa(self, event: _snd_seq_event_t, **kwargs):
        super()._to_alsa(event, **kwargs)
        event.data.note.note = self.note
        event.data.note.channel = self.channel
        event.data.note.velocity = self.velocity
        return event


class ControlChangeEventBase(Event):
    channel: int
    param: int
    value: int

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

    def _to_alsa(self, event: _snd_seq_event_t, **kwargs):
        super()._to_alsa(event, **kwargs)
        event.data.result.channel = self.channel
        event.data.result.param = self.param
        event.data.result.value = self.value
        return event


class ParamChangeEventBase(Event):
    channel: int
    value: int

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

    def _to_alsa(self, event: _snd_seq_event_t, **kwargs):
        super()._to_alsa(event, **kwargs)
        event.data.result.channel = self.channel
        event.data.result.value = self.value
        return event


class QueueControlEventBase(Event):
    control_queue: int

    def __init__(self,
                 control_queue: Union[int, 'Queue'],
                 **kwargs):
        assert self.type is not None
        super().__init__(self.type, **kwargs)
        if isinstance(control_queue, int):
            self.control_queue = control_queue
        elif control_queue.queue_id is not None:
            self.control_queue = control_queue.queue_id
        else:
            raise StateError("Queue already closed")

    def __repr__(self):
        if self.control_queue is not None:
            return (f"<{self.__class__.__name__} queue={self.control_queue}>")
        else:
            return (f"<{self.__class__.__name__}>")

    @classmethod
    def _from_alsa(cls, event: _snd_seq_event_t, **kwargs):
        kwargs["control_queue"] = event.data.queue.queue
        return super()._from_alsa(event, **kwargs)

    def _to_alsa(self, event: _snd_seq_event_t, **kwargs):
        super()._to_alsa(event, **kwargs)
        queue_id = self.control_queue
        if queue_id is not None:
            event.data.queue.queue = queue_id
        return event


class AddressEventBase(Event):
    addr: Address

    def __init__(self,
                 addr: AddressType,
                 **kwargs):
        assert self.type is not None
        super().__init__(self.type, **kwargs)
        self.addr = Address(addr)

    def __repr__(self):
        return (f"<{self.__class__.__name__} {self.addr}>")

    @classmethod
    def _from_alsa(cls, event: _snd_seq_event_t, **kwargs):
        kwargs["addr"] = Address(event.data.addr.client, event.data.addr.port)
        return super()._from_alsa(event, **kwargs)

    def _to_alsa(self, event: _snd_seq_event_t, **kwargs):
        super()._to_alsa(event, **kwargs)
        event.event.data.addr.client = self.addr.client_id
        event.event.data.addr.port = self.addr.port_id
        return event


class ConnectEventBase(Event):
    connect_sender: Address
    connect_dest: Address

    def __init__(self,
                 connect_sender: AddressType,
                 connect_dest: AddressType,
                 **kwargs):
        assert self.type is not None
        super().__init__(self.type, **kwargs)
        self.connect_sender = Address(connect_sender)
        self.connect_dest = Address(connect_dest)

    def __repr__(self):
        return (f"<{self.__class__.__name__} from {self.connect_sender} to {self.connect_dest}>")

    @classmethod
    def _from_alsa(cls, event: _snd_seq_event_t, **kwargs):
        kwargs["connect_sender"] = Address(event.data.connect.sender.client,
                                           event.data.connect.sender.port)
        kwargs["connect_dest"] = Address(event.data.connect.dest.client,
                                         event.data.connect.dest.port)
        return super()._from_alsa(event, **kwargs)

    def _to_alsa(self, event: _snd_seq_event_t, **kwargs):
        super()._to_alsa(event, **kwargs)
        event.event.data.connect.sender.client = self.connect_sender.client_id
        event.event.data.connect.sender.port = self.connect_sender.port_id
        event.event.data.connect.dest.client = self.connect_dest.client_id
        event.event.data.connect.dest.port = self.connect_dest.port_id
        return event


class ExternalDataEventBase(Event):
    data: bytes

    def __init__(self,
                 data: bytes,
                 **kwargs):
        assert self.type is not None
        super().__init__(self.type, **kwargs)
        self.data = bytes(data)

    def __repr__(self):
        if len(self.data) < 32:
            return (f"<{self.__class__.__name__} data={self.data!r}>")
        else:
            return (f"<{self.__class__.__name__} data=<{len(self.data)} bytes>>")

    @classmethod
    def _from_alsa(cls, event: _snd_seq_event_t, **kwargs):
        data = bytes(ffi.buffer(event.data.ext.ptr, event.data.ext.len))
        kwargs["data"] = data
        return super()._from_alsa(event, **kwargs)

    def _to_alsa(self, event: _snd_seq_event_t, **kwargs):
        super()._to_alsa(event, **kwargs)
        event.flags |= EventFlags.EVENT_LENGTH_VARIABLE
        event.data.ext.len = len(self.data)
        event.data.ext.ptr = ffi.from_buffer(self.data)
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

    def _to_alsa(self, event: _snd_seq_event_t, **kwargs):
        super()._to_alsa(event, **kwargs)
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


# how is it encoded into snd_seq_ev_ctrl_t?
@_specialized_event_class(EventType.TIMESIGN)
class TimeSignatureEvent(ParamChangeEventBase):
    pass


# how is it encoded into snd_seq_ev_ctrl_t?
@_specialized_event_class(EventType.KEYSIGN)
class KeySignatureEvent(ParamChangeEventBase):
    pass


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
class SetQueuePositionTickEvent(QueueControlEventBase):
    def __init__(self,
                 position: int,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.position = position

    def __repr__(self):
        if self.control_queue is not None:
            return (f"<{self.__class__.__name__} queue={self.control_queue} tick={self.position}>")
        else:
            return (f"<{self.__class__.__name__} tick={self.position}>")

    @classmethod
    def _from_alsa(cls, event: _snd_seq_event_t, **kwargs):
        kwargs["position"] = event.data.queue.time.tick
        return super()._from_alsa(event, **kwargs)

    def _to_alsa(self, event: _snd_seq_event_t, **kwargs):
        super()._to_alsa(event, **kwargs)
        event.data.queue.time.tick = self.position
        return event


@_specialized_event_class(EventType.SETPOS_TIME)
class SetQueuePositionTimeEvent(QueueControlEventBase):
    def __init__(self,
                 time: Union[RealTime, int, float],
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.position = RealTime(time)

    def __repr__(self):
        if self.control_queue is not None:
            return (f"<{self.__class__.__name__} queue={self.control_queue} time={self.position}>")
        else:
            return (f"<{self.__class__.__name__} time={self.position}>")

    @classmethod
    def _from_alsa(cls, event: _snd_seq_event_t, **kwargs):
        kwargs["time"] = RealTime(event.data.queue.param.time.time.tv_sec,
                                  event.data.queue.param.time.time.tv_nsec)
        return super()._from_alsa(event, **kwargs)

    def _to_alsa(self, event: _snd_seq_event_t, **kwargs):
        super()._to_alsa(event, **kwargs)
        event.data.queue.param.time.time.tv_sec = self.position.seconds
        event.data.queue.param.time.time.tv_nsec = self.position.nanoseconds
        return event


@_specialized_event_class(EventType.TEMPO)
class SetQueueTempoEvent(QueueControlEventBase):
    def __init__(self,
                 midi_tempo: int = None,
                 *,
                 bpm: float = None,
                 **kwargs):
        if midi_tempo is not None and bpm is not None:
            raise ValueError("Either tempo or must be provided, not both.")
        if midi_tempo is not None:
            self.midi_tempo = midi_tempo
        elif bpm is not None:
            self.midi_tempo = int(60000000.0 / bpm)
        else:
            raise ValueError("Either tempo or must be provided.")
        super().__init__(**kwargs)

    @property
    def bpm(self):
        return 60000000.0 / self.midi_tempo

    def __repr__(self):
        tempo = self.midi_tempo
        bpm = self.bpm
        if self.control_queue is not None:
            return (f"<{self.__class__.__name__} queue={self.control_queue}"
                    f" tempo={tempo} ({bpm} bpm)>")
        else:
            return (f"<{self.__class__.__name__} tempo={tempo} ({bpm} bpm)>")

    @classmethod
    def _from_alsa(cls, event: _snd_seq_event_t, **kwargs):
        kwargs["midi_tempo"] = event.data.queue.param.value
        return super()._from_alsa(event, **kwargs)

    def _to_alsa(self, event: _snd_seq_event_t, **kwargs):
        super()._to_alsa(event, **kwargs)
        event.data.queue.param.value = self.midi_tempo
        return event


@_specialized_event_class(EventType.CLOCK)
class ClockEvent(QueueControlEventBase):
    pass


@_specialized_event_class(EventType.TICK)
class TickEvent(QueueControlEventBase):
    pass


@_specialized_event_class(EventType.QUEUE_SKEW)
class QueueSkewEvent(QueueControlEventBase):
    value: int
    base: int

    def __init__(self,
                 value: int,
                 base: int,
                 *args, **kwargs):
        self.value = value
        self.base = base
        super().__init__(*args, **kwargs)

    def __repr__(self):
        if self.control_queue is not None:
            return (f"<{self.__class__.__name__} queue={self.control_queue}"
                    f" value={self.value} base={self.base}>")
        else:
            return (f"<{self.__class__.__name__} value={self.value} base={self.base}>")

    @classmethod
    def _from_alsa(cls, event: _snd_seq_event_t, **kwargs):
        kwargs["value"] = event.data.queue.param.skew.value
        kwargs["base"] = event.data.queue.param.skew.base
        return super()._from_alsa(event, **kwargs)

    def _to_alsa(self, event: _snd_seq_event_t, **kwargs):
        super()._to_alsa(event, **kwargs)
        event.data.queue.param.skew.value = self.value
        event.data.queue.param.skew.base = self.base
        return event


@_specialized_event_class(EventType.SYNC_POS)
class SyncPositionChangedEvent(QueueControlEventBase):
    position: int

    def __init__(self,
                 position: int,
                 *args, **kwargs):
        self.position = position
        super().__init__(*args, **kwargs)

    def __repr__(self):
        if self.control_queue is not None:
            return (f"<{self.__class__.__name__} queue={self.control_queue}"
                    f" position={self.position}>")
        else:
            return (f"<{self.__class__.__name__} position={self.position}>")

    @classmethod
    def _from_alsa(cls, event: _snd_seq_event_t, **kwargs):
        kwargs["position"] = event.data.queue.param.position
        return super()._from_alsa(event, **kwargs)

    def _to_alsa(self, event: _snd_seq_event_t, **kwargs):
        super()._to_alsa(event, **kwargs)
        event.data.queue.param.position = self.position
        return event


@_specialized_event_class(EventType.TUNE_REQUEST)
class TuneRequestEvent(Event):
    pass


@_specialized_event_class(EventType.RESET)
class ResetEvent(Event):
    pass


@_specialized_event_class(EventType.SENSING)
class ActiveSensingEvent(Event):
    pass


@_specialized_event_class(EventType.ECHO)
class EchoEvent(Event):
    def __repr__(self):
        return (f"<{self.__class__.__name__} data={self.raw_data!r}>")


@_specialized_event_class(EventType.ECHO)
class OSSEvent(Event):
    def __repr__(self):
        return (f"<{self.__class__.__name__} data={self.raw_data!r}>")


@_specialized_event_class(EventType.CLIENT_START)
class ClientStartEvent(AddressEventBase):
    pass


@_specialized_event_class(EventType.CLIENT_EXIT)
class ClientExitEvent(AddressEventBase):
    pass


@_specialized_event_class(EventType.CLIENT_CHANGE)
class ClientChangeEvent(AddressEventBase):
    pass


@_specialized_event_class(EventType.PORT_START)
class PortStartEvent(AddressEventBase):
    pass


@_specialized_event_class(EventType.PORT_EXIT)
class PortExitEvent(AddressEventBase):
    pass


@_specialized_event_class(EventType.PORT_CHANGE)
class PortChangeEvent(AddressEventBase):
    pass


@_specialized_event_class(EventType.PORT_SUBSCRIBED)
class PortSubscribedEvent(ConnectEventBase):
    pass


@_specialized_event_class(EventType.PORT_UNSUBSCRIBED)
class PortUnsubscribedEvent(ConnectEventBase):
    pass


@_specialized_event_class(EventType.SYSEX)
class SysExEvent(ExternalDataEventBase):
    pass


@_specialized_event_class(EventType.BOUNCE)
class BounceEvent(ExternalDataEventBase):
    pass


@_specialized_event_class(EventType.USR_VAR0)
class UserVar0Event(ExternalDataEventBase):
    pass


@_specialized_event_class(EventType.USR_VAR1)
class UserVar1Event(ExternalDataEventBase):
    pass


@_specialized_event_class(EventType.USR_VAR2)
class UserVar2Event(ExternalDataEventBase):
    pass


@_specialized_event_class(EventType.USR_VAR3)
class UserVar3Event(ExternalDataEventBase):
    pass


__all__ = [
        "RealTime",
        "EventType", "EventFlags", "Event", "MidiBytesEvent",
        "NoteEventBase",
        "NoteOnEvent", "NoteOffEvent"
        ]
