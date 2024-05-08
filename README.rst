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

* Python 3.8 – 3.12 compatibility

* Both synchronous (blocking) and asynchronous (asyncio) I/O

* Only Python code, no need to compile a binary module. Requires `cffi`_, though.

* `MIDO`_ backend provided

Installation
------------

This package requires ALSA library to be installed (``libasound.so.2`` –
'libasound2' package on Debian-like systems). On a typical Linux system it is
probably already installed for some other audio or MIDI software.

python-alsa-midi package may be installed with pip::

  python3 -m pip install alsa-midi

This should normally install a binary wheel compiled on a compatible system or
pure-python wheel working without compilation.

If no compatible wheel is found build from source package will be triggered,
which will also require ALSA library development files (libasound2-dev).

To force installing from source (and compiling the binary extension) use::

  python3 -m pip install --no-binary=alsa-midi alsa-midi

To force installing from source without compiling the extension::

  PY_ALSA_MIDI_NO_COMPILE=1 python3 -m pip install --no-binary=alsa-midi alsa-midi

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

Using with MIDO
---------------

python-alsa-midi can be used as a `MIDO`_ back-end too::

  export MIDO_BACKEND=alsa_midi.MIDO_BACKEND
  mido/examples/midifiles/play_midi_file.py file.mid


.. _cffi: http://cffi.readthedocs.org/
.. _MIDO: https://mido.readthedocs.io/
