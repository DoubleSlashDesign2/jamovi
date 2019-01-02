

from nanomsg import Socket
from nanomsg import PAIR

from collections import OrderedDict

class RemoteQueue:

    def __init__(self, analyses, path):
        self._analyses = analyses
        self._path = path
        self._waiting = OrderedDict()  # use as an ordered set
        self._n_in_progress = 0
        self._max_n_in_progress = 12

        self._socket = Socket(PAIR)
        self._socket._set_recv_timeout(500)
        self._socket.connect(self._path)

        self._analyses.add_options_changed_listener(self._send_next)

    def _send_next(self, analysis=None):
        if self._n_in_progress < self._max_n_in_progress:
            pass
        else:
            self._waiting[analysis] = None

    def _receive(self):

        self._n_in_progress -= 1
        self._next_next()
