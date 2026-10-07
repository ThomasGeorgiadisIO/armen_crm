"""Export wizard: pick which documents to generate + the per-generation
installation/boiler/meter details and test fields."""
import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from data_store import INSTALLATION_FIELDS

DOCUMENT_LABELS = {
    "compliance": "Πιστοποιητικό Τήρησης Κανονισμού",
    "strength_tightness_test": "Πιστοποιητικό Δοκιμής Αντοχής & Στεγανότητας",
    "maintenance_program": "Πρόγραμμα Λειτουργίας & Συντήρησης",
    "technical_report": "Τεχνική Έκθεση Αερίου",
}

INSTALLATION_LABELS = {
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

INSTALLATION_ROWS_PER_COLUMN = 8


def show_export_wizard(parent) -> dict | None:
    """Blocks until confirmed or cancelled. Returns:
        {"document_types": [...], "visit_date": "YYYY-MM-DD",
         "test_start_time": str, "test_end_time": str, "pass_fail": "pass"|"fail",
         <INSTALLATION_FIELDS...>: str}
    or None if cancelled."""
    result = {}

    dialog = tk.Toplevel(parent)
    dialog.title("Export Document")
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(False, False)

    ttk.Label(dialog, text="Επιλέξτε έγγραφα:", font=("TkDefaultFont", 9, "bold")).grid(
        row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 2)
    )

    doc_vars = {}
    for i, (key, label) in enumerate(DOCUMENT_LABELS.items()):
        var = tk.BooleanVar(value=False)
        ttk.Checkbutton(dialog, text=label, variable=var).grid(
            row=1 + i, column=0, columnspan=2, sticky="w", padx=16, pady=2
        )
        doc_vars[key] = var

    row = 1 + len(DOCUMENT_LABELS)
    ttk.Separator(dialog, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)
    row += 1

    ttk.Label(dialog, text="Στοιχεία εγκατάστασης:", font=("TkDefaultFont", 9, "bold")).grid(
        row=row, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 2)
    )
    row += 1

    install_frame = ttk.Frame(dialog)
    install_frame.grid(row=row, column=0, columnspan=2, padx=8, pady=2)
    row += 1

    install_entries = {}
    for i, key in enumerate(INSTALLATION_FIELDS):
        col_group = i // INSTALLATION_ROWS_PER_COLUMN
        frame_row = i % INSTALLATION_ROWS_PER_COLUMN
        label_col = col_group * 2
        entry_col = label_col + 1

        ttk.Label(install_frame, text=INSTALLATION_LABELS[key]).grid(
            row=frame_row, column=label_col, sticky="w", padx=4, pady=2
        )
        entry = ttk.Entry(install_frame, width=28)
        entry.grid(row=frame_row, column=entry_col, padx=4, pady=2)
        install_entries[key] = entry

    ttk.Separator(dialog, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)
    row += 1

    ttk.Label(dialog, text="Ημερομηνία επίσκεψης (visit date):").grid(row=row, column=0, sticky="w", padx=8, pady=4)
    visit_date_entry = ttk.Entry(dialog, width=20)
    visit_date_entry.insert(0, date.today().isoformat())
    visit_date_entry.grid(row=row, column=1, padx=8, pady=4)
    row += 1

    ttk.Label(dialog, text="Ώρα έναρξης δοκιμής (test start):").grid(row=row, column=0, sticky="w", padx=8, pady=4)
    test_start_entry = ttk.Entry(dialog, width=20)
    test_start_entry.grid(row=row, column=1, padx=8, pady=4)
    row += 1

    ttk.Label(dialog, text="Ώρα τέλους δοκιμής (test end):").grid(row=row, column=0, sticky="w", padx=8, pady=4)
    test_end_entry = ttk.Entry(dialog, width=20)
    test_end_entry.grid(row=row, column=1, padx=8, pady=4)
    row += 1

    ttk.Label(dialog, text="Έκβαση δοκιμής (pass/fail):").grid(row=row, column=0, sticky="w", padx=8, pady=4)
    pass_fail_var = tk.StringVar(value="pass")
    pass_fail_frame = ttk.Frame(dialog)
    pass_fail_frame.grid(row=row, column=1, sticky="w", padx=8, pady=4)
    ttk.Radiobutton(pass_fail_frame, text="Θετική", variable=pass_fail_var, value="pass").pack(side=tk.LEFT)
    ttk.Radiobutton(pass_fail_frame, text="Αρνητική", variable=pass_fail_var, value="fail").pack(side=tk.LEFT)
    row += 1

    def on_ok():
        selected = [key for key, var in doc_vars.items() if var.get()]
        if not selected:
            messagebox.showinfo("Export Document", "Select at least one document type.")
            return
        visit_date = visit_date_entry.get().strip()
        try:
            date.fromisoformat(visit_date)
        except ValueError:
            messagebox.showerror("Export Document", "Visit date must be in YYYY-MM-DD format.")
            return
        result["document_types"] = selected
        result["visit_date"] = visit_date
        result["test_start_time"] = test_start_entry.get().strip() or None
        result["test_end_time"] = test_end_entry.get().strip() or None
        result["pass_fail"] = pass_fail_var.get()
        for key in INSTALLATION_FIELDS:
            result[key] = install_entries[key].get().strip() or None
        dialog.destroy()

    def on_cancel():
        result.clear()
        dialog.destroy()

    buttons = ttk.Frame(dialog)
    buttons.grid(row=row, column=0, columnspan=2, pady=10)
    ttk.Button(buttons, text="Generate", command=on_ok).pack(side=tk.LEFT, padx=4)
    ttk.Button(buttons, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=4)

    dialog.bind("<Escape>", lambda e: on_cancel())

    dialog.wait_window()
    return result or None
