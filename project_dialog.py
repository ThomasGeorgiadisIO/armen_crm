"""Modal Add/Edit dialog for a Project (installation details)."""
import tkinter as tk
from tkinter import ttk

from data_store import PROJECT_FIELDS

LABELS = {
    "application_no": "Αρ. Αίτησης",
    "hkasp": "ΗΚΑΣΠ",
    "installation_address": "Διεύθυνση Εγκατάστασης",
    "access_street": "Οδός Προσπέλασης",
    "property_use": "Χρήση Ακινήτου",
    "gas_use": "Χρήση Αερίου",
    "boiler_brand_model": "Λέβητας (Μοντέλο)",
    "boiler_type": "Τύπος Λέβητα",
    "power_kw": "Ισχύς (kW)",
    "flow_m3h": "Παροχή (m³/h)",
    "technology": "Τεχνολογία",
    "meter_type": "Τύπος Μετρητή",
    "meter_position": "Θέση Μετρητή",
    "regulator_pressure_mbar": "Πίεση Ρυθμιστή (mbar)",
    "strength_test_design_pressure_mbar": "Πίεση Δοκιμής Αντοχής (mbar)",
    "tightness_test_design_pressure_mbar": "Πίεση Δοκιμής Στεγανότητας (mbar)",
}

ROWS_PER_COLUMN = 8


def show_project_dialog(parent, project=None) -> dict | None:
    """Blocks until the user confirms or cancels. Returns a dict of field values, or None if cancelled."""
    result = {}

    dialog = tk.Toplevel(parent)
    dialog.title("Edit Project" if project else "Add Project")
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(False, False)

    entries = {}
    for i, key in enumerate(PROJECT_FIELDS):
        col_group = i // ROWS_PER_COLUMN
        row = i % ROWS_PER_COLUMN
        label_col = col_group * 2
        entry_col = label_col + 1

        ttk.Label(dialog, text=LABELS[key]).grid(row=row, column=label_col, sticky="w", padx=8, pady=4)
        entry = ttk.Entry(dialog, width=30)
        entry.grid(row=row, column=entry_col, padx=8, pady=4)
        if project is not None:
            value = getattr(project, key, None)
            if value:
                entry.insert(0, value)
        entries[key] = entry

    def on_ok():
        for key in PROJECT_FIELDS:
            result[key] = entries[key].get().strip() or None
        dialog.destroy()

    def on_cancel():
        result.clear()
        dialog.destroy()

    button_row = ROWS_PER_COLUMN
    num_columns = (len(PROJECT_FIELDS) - 1) // ROWS_PER_COLUMN + 1
    buttons = ttk.Frame(dialog)
    buttons.grid(row=button_row, column=0, columnspan=num_columns * 2, pady=8)
    ttk.Button(buttons, text="OK", command=on_ok).pack(side=tk.LEFT, padx=4)
    ttk.Button(buttons, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=4)

    dialog.bind("<Return>", lambda e: on_ok())
    dialog.bind("<Escape>", lambda e: on_cancel())

    dialog.wait_window()
    return result or None
