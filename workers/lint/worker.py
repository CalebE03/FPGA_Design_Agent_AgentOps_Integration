"""
TODO: Implement lint worker.

Should consume lint tasks, run HDL lint (e.g., Verilator), and publish results.
"""


class LintWorker:
    def __init__(self, connection_params=None, stop_event=None):
        self.connection_params = connection_params
        self.stop_event = stop_event

    def run(self) -> None:
        raise NotImplementedError("LintWorker run() is TODO.")
