# app/background/controller.py

from .model import load_processes, kill_process


class BackgroundController:
    def __init__(self, view):
        self.view = view
        self._primed = False

    def refresh(self):
        # First call primes the Go CPU sampler
        if not self._primed:
            load_processes()   # warm-up, ignored
            self._primed = True

        rows = load_processes()  # real interval data
        self.view.render(rows)

    def kill(self, pid):
        kill_process(pid)
        self.refresh()
