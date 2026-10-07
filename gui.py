"""Three-panel Tkinter GUI: Customers -> Projects -> Templates (generated documents)."""
import tkinter as tk
from tkinter import messagebox, ttk

import data_store as ds
import documents
from customer_dialog import show_customer_dialog
from project_dialog import show_project_dialog
from wizard import show_export_wizard


class App:
    def __init__(self, root: tk.Tk, conn):
        self.root = root
        self.conn = conn
        self.selected_customer_id = None
        self.selected_project_id = None

        self._build_layout()
        self.refresh_customers()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_layout(self):
        panes = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True)

        panes.add(self._build_customers_panel(panes), weight=1)
        panes.add(self._build_projects_panel(panes), weight=1)
        panes.add(self._build_templates_panel(panes), weight=1)

    def _build_customers_panel(self, parent):
        frame = ttk.Frame(parent)

        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X)
        ttk.Label(toolbar, text="Customers", font=("TkDefaultFont", 10, "bold")).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="Add", command=self.add_customer).pack(side=tk.RIGHT)
        ttk.Button(toolbar, text="Delete", command=self.delete_customer).pack(side=tk.RIGHT)
        ttk.Button(toolbar, text="Edit", command=self.edit_customer).pack(side=tk.RIGHT)

        search = ttk.Entry(frame)
        search.pack(fill=tk.X, padx=4, pady=2)
        search.bind("<KeyRelease>", lambda e: self.refresh_customers(search.get()))
        self.customer_search_var = search

        columns = ("name", "address", "phone")
        tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        tree.heading("name", text="Πελάτης")
        tree.heading("address", text="Διεύθυνση")
        tree.heading("phone", text="τηλ.")
        tree.pack(fill=tk.BOTH, expand=True)
        tree.bind("<<TreeviewSelect>>", self.on_select_customer)
        self.customers_tree = tree

        return frame

    def _build_projects_panel(self, parent):
        frame = ttk.Frame(parent)

        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X)
        ttk.Label(toolbar, text="Projects", font=("TkDefaultFont", 10, "bold")).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="Add", command=self.add_project).pack(side=tk.RIGHT)
        ttk.Button(toolbar, text="Delete", command=self.delete_project).pack(side=tk.RIGHT)
        ttk.Button(toolbar, text="Edit", command=self.edit_project).pack(side=tk.RIGHT)

        search = ttk.Entry(frame)
        search.pack(fill=tk.X, padx=4, pady=2)
        search.bind("<KeyRelease>", lambda e: self.refresh_projects(search.get()))
        self.project_search_var = search

        columns = ("application_no", "hkasp", "boiler_brand_model", "installation_address")
        tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        tree.heading("application_no", text="Αρ. Αίτησης")
        tree.heading("hkasp", text="ΗΚΑΣΠ")
        tree.heading("boiler_brand_model", text="Λέβητας")
        tree.heading("installation_address", text="Διεύθυνση Εγκατάστασης")
        tree.pack(fill=tk.BOTH, expand=True)
        tree.bind("<<TreeviewSelect>>", self.on_select_project)
        self.projects_tree = tree

        return frame

    def _build_templates_panel(self, parent):
        frame = ttk.Frame(parent)

        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X)
        ttk.Label(toolbar, text="Documents", font=("TkDefaultFont", 10, "bold")).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="Export Document...", command=self.export_document).pack(side=tk.RIGHT)

        columns = ("document_type", "visit_date", "generated_at", "output_pdf_path")
        tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        tree.heading("document_type", text="Document Type")
        tree.heading("visit_date", text="Visit Date")
        tree.heading("generated_at", text="Generated At")
        tree.heading("output_pdf_path", text="Output PDF")
        tree.pack(fill=tk.BOTH, expand=True)
        self.templates_tree = tree

        return frame

    # ------------------------------------------------------------------
    # Refresh / selection
    # ------------------------------------------------------------------

    def refresh_customers(self, search_text: str = ""):
        self.customers_tree.delete(*self.customers_tree.get_children())
        for c in ds.list_customers(self.conn):
            if search_text and search_text.lower() not in " ".join(
                filter(None, [c.name, c.address, c.phone])
            ).lower():
                continue
            self.customers_tree.insert("", tk.END, iid=str(c.id), values=(c.name, c.address or "", c.phone or ""))
        self.refresh_projects()

    def refresh_projects(self, search_text: str = ""):
        self.projects_tree.delete(*self.projects_tree.get_children())
        if self.selected_customer_id is not None:
            for p in ds.list_projects_for_customer(self.conn, self.selected_customer_id):
                if search_text and search_text.lower() not in " ".join(
                    filter(None, [p.application_no, p.hkasp, p.boiler_brand_model, p.installation_address])
                ).lower():
                    continue
                self.projects_tree.insert(
                    "", tk.END, iid=str(p.id),
                    values=(p.application_no or "", p.hkasp or "", p.boiler_brand_model or "", p.installation_address or ""),
                )
        self.refresh_templates()

    def refresh_templates(self):
        self.templates_tree.delete(*self.templates_tree.get_children())
        if self.selected_project_id is not None:
            for t in ds.list_templates_for_project(self.conn, self.selected_project_id):
                self.templates_tree.insert(
                    "", tk.END, iid=str(t.id),
                    values=(t.document_type, t.visit_date or "", t.generated_at or "", t.output_pdf_path or ""),
                )

    def on_select_customer(self, event=None):
        selection = self.customers_tree.selection()
        self.selected_customer_id = int(selection[0]) if selection else None
        self.selected_project_id = None
        self.refresh_projects()

    def on_select_project(self, event=None):
        selection = self.projects_tree.selection()
        self.selected_project_id = int(selection[0]) if selection else None
        self.refresh_templates()

    # ------------------------------------------------------------------
    # Customer CRUD
    # ------------------------------------------------------------------

    def add_customer(self):
        data = show_customer_dialog(self.root)
        if data:
            ds.create_customer(self.conn, **data)
            self.refresh_customers()

    def edit_customer(self):
        if self.selected_customer_id is None:
            messagebox.showinfo("Edit Customer", "Select a customer first.")
            return
        customer = ds.get_customer(self.conn, self.selected_customer_id)
        data = show_customer_dialog(self.root, customer)
        if data:
            ds.update_customer(self.conn, self.selected_customer_id, **data)
            self.refresh_customers()

    def delete_customer(self):
        if self.selected_customer_id is None:
            messagebox.showinfo("Delete Customer", "Select a customer first.")
            return
        project_count, template_count = ds.count_descendants(self.conn, self.selected_customer_id)
        warning = ""
        if project_count or template_count:
            warning = f"\n\nThis will also delete {project_count} project(s) and {template_count} document record(s)."
        if messagebox.askyesno("Delete Customer", f"Delete this customer?{warning}"):
            ds.delete_customer(self.conn, self.selected_customer_id)
            self.selected_customer_id = None
            self.refresh_customers()

    # ------------------------------------------------------------------
    # Project CRUD
    # ------------------------------------------------------------------

    def add_project(self):
        if self.selected_customer_id is None:
            messagebox.showinfo("Add Project", "Select a customer first.")
            return
        data = show_project_dialog(self.root)
        if data:
            ds.create_project(self.conn, self.selected_customer_id, **data)
            self.refresh_projects()

    def edit_project(self):
        if self.selected_project_id is None:
            messagebox.showinfo("Edit Project", "Select a project first.")
            return
        project = ds.get_project(self.conn, self.selected_project_id)
        data = show_project_dialog(self.root, project)
        if data:
            ds.update_project(self.conn, self.selected_project_id, **data)
            self.refresh_projects()

    def delete_project(self):
        if self.selected_project_id is None:
            messagebox.showinfo("Delete Project", "Select a project first.")
            return
        if messagebox.askyesno("Delete Project", "Delete this project and all its generated documents?"):
            ds.delete_project(self.conn, self.selected_project_id)
            self.selected_project_id = None
            self.refresh_projects()

    # ------------------------------------------------------------------
    # Document export (wired in a later milestone)
    # ------------------------------------------------------------------

    def export_document(self):
        if self.selected_project_id is None:
            messagebox.showinfo("Export Document", "Select a project first.")
            return

        answers = show_export_wizard(self.root)
        if not answers:
            return

        project = ds.get_project(self.conn, self.selected_project_id)
        customer = ds.get_customer(self.conn, project.customer_id)

        generated_paths = []
        for document_type in answers["document_types"]:
            template_id = ds.create_template(
                self.conn,
                project.id,
                document_type,
                visit_date=answers["visit_date"],
                test_start_time=answers["test_start_time"],
                test_end_time=answers["test_end_time"],
                pass_fail=answers["pass_fail"],
            )
            template_row = ds.get_template(self.conn, template_id)

            context = documents.build_context(customer, project, template_row)
            tex_source = documents.render_tex(document_type, context)
            output_path = documents.output_path_for(customer.name, project.id, document_type)

            try:
                documents.compile_pdf(tex_source, str(output_path))
            except RuntimeError as e:
                messagebox.showerror("Export Document", f"Failed to generate {document_type}:\n{e}")
                continue

            ds.set_template_output_path(self.conn, template_id, str(output_path))
            generated_paths.append(output_path)

        self.refresh_templates()
        if generated_paths:
            listing = "\n".join(str(p) for p in generated_paths)
            messagebox.showinfo("Export Document", f"Generated {len(generated_paths)} document(s):\n{listing}")
