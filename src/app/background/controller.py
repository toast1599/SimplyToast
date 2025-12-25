# app/background/controller.py

from .model import load_processes, kill_process

class BackgroundController:
    def __init__(self, view):
        self.view = view
        self._rows_by_pid = {}

    def refresh(self):
        rows = load_processes()
        self.view.render(rows)

    def kill(self, pid):
        kill_process(pid)
        self.refresh()
