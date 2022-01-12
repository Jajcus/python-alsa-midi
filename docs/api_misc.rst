Miscelanous objects
===================

.. py:currentmodule:: alsa_midi

.. autoclass:: Address

.. autoclass:: RealTime

.. autoclass:: ClientInfo

.. autoclass:: SystemInfo

.. autoclass:: ClientPool

.. py:data:: alsa

   Provides direct access to ALSA library functions (snd_seq_*) as `cffi`_ bindings.

.. py:data:: ffi

   `FFI object`_ for use with the :data:`alsa` bindings.

.. py:currentmodule:: alsa_midi.client

.. autoclass:: StreamOpenType
   :members:
   :undoc-members:

.. autoclass:: OpenMode
   :members:
   :undoc-members:

.. autoclass:: ClientType
   :members:
   :undoc-members:

.. autoclass:: SequencerType
   :members:
   :undoc-members:

.. autoclass:: SequencerClientBase
   :members:

.. _cffi: https://cffi.readthedocs.io/en/stable/
.. _FFI object: https://cffi.readthedocs.io/en/stable/ref.html#ffi-interface
