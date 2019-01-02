
class Scheduler:

    def __init__(self, analyses, runner):
        self._analyses = analyses
        self._runner = runner

        self._analyses.add_options_changed_listener(self._send_next)
        self._runner.add_slot_available_listener(self._send_next)

    def _send_next(self, analysis=None):

        print('_send_next', analysis)

        # if the analysis already running, send to the same slot
        if analysis is not None:
            for i in range(self._runner.n_slots):
                if self._runner[i].analysis is analysis:
                    print('initing', analysis.id, 'on', i)
                    self._runner[i].send(analysis, False)
                    break

        for analysis in self._analyses.needs_init:
            for i in range(0, self._runner.n_slots):
                if self._runner[i].analysis is None:
                    print('needs initing', analysis.id, 'on', i)
                    self._runner[i].send(analysis, False)
                    break

        for analysis in self._analyses.needs_op:
            for i in range(1, self._runner.n_slots):
                if self._runner[i].analysis is None:
                    print('running', analysis.id, 'on', i)
                    self._runner[i].send(analysis, True)
                    break

        for analysis in self._analyses.needs_run:
            for i in range(1, self._runner.n_slots):
                if self._runner[i].analysis is None:
                    print('running', analysis.id, 'on', i, 'because', analysis.status)
                    self._runner[i].send(analysis, True)
                    break
