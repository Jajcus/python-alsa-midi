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
:meth:`Port.connect_to()` or :meth:`Port.connect_from()` method:

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

  for event in NoteOnEvent(note=60), NoteOnEvent(note=64), NoteOnEvent(node=67):
      client.event_output(event, port=port)
  client.drain_output()

  time.sleep(1)

  for event in NoteOffEvent(note=60), NoteOffEvent(note=64), NoteOffEvent(node=67):
      client.event_output(event, port=port)
  client.drain_output()


Event input
-----------

Incoming events can be received using the :meth:`SequencerClient.event_input` method::

  while True:
      event = client.event_input()
      print(repr(event))

Queues
------

What makes ALSA sequencer a sequencer is precise control of event timing using event queues.
A queue is created using the :meth:`SequencerClient.create_queue()` method::

  queue = client.create_queue("my queue")


