STATUS_SUCCESS = "completed success"
STATUS_FAILURE = "completed failure"
STATUS_RUNNING = "running"


class BaseResult:
    """
    Keeps track of results.

    Subclasses should implement _result_name and _addl_str.
    """
    def __init__(self):
        self.success = True
        self.started = None
        self.ended = None
        self.infos = []
        self.warnings = []
        self.errors = []

    def __nonzero__(self):
        return 1 if self.success else 0

    @property
    def _result_name(self):
        """
        Returns name of the result for including in __str__.

        For example, "Harvest"
        """
        return ""

    def _addl_str(self):
        """
        Additional text to add to __str__.
        """
        return ""

    def __str__(self):
        str_text = "{} response is {}.".format(self._result_name, self.success)
        if self.started:
            str_text += " Started: {}".format(self.started)
        if self.ended:
            str_text += " Ended: {}".format(self.ended)
        str_text += self._str_messages(self.infos, "Informational")
        str_text += self._str_messages(self.warnings, "Warning")
        str_text += self._str_messages(self.errors, "Error")
        str_text += self._addl_str()
        return str_text

    @staticmethod
    def _str_messages(messages, name):
        msg_str = ""
        if messages:
            msg_str += " {} messages are:".format(name)

        for (i, msg) in enumerate(messages, start=1):
            msg_str += "({}) [{}] {}".format(i, msg.code, msg.message)

        return msg_str


class Msg:
    """
    An informational, warning, or error message to be included in a result.
    """
    def __init__(self, code, message):
        assert code
        assert message
        self.code = code
        self.message = message

    def to_map(self):
        return {
            "code": self.code,
            "message": self.message
        }
