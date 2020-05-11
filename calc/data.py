class SharedData:
    def __init__(self):
        self._results = dict()                  # results of calculated expressions, key - pid, value - result
        self._calculated_expressions = dict()   # cache of soon calculated expressions, key - expression, value - pid
        self._processing = set()                # pid's now running
        self._processing_expressions = dict()   # dict of processing expressions, key - expression, value - pid
        self._errors = dict()                   # dict of errors, key - pid, value - err_text
        self._pid_counter = 0
        self._invalid_expressions = set()      #cache of invalid expressions, key - expression

    def _del_from_processing(self, pid, expression):
        if pid in self._processing:
            self._processing.remove(pid)
            if expression in self._processing_expressions:
                del self._processing_expressions[expression]

    def add_result(self, res, pid, expression):
        self._calculated_expressions[expression] = pid
        self._results[pid] = res
        self._del_from_processing(pid, expression)
        print('\nend process pid=%s res=%s expression = %s\n' % (pid, res, expression))

    def add_processing(self, expression):
        pid = self._pid_counter
        self._processing.add(pid)
        self._processing_expressions[expression] = pid
        self._pid_counter += 1
        print('\nstart process pid=%s expression=%s\n' % (pid, expression))
        return pid

    def add_error(self, err_text, pid, expression):
        self._errors[pid] = 'ERROR: %s in calculating expression %s; task with pid = %s failed\n' % (err_text, expression, pid)
        self._del_from_processing(pid, expression)
        if not expression in self._invalid_expressions:
            self._invalid_expressions.add(expression)

    def is_invalid(self, expression):
        return expression in self._invalid_expressions

    def get_cached(self, expression):
        if expression in self._calculated_expressions:
            if self._calculated_expressions[expression] in self._results:
                return self._results[self._calculated_expressions[expression]]
        return None

    def get_processing(self, expression):
        if expression in self._processing_expressions:
            return self._processing_expressions[expression]
        return None

    def get_result(self, pid):
        if pid in self._results:
            return self._results[pid]
        return None

    def get_error(self, pid):
        if pid in self._errors:
            return self._errors[pid]
        return None

    def is_processing(self, pid):
        return pid in self._processing