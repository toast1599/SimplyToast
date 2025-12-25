# src/app/startup/controller.py

from .model import load_entries, toggle_entry, delete_entry
from .impact import compute_impacts, impact_level, impact_sort_key


class StartupController:
    def __init__(self, view):
        self.view = view
        self.entries = []

    def refresh(self):
        self.entries = load_entries()

        impacts = compute_impacts(self.entries)
        max_impact = max(impacts.values(), default=0.0)

        rows = []
        for entry in self.entries:
            impact = impacts.get(entry, 0.0)
            label, color = impact_level(impact, max_impact)

            rows.append(
                {
                    "entry": entry,
                    "impact": impact,
                    "impact_label": label,
                    "impact_color": color,
                }
            )

        rows.sort(
            key=lambda r: impact_sort_key(r["impact"], max_impact)
        )

        self.view.render(rows)

    def toggle(self, entry, enabled: bool):
        toggle_entry(entry, enabled)
        self.refresh()

    def delete(self, entry):
        delete_entry(entry)
        self.refresh()
