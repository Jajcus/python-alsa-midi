Usage
=====

.. currentmodule:: alsa_midi


Client and ports
----------------

To interface ALSA sequencer a client needs to be created. This is done by
creating a :class:`SequencerClient` object::

  from alsa_midi import SequencerClient

  client = SequencerClient("my client")

To receive or send MIDI events at least one port will be needed too::

  port = client.create_port("inout")

By default a generic bi-directional MIDI port with full subscription access is
created.  Additional arguments :meth:`SequencerClient.create_port()`
method can be used to change that::

  from alsa_midi import WRITE_PORT, PortType

  input_port = client.create_port("input",
                                  caps=WRITE_PORT,
                                  type=PortType.MIDI_GENERIC | PortType.MIDI_GM | PortType.SYNTHESIZER)

Note: use :data:`WRITE_PORT` (or :attr:`PortCaps.WRITE`) for creating input
ports (ports other clients can write to) and :data:`READ_PORT` (or
:attr:`PortCaps.READ`) for creating output ports (that other clients can read
from).


External port discovery
-----------------------

Client and port discovery can be done using
:meth:`SequencerClient.query_next_client()` and
:meth:`SequencerClient.query_next_port()` methods, which are Python interface to
the original the ALSA API calls.

There is also a convenience :meth:`SequencerClient.list_ports()` method
provided do get list of all available and relevant ports at once. The result is
also sorted in a way, that the first entry should be the most useful one
(according to some heuristics).

To get a list of available ports for MIDI output::

  out_ports = client.list_ports(output=True)

To get a list of hardware MIDI input ports::

  in_ports = client.list_ports(input=True, type=PortType.MIDI_GENERIC | PortType.HARDWARE)


Port subscriptions
------------------

ALSA sequencer keeps a list of subscriptions (connections) between ports.
Events can then be sent either to a specific port or to all connected ports,
the latter being often more useful.

Creating a connection of own port to some other port is as easy as calling the
:meth:`Port.connect_to()` or :meth:`Port.connect_from()` method::

  dest_port = client.list_ports(output=True)[0]
  port.connect_to(dest_port)

  source_port = client.list_ports(input=True)[0]
  input_port.connect_from(source_port)

Ports can be disconnected using :meth:`Port.disconnect_to()` or
:meth:`Port.disconnect_from()` method, appropriately.

Client can also manage connection between ports on other clients with
:meth:`SequencerClient.subscribe_port()` and
:meth:`SequencerClient.unsubscribe_port()` methods.


Event output
------------

Events, which are instances of :class:`Event` subclasses can be sent out using
the :meth:`SequencerClient.event_output` method. It does not send the events immediately,
unless the buffer gets full, so :meth:`SequencerClient.drain_output` has to be called afterwards::

  import time
  from alsa_midi import NoteOnEvent, NoteOffEvent

  for event in NoteOnEvent(note=60), NoteOnEvent(note=64), NoteOnEvent(note=67):
      client.event_output(event, port=port)
  client.drain_output()

  time.sleep(1)

  for event in NoteOffEvent(note=60), NoteOffEvent(note=64), NoteOffEvent(note=67):
      client.event_output(event, port=port)
  client.drain_output()


Event input
-----------

Incoming events can be received using the :meth:`SequencerClient.event_input()` method::

  while True:
      event = client.event_input()
      print(repr(event))


Queues
------

What makes ALSA sequencer a sequencer is precise control of event timing using event queues.
A queue is created using the :meth:`SequencerClient.create_queue()` method::

  queue = client.create_queue("my queue")

Then queue tempo should be set::

  beats_per_minute = 120
  ticks_per_quarter_note = 96

  queue.set_tempo(int(60.0 * 1000000 / beats_per_minute), ticks_per_quarter_note)

And the queue start command should be issued (will be executed after `SequencerClient.drain_output()`::

  queue.start()

The queue now might be used for placing output events in time::

   for event in NoteOnEvent(note=60, tick=0), NoteOffEvent(note=60, tick=96):
      client.event_output(event, port=port)
  client.drain_output()

Queues can also be used for setting timestamps (in MIDI ticks or seconds and nanoseconds) on incoming events::

  port = client.create_port("input", WRITE_PORT,
                            timestamping=True,
                            timestamp_real=True,
                            timestamp_queue=queue)

  while True:
      event = client.event_input()
      print("Time:", event.time, "Event:", repr(event))


Asynchronous Interface
----------------------

python-alsa-midi can work with :mod:`asyncio` event loop. For this task there is :class:`AsyncSequencerClient` class.
It is mostly the same as :class:`AsyncSequencerClient`, but
:meth:`~AsyncSequencerClient.event_input()`,
:meth:`~AsyncSequencerClient.drain_output()`,
:meth:`~AsyncSequencerClient.event_output()` and
:meth:`~AsyncSequencerClient.event_output_direct()` are coroutines here.

Example::

  import asyncio

  from alsa_midi import (AsyncSequencerClient, READ_PORT, WRITE_PORT,
                         NoteOnEvent, NoteOffEvent)

  async def play_chord(client):
      port = client.create_port("output", READ_PORT)
      port.connect_to(client.list_ports(output=True)[0])

      for event in NoteOnEvent(note=60), NoteOnEvent(note=64), NoteOnEvent(note=67):
          await client.event_output(event, port=port)
      await client.drain_output()

      await asyncio.sleep(1)

      for event in NoteOffEvent(note=60), NoteOffEvent(note=64), NoteOffEvent(note=67):
          await client.event_output(event, port=port)
      await client.drain_output()

  async def show_input(client):
      port = client.create_port("input", WRITE_PORT)
      port.connect_to(client.list_ports(input=True)[0])
      while True:
              event = await client.event_input()
              print(repr(event))

  client = AsyncSequencerClient("async example")
  loop = asyncio.get_event_loop()
  loop.run_until_complete(asyncio.gather(play_chord(client), show_input(client)))


Direct access to ALSA API
-------------------------

The raw ALSA `cffi`_ bindings are available through :data:`alsa_midi.alsa` and
:data:`alsa_midi.ffi` objects::

  from alsa_midi import alsa, ffi

  version = alsa.snd_asoundlib_version()
  print(ffi.string(version).decode())


Thread safety
-------------

:class:`SequencerClient`, :class:`AsyncSequencerClient` objects and
:class:`Port` and :class:`Queue` objects created through them should only be
used in a single thread and a single :mod:`asyncio` loop.

:class:`Event` objects do not contain any external resources, so the can be
safely passed around. Simultaneous access from different threads should still
be avoided.


MIDO back-end
-------------

The package also includes a `MIDO`_ back-end module. To use it set shell
variable $MIDO_BACKEND to 'alsa_midi.mido_backend' or programmatically::

  mido.set_backend('alsa_midi.mido_backend')


.. _cffi: http://cffi.readthedocs.org/
.. _MIDO: https://mido.readthedocs.io/
