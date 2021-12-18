"""Exceptions raised by the alsa-midi modules."""


class Error(Exception):
    pass


class StateError(Error):
    pass


class ALSAError(Error):
    def __init__(self, message, errnum):
        Error.__init__(self, message, errnum)
        self.message = message
        self.errnum = errnum

    def __str__(self):
        return self.message


__all__ = ["Error", "StateError", "ALSAError"]
