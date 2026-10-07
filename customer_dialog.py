"""Modal Add/Edit dialog for a Customer."""
import tkinter as tk
from tkinter import ttk

FIELDS = [
    ("name", "Πελάτης (Name)"),
    ("address", "Διεύθυνση (Address)"),
    ("phone", "τηλ. (Phone)"),
]


def show_customer_dialog(parent, customer=None) -> dict | None:
    """Blocks until the user confirms or cancels. Returns a dict of field values, or None if cancelled."""
    result = {}

    dialog = tk.Toplevel(parent)
    dialog.title("Edit Customer" if customer else "Add Customer")
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(False, False)

    entries = {}
    for row, (key, label) in enumerate(FIELDS):
        ttk.Label(dialog, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=4)
        entry = ttk.Entry(dialog, width=40)
        entry.grid(row=row, column=1, padx=8, pady=4)
        if customer is not None:
            value = getattr(customer, key, None)
            if value:
                entry.insert(0, value)
        entries[key] = entry

    def on_ok():
        name = entries["name"].get().strip()
        if not name:
            entries["name"].focus_set()
            return
        for key, _ in FIELDS:
            result[key] = entries[key].get().strip() or None
        dialog.destroy()

    def on_cancel():
        result.clear()
        dialog.destroy()

    button_row = len(FIELDS)
    buttons = ttk.Frame(dialog)
    buttons.grid(row=button_row, column=0, columnspan=2, pady=8)
    ttk.Button(buttons, text="OK", command=on_ok).pack(side=tk.LEFT, padx=4)
    ttk.Button(buttons, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=4)

    dialog.bind("<Return>", lambda e: on_ok())
    dialog.bind("<Escape>", lambda e: on_cancel())
    entries["name"].focus_set()

    dialog.wait_window()
    return result or None
