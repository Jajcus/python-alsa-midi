"""python-alsa-midi back-end for `MIDO`_.

To use this backend copy call this from a MIDO application::

    mido.set_backend('alsa_midi.mido_backend')

or set shell variable $MIDO_BACKEND to 'alsa_midi.mido_backend'

.. _MIDO: https://mido.readthedocs.io/
"""

import logging
import queue
import sys
import threading
from typing import Any, Callable, List, MutableMapping, Optional
from weakref import WeakValueDictionary

from mido.messages import Message
from mido.parser import Parser
from mido.ports import BaseInput, BaseOutput

import alsa_midi

logger = logging.getLogger("alsa_midi.mido_backend")


class _Client:
    instance: Optional['_Client'] = None

    client: alsa_midi.SequencerClient
    in_thread: threading.Thread
    ports: MutableMapping[int, 'PortCommon']
    closing: bool

    def __init__(self):
        name = f"{sys.argv[0]!r} MIDO"
        self.ports = WeakValueDictionary()
        self.client = alsa_midi.SequencerClient(name)
        self.closing = False
        self.in_thread = threading.Thread(name="ALSA seq input",
                                          target=self._input_loop,
                                          daemon=True)
        self.in_thread.start()

    def __del__(self):
        self.close()

    def close(self):
        self.closing = True
        self.client.close()

    @classmethod
    def get_instance(cls):
        if cls.instance is not None:
            return cls.instance
        cls.instance = cls()
        return cls.instance

    def get_devices(self, *args, **kwargs):
        _ = args, kwargs
        client = self.client
        devices = []
        for port in client.list_ports():
            devices.append({
                'name': f"{port.client_name}:{port.name} {port.client_id}:{port.port_id}",
                'is_input': port.capability & alsa_midi.PortCaps.READ,
                'is_output': port.capability & alsa_midi.PortCaps.WRITE,
            })
        return devices

    def _input_loop(self):
        try:
            while not self.closing:
                event = self.client.event_input(timeout=1,
                                                prefer_bytes=True)
                if event is None:
                    continue
                if not isinstance(event, alsa_midi.MidiBytesEvent):
                    continue
                assert event.dest is not None
                mido_port = self.ports.get(event.dest.port_id)
                if mido_port is None or not mido_port._for_input:
                    continue
                mido_port._handle_input_bytes(event.midi_bytes)
        except Exception:
            logger.error("Error in alsa_midi.mido_backend input loop:", exc_info=True)


def get_devices(*args, **kwargs):
    client = _Client.get_instance()
    return client.get_devices(*args, **kwargs)


def _find_port(ports: List[alsa_midi.PortInfo], name: str) -> alsa_midi.PortInfo:
    try:
        addr = alsa_midi.Address(name)
    except ValueError:
        addr = None

    if addr is not None:
        # name is ALSA sequencer address, exact match
        for port in ports:
            if addr == alsa_midi.Address(port):
                return port
        else:
            raise IOError(f"unknown port {name!r}")

    # check for exact match with name from get_devices()
    for port in ports:
        mido_name = f"{port.client_name}:{port.name} {port.client_id}:{port.port_id}"
        if name == mido_name:
            return port

    # check for exact match for client_name:port_name
    for port in ports:
        check_name = f"{port.client_name}:{port.name}"
        if name == check_name:
            return port

    # check for exact match for client_name
    for port in ports:
        if name == port.client_name:
            return port

    # check for exact match for port_name
    for port in ports:
        if name == port.name:
            return port

    raise IOError(f"unknown port {name!r}")


class PortCommon(object):
    _last_num = 0
    _name_prefix = "inout"
    _caps = alsa_midi.PortCaps.READ | alsa_midi.PortCaps.WRITE
    _type = alsa_midi.PortType.MIDI_GENERIC
    _for_input = False
    _for_output = False

    _parser: Parser
    _virtual: bool = False
    _callback: Optional[Callable[[Message], Any]] = None

    _port: Optional[alsa_midi.Port] = None
    _dest_port: Optional[alsa_midi.PortInfo] = None
    name: str

    @classmethod
    def _generate_alsa_port_name(cls) -> str:
        num = cls._last_num + 1
        cls._last_num = num
        return f"{cls._name_prefix}{num}"

    def _open(self, virtual=False, **kwargs):

        self._queue = queue.Queue()
        self._callback = kwargs.get("callback")

        client = _Client.get_instance()

        port_caps = kwargs.get("alsa_capability", self._caps)
        port_type = kwargs.get("alsa_type", self._type)

        if virtual:
            if self._caps & alsa_midi.PortCaps.READ:
                self._caps |= alsa_midi.PortCaps.SUBS_READ
            if self._caps & alsa_midi.PortCaps.WRITE:
                self._caps |= alsa_midi.PortCaps.SUBS_WRITE
            if self.name is None:
                name = self._generate_alsa_port_name()
            else:
                name = self.name
            self._virtual = True
        else:
            name = self._generate_alsa_port_name()

        if virtual:
            dest_port = None
        else:
            ports = client.client.list_ports(input=self._for_input, output=self._for_output)

            if not ports:
                raise IOError('no ports available')

            if self.name is None:
                dest_port = ports[0]
            else:
                dest_port = _find_port(ports, self.name)

        self._port = client.client.create_port(name, caps=port_caps, type=port_type)

        if dest_port is not None:
            if self._for_output:
                self._port.connect_to(dest_port)
            if self._for_input:
                self._port.connect_from(dest_port)

        self._dest_port = dest_port

        api = 'seq'
        self._device_type = 'AlsaMidi/{}'.format(api)
        if virtual:
            self._device_type = 'virtual {}'.format(self._device_type)

        client.ports[self._port.port_id] = self

    def _handle_input_bytes(self, midi_bytes):
        if self._callback:
            self._parser.feed(midi_bytes)
            for message in self._parser:
                self._callback(message)
        else:
            self._queue.put(midi_bytes)

    def _close(self):
        port = self._port
        if port is not None:
            self._port = None
            port.close()

    @property
    def callback(self):
        return self._callback

    @callback.setter
    def callback(self, func):
        self._callback = func


class Input(PortCommon, BaseInput):
    _last_num = 0
    _name_prefix = "in"
    _for_input = True
    _caps = alsa_midi.PortCaps.WRITE

    def _receive(self, block=True):
        data = self._queue.get(block)
        self._parser.feed(data)


class Output(PortCommon, BaseOutput):
    _last_num = 0
    _name_prefix = "out"
    _for_output = True
    _caps = alsa_midi.PortCaps.READ

    def _send(self, message):
        client = _Client.get_instance().client
        event = alsa_midi.MidiBytesEvent(message.bytes())
        client.event_output(event,
                            port=self._port,
                            dest=self._dest_port)
        client.drain_output()
