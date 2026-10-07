"""Modal Add/Edit dialog for a Project (just a name -- installation details
are entered per-document-generation via the export wizard)."""
import tkinter as tk
from tkinter import ttk


def show_project_dialog(parent, project=None) -> dict | None:
    """Blocks until the user confirms or cancels. Returns {"name": str}, or None if cancelled."""
    result = {}

    dialog = tk.Toplevel(parent)
    dialog.title("Edit Project" if project else "Add Project")
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(False, False)

    ttk.Label(dialog, text="Όνομα Έργου").grid(row=0, column=0, sticky="w", padx=8, pady=4)
    entry = ttk.Entry(dialog, width=30)
    entry.grid(row=0, column=1, padx=8, pady=4)
    if project is not None and project.name:
        entry.insert(0, project.name)
    entry.focus_set()

    def on_ok():
        name = entry.get().strip()
        if not name:
            return
        result["name"] = name
        dialog.destroy()

    def on_cancel():
        result.clear()
        dialog.destroy()

    buttons = ttk.Frame(dialog)
    buttons.grid(row=1, column=0, columnspan=2, pady=8)
    ttk.Button(buttons, text="OK", command=on_ok).pack(side=tk.LEFT, padx=4)
    ttk.Button(buttons, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=4)

    dialog.bind("<Return>", lambda e: on_ok())
    dialog.bind("<Escape>", lambda e: on_cancel())

    dialog.wait_window()
    return result or None
