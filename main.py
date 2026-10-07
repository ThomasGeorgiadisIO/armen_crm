"""Entry point for the Armen CRM desktop app."""
import tkinter as tk

import data_store as ds
from gui import App
from paths import app_dir


def main() -> None:
    db_path = app_dir() / "customers.db"
    conn = ds.connect(str(db_path))
    ds.init_db(conn)

    root = tk.Tk()
    root.title("Armen CRM")
    root.geometry("1100x600")
    App(root, conn)
    root.mainloop()

    conn.close()


if __name__ == "__main__":
    main()
