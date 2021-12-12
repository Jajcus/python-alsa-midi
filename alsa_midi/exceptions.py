"""Exceptions raised by the alsa-midi modules."""


class SequencerError(Exception):
    pass


class SequencerStateError(SequencerError):
    pass


class SequencerALSAError(SequencerError):
    def __init__(self, message, errnum):
        SequencerError.__init__(self, message, errnum)
        self.message = message
        self.errnum = errnum

    def __str__(self):
        return self.message


__all__ = ["SequencerError", "SequencerStateError", "SequencerALSAError"]
