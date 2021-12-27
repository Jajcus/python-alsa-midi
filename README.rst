python-alsa-midi – Python interface to ALSA MIDI Sequencer
==========================================================

This project provides Python interface to ALSA sequencer API.

Features
--------

* Pythonic API to most of the ALSA sequencer functionality

* Access to ALSA sequencer features not available when using other ('portable')
  Python MIDI libraries:

  * Precise timestamping of messages sent and received
  * Port connection management, including connection between ports on different
    clients
  * Access to non-MIDI events, like announcements about new clients, ports and
    connections

* Python 3.7 – 3.10 compatibility

* Both synchronous (blocking) and asynchronous (asyncio) I/O

* Only Python code, no need to compile a binary module. Requires `cffi`_, though.

Installation
------------

Usually the package would be installed with pip::

  python3 -m pip install alsa-midi

That may trigger building of the binary module with the cffi bindings, that may
fail if a compiler or ALSA headers are not available. This might be prevented
by setting the ``PY_ALSA_MIDI_NO_COMPILE`` environment variable::

  PY_ALSA_MIDI_NO_COMPILE=1 python3 -m pip install --no-binary :all: alsa-midi

Alternatively one can just add the source directory (as checked out from
https://github.com/Jajcus/python-alsa-midi.git) to `$PYTHONPATH` and use the
packages directly, with no compilation.

Usage
-----

Detailed documentation is available at https://python-alsa-midi.readthedocs.io/

Simple example::

  import time
  from alsa_midi import SequencerClient, READ_PORT, NoteOnEvent, NoteOffEvent

  client = SequencerClient("my client")
  port = client.create_port("output", caps=READ_PORT)
  dest_port = client.list_ports(output=True)[0]
  port.connect_to(dest_port)
  event1 = NoteOnEvent(note=60, velocity=64, channel=0)
  client.event_output(event1)
  client.drain_output()
  time.sleep(1)
  event2 = NoteOffEvent(note=60, channel=0)
  client.event_output(event2)
  client.drain_output()


.. _cffi: http://cffi.readthedocs.org/
