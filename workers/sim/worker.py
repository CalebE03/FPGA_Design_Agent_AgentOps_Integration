"""
TODO: Implement simulation worker.

Should consume simulation tasks, run HDL sims, and publish results/coverage.
"""


class SimulationWorker:
    def __init__(self, connection_params=None, stop_event=None):
        self.connection_params = connection_params
        self.stop_event = stop_event

    def run(self) -> None:
        raise NotImplementedError("SimulationWorker run() is TODO.")
