python-alsa-midi – Python interface to ALSA MIDI Sequencer
==========================================================

This project provides Python interface to ALSA sequencer API.

Features
--------

* Pythonic API to most of the ALSA sequencer functionality
* Python 3.7 – 3.10 compatibility
* Both synchronous (blocking) and asynchronous (asyncio) I/O
* Only Python code, no need to compile a binary module. Requires `cffi`_, though.

Usage
-----

.. currentmodule:: alsa_midi

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

.. _cffi: http://cffi.readthedocs.org/
