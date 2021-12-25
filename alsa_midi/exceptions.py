"""Exceptions raised by the alsa-midi modules."""


class Error(Exception):
    """Base class for python-alsa-midi exceptions."""
    pass


class StateError(Error):
    """Raised when an object is used in invalid state, e.g. after close."""
    pass


class ALSAError(Error):
    """Raised when ALSA error occurs.

    :param message: Error message.
    :param errnum: Error code. Always a negative value, usually a negation of
                   an :mod:`errno` value.

    :ivar message: Error message.
    :ivar errnum: Error code. Always a negative value, usually a negation of an
                  :mod:`errno` value.
    """

    message: str
    errnum: int

    def __init__(self, message, errnum):
        Error.__init__(self, message, errnum)
        self.message = message
        self.errnum = errnum

    def __str__(self):
        return self.message


__all__ = ["Error", "StateError", "ALSAError"]
