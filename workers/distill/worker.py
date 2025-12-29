"""
TODO: Implement distillation worker.

Should distill simulation logs/waveforms and emit structured datasets.
"""


class DistillWorker:
    def __init__(self, connection_params=None, stop_event=None):
        self.connection_params = connection_params
        self.stop_event = stop_event

    def run(self) -> None:
        raise NotImplementedError("DistillWorker run() is TODO.")
