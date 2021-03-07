# -*- coding: utf-8 -*-


class DummyMultiDict(dict):
    """dummy MultiDict class for testing
    """

    def getall(self, key):
        try:
            return self.__getitem__(key)
        except KeyError:
            return []


class DummyFileParam(object):
    """dummy FileParam object for testing
    """

    def __init__(self, filename=None, file=None):
        self.filename = filename
        self.file = file


class DummySession(object):
    """dummy session object for testing
    """

    def __init__(self):
        self.messages = []

    def flash(self, message):
        self.messages.append(message)
