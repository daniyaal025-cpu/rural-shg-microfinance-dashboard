from __future__ import annotations

"""Rural SHG & Microfinance Tracker

A single-file Tkinter + SQLite CRUD application. Run with Python 3.9+:
    python shg_microfinance_dashboard.py

In Jupyter/Colab, run the file in a local desktop Python environment with a
working Tk display. A GUI cannot be rendered inside a hosted notebook kernel;
this script detects display startup failures and reports a helpful message.
"""

import re
import sqlite3
import tkinter as tk
from contextlib import closing
from datetime import date
from pathlib import Path
from tkinter import messagebox, ttk

APP_TITLE = "Rural SHG & Microfinance Tracker"
DB_PATH = Path(__file__).resolve().with_name("shg_microfinance.db")
ENTRY_TYPES = (
    "Monthly Savings (₹)",
    "Loan Disbursed (₹)",
    "Repayment (₹)",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS village_clusters (
    cluster_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    officer_email TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS self_help_groups (
    shg_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id INTEGER NOT NULL,
    shg_name TEXT NOT NULL,
    formation_date TEXT NOT NULL,
    FOREIGN KEY (cluster_id) REFERENCES village_clusters(cluster_id)
        ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS savings_loan_entries (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    shg_id INTEGER NOT NULL,
    entry_type TEXT NOT NULL,
    entry_amount REAL NOT NULL CHECK (entry_amount >= 0),
    FOREIGN KEY (shg_id) REFERENCES self_help_groups(shg_id)
        ON DELETE CASCADE
);
"""

SEED = (
    ("Sundarpur Cluster", "bdo.sundarpur@example.org",
     "Shakti Mahila Sangathan", "2023-04-12", "Monthly Savings (₹)", 1200.00),
    ("Sundarpur Cluster", "bdo.sundarpur@example.org",
     "Kisan Vikas Group", "2022-11-05", "Loan Disbursed (₹)", 25000.00),
    ("Rampur Cluster", "bdo.rampur@example.org",
     "Pragati Self Help Group", "2024-01-20", "Repayment (₹)", 3500.00),
)


def connect_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open a connection with foreign key enforcement enabled."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database(db_path: Path = DB_PATH) -> None:
    """Create tables and seed examples only when the database has no records."""
    with closing(connect_db(db_path)) as conn:
        with conn:
            conn.executescript(SCHEMA)
            counts = conn.execute(
                "SELECT (SELECT COUNT(*) FROM village_clusters) + "
                "(SELECT COUNT(*) FROM self_help_groups) + "
                "(SELECT COUNT(*) FROM savings_loan_entries)"
            ).fetchone()[0]
            if counts == 0:
                cluster_ids: dict[str, int] = {}
                for cluster_name, email, shg_name, formed, kind, amount in SEED:
                    key = cluster_name.casefold()
                    if key not in cluster_ids:
                        cur = conn.execute(
                            "INSERT INTO village_clusters(cluster_name, officer_email) VALUES (?, ?)",
                            (cluster_name, email),
                        )
                        cluster_ids[key] = cur.lastrowid
                    cur = conn.execute(
                        "INSERT INTO self_help_groups(cluster_id, shg_name, formation_date) VALUES (?, ?, ?)",
                        (cluster_ids[key], shg_name, formed),
                    )
                    conn.execute(
                        "INSERT INTO savings_loan_entries(shg_id, entry_type, entry_amount) VALUES (?, ?, ?)",
                        (cur.lastrowid, kind, amount),
                    )


class SHGDashboard:
    def __init__(self, root: tk.Tk, db_path: Path = DB_PATH) -> None:
        self.root = root
        self.db_path = db_path
        self.root.title(APP_TITLE)
        self.root.geometry("1280x850")
        self.root.minsize(900, 650)
        self.root.configure(bg="#eef3ef")
        self._style()
        self._build_ui()
        self.refresh_all()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#eef3ef")
        style.configure("Card.TLabelframe", background="#ffffff", padding=15, borderwidth=1, relief="solid")
        style.configure("Card.TLabelframe.Label", background="#ffffff", foreground="#234b3e", font=("Segoe UI", 10, "bold"))
        style.configure("TLabel", background="#eef3ef", foreground="#20352c", font=("Segoe UI", 9))
        style.configure("Card.TLabel", background="#ffffff", foreground="#32463d")
        style.configure("Title.TLabel", background="#173d31", foreground="#ffffff", font=("Segoe UI", 20, "bold"))
        style.configure("HeroHint.TLabel", background="#173d31", foreground="#c7ded1", font=("Segoe UI", 10))
        style.configure("Hint.TLabel", background="#eef3ef", foreground="#62766c", font=("Segoe UI", 9))
        style.configure("Accent.TButton", padding=(14, 9), background="#287653", foreground="white", font=("Segoe UI", 9, "bold"), borderwidth=0)
        style.map("Accent.TButton", background=[("active", "#1e6042"), ("disabled", "#9ab8a7")])
        style.configure("Danger.TButton", padding=(12, 8), background="#fff1ed", foreground="#a33f2d", font=("Segoe UI", 9, "bold"), borderwidth=1)
        style.map("Danger.TButton", background=[("active", "#ffe1d9")])
        style.configure("Treeview", rowheight=30, font=("Segoe UI", 9), background="#ffffff", fieldbackground="#ffffff", foreground="#253a31", borderwidth=0)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#e4eee7", foreground="#234b3e", padding=(8, 8), relief="flat")
        style.map("Treeview", background=[("selected", "#d8ebe0")], foreground=[("selected", "#173d31")])
        style.configure("TNotebook", background="#eef3ef", borderwidth=0, tabmargins=(0, 4, 0, 0))
        style.configure("TNotebook.Tab", padding=(16, 10), background="#e2eae4", foreground="#4e665b", font=("Segoe UI", 9, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "#ffffff")], foreground=[("selected", "#1d6345")])
        style.configure("TCombobox", padding=5)
        style.configure("TEntry", padding=6)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=(20, 18))
        outer.pack(fill="both", expand=True)
        hero = tk.Frame(outer, bg="#173d31", padx=22, pady=18)
        hero.pack(fill="x", pady=(0, 15))
        ttk.Label(hero, text="RURAL FINANCE  /  OVERVIEW", style="HeroHint.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(hero, text=APP_TITLE, style="Title.TLabel").pack(anchor="w")
        ttk.Label(hero, text="A clear picture of community groups, savings, and lending activity", style="HeroHint.TLabel").pack(anchor="w", pady=(4, 0))
        tk.Label(hero, text=date.today().strftime("%d %b %Y"), bg="#245544", fg="#e4f1e9", font=("Segoe UI", 9, "bold"), padx=12, pady=7).place(relx=1.0, rely=0.0, anchor="ne")

        self.metric_values = {}
        metrics = ttk.Frame(outer)
        metrics.pack(fill="x", pady=(0, 15))
        for key, caption, accent in (("clusters", "VILLAGE CLUSTERS", "#3a7e5b"), ("groups", "SELF-HELP GROUPS", "#4b79a1"), ("entries", "LEDGER ENTRIES", "#b27a35"), ("total", "TOTAL RECORDED (₹)", "#805e9b")):
            card = tk.Frame(metrics, bg="white", highlightbackground="#dce6df", highlightthickness=1, padx=14, pady=11)
            card.pack(side="left", fill="x", expand=True, padx=(0, 9))
            tk.Frame(card, bg=accent, width=4, height=39).pack(side="left", fill="y", padx=(0, 12))
            text_box = tk.Frame(card, bg="white")
            text_box.pack(side="left", fill="x", expand=True)
            tk.Label(text_box, text=caption, bg="white", fg="#718278", font=("Segoe UI", 8, "bold")).pack(anchor="w")
            value = tk.Label(text_box, text="—", bg="white", fg="#203d31", font=("Segoe UI", 17, "bold"))
            value.pack(anchor="w", pady=(2, 0))
            self.metric_values[key] = value

        top = ttk.Frame(outer)
        top.pack(fill="x", pady=(0, 12))
        self._build_insert_panel(top)
        self._build_delete_panel(top)
        self.status_var = tk.StringVar(value="Ready")
        status_row = ttk.Frame(outer)
        status_row.pack(fill="x", pady=(0, 7))
        ttk.Label(status_row, text="LIVE RECORDS", style="Hint.TLabel").pack(side="left")
        self.status_label = ttk.Label(status_row, textvariable=self.status_var, style="Hint.TLabel")
        self.status_label.pack(side="right")
        self._build_tabs(outer)

    def _build_insert_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.LabelFrame(parent, text="Add a group and entry", style="Card.TLabelframe")
        panel.pack(side="left", fill="both", expand=True, padx=(0, 8))
        for col in (1, 3):
            panel.columnconfigure(col, weight=1)
        self.cluster_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.shg_var = tk.StringVar()
        self.entry_type_var = tk.StringVar(value=ENTRY_TYPES[0])
        self.amount_var = tk.StringVar()
        self._field(panel, "Cluster name", self.cluster_var, 0, 0)
        self._field(panel, "Officer email (new cluster)", self.email_var, 0, 2)
        self._field(panel, "SHG name", self.shg_var, 1, 0)
        ttk.Label(panel, text="Entry type", style="Card.TLabel").grid(row=1, column=2, sticky="w", padx=(10, 4), pady=5)
        ttk.Combobox(panel, textvariable=self.entry_type_var, values=ENTRY_TYPES, state="readonly").grid(row=1, column=3, sticky="ew", padx=(0, 4), pady=5)
        self._field(panel, "Amount (₹)", self.amount_var, 2, 0)
        ttk.Button(panel, text="Add Record", style="Accent.TButton", command=self.add_record).grid(row=2, column=2, columnspan=2, sticky="e", padx=4, pady=(9, 2))
        ttk.Label(panel, text="Existing cluster? Reuse its profile. New cluster? Add the officer email.", style="Card.TLabel").grid(row=3, column=0, columnspan=4, sticky="w", padx=4, pady=(7, 0))

    @staticmethod
    def _field(parent: ttk.LabelFrame, label: str, variable: tk.StringVar, row: int, col: int) -> None:
        ttk.Label(parent, text=label, style="Card.TLabel").grid(row=row, column=col, sticky="w", padx=(4 if col == 0 else 10, 4), pady=5)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=col + 1, sticky="ew", padx=(0, 4), pady=5)

    def _build_delete_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.LabelFrame(parent, text="Delete a record", style="Card.TLabelframe")
        panel.pack(side="left", fill="both", expand=True, padx=(8, 0))
        panel.columnconfigure(1, weight=1)
        self.delete_kind_var = tk.StringVar(value="Village Cluster")
        self.delete_target_var = tk.StringVar()
        ttk.Label(panel, text="Record type", style="Card.TLabel").grid(row=0, column=0, sticky="w", padx=4, pady=6)
        kind_box = ttk.Combobox(panel, textvariable=self.delete_kind_var, values=("Village Cluster", "Self-Help Group", "Savings/Loan Entry"), state="readonly")
        kind_box.grid(row=0, column=1, sticky="ew", padx=4, pady=6)
        kind_box.bind("<<ComboboxSelected>>", lambda _event: self.refresh_delete_options())
        ttk.Label(panel, text="Select record", style="Card.TLabel").grid(row=1, column=0, sticky="w", padx=4, pady=6)
        self.delete_combo = ttk.Combobox(panel, textvariable=self.delete_target_var, state="readonly")
        self.delete_combo.grid(row=1, column=1, sticky="ew", padx=4, pady=6)
        ttk.Button(panel, text="Delete Selected", style="Danger.TButton", command=self.delete_selected).grid(row=2, column=1, sticky="e", padx=4, pady=(8, 2))
        ttk.Label(panel, text="Cluster and SHG deletes cascade to their child rows.", style="Card.TLabel").grid(row=3, column=0, columnspan=2, sticky="w", padx=4, pady=(5, 0))

    def _build_tabs(self, parent: ttk.Frame) -> None:
        section = ttk.Frame(parent)
        section.pack(fill="both", expand=True)
        section_head = ttk.Frame(section)
        section_head.pack(fill="x", pady=(0, 7))
        ttk.Label(section_head, text="Database explorer", font=("Segoe UI", 12, "bold")).pack(side="left")
        ttk.Label(section_head, text="Live view  ·  updates after every change", style="Hint.TLabel").pack(side="left", padx=(12, 0))
        ttk.Button(section_head, text="↻  Refresh", command=self.refresh_all).pack(side="right")
        tabs = ttk.Notebook(section)
        tabs.pack(fill="both", expand=True)
        self.trees: dict[str, ttk.Treeview] = {}
        specs = (
            ("joined", "SHG + Ledger", ("shg_id", "cluster_name", "shg_name", "formation_date", "entry_type", "entry_amount")),
            ("clusters", "Village Clusters", ("cluster_id", "cluster_name", "officer_email")),
            ("groups", "Self-Help Groups", ("shg_id", "cluster_id", "shg_name", "formation_date")),
            ("entries", "Savings & Loan Entries", ("entry_id", "shg_id", "entry_type", "entry_amount")),
        )
        headings = {"shg_id": "SHG ID", "cluster_name": "Cluster Name", "shg_name": "SHG Name", "formation_date": "Formation Date", "entry_type": "Entry Type", "entry_amount": "Entry Amount (₹)", "cluster_id": "Cluster ID", "cluster_id": "Cluster ID", "officer_email": "Officer Email", "entry_id": "Entry ID"}
        widths = {"shg_id": 80, "cluster_name": 180, "shg_name": 210, "formation_date": 125, "entry_type": 190, "entry_amount": 120, "cluster_id": 90, "officer_email": 240, "entry_id": 85}
        for key, title, columns in specs:
            frame = ttk.Frame(tabs, padding=8)
            tabs.add(frame, text=title)
            frame.rowconfigure(0, weight=1)
            frame.columnconfigure(0, weight=1)
            tree = ttk.Treeview(frame, columns=columns, show="headings")
            ybar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            xbar = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
            tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
            tree.grid(row=0, column=0, sticky="nsew")
            ybar.grid(row=0, column=1, sticky="ns")
            xbar.grid(row=1, column=0, sticky="ew")
            for col in columns:
                tree.heading(col, text=headings[col])
                tree.column(col, width=widths.get(col, 130), minwidth=70, stretch=True, anchor="e" if col in ("entry_amount", "shg_id", "cluster_id", "entry_id") else "w")
            tree.tag_configure("even", background="#ffffff")
            tree.tag_configure("odd", background="#f5f8f5")
            self.trees[key] = tree

    def add_record(self) -> None:
        cluster = self.cluster_var.get().strip()
        email = self.email_var.get().strip()
        shg = self.shg_var.get().strip()
        amount_text = self.amount_var.get().strip().replace(",", "")
        if not cluster or not shg or not self.entry_type_var.get().strip() or not amount_text:
            messagebox.showwarning("Missing information", "Enter a cluster name, SHG name, entry type, and amount.", parent=self.root)
            return
        try:
            amount = float(amount_text)
        except ValueError:
            messagebox.showwarning("Invalid amount", "Entry amount must be a number, such as 1250 or 1250.50.", parent=self.root)
            return
        if amount < 0:
            messagebox.showwarning("Invalid amount", "Entry amount cannot be negative.", parent=self.root)
            return
        if not amount < float("inf"):
            messagebox.showwarning("Invalid amount", "Enter a finite numeric amount.", parent=self.root)
            return
        try:
            with closing(connect_db(self.db_path)) as conn, conn:
                cluster_row = conn.execute("SELECT cluster_id FROM village_clusters WHERE cluster_name = ? COLLATE NOCASE", (cluster,)).fetchone()
                if cluster_row:
                    cluster_id = cluster_row["cluster_id"]
                else:
                    if not email:
                        messagebox.showwarning("Officer email required", "Provide an officer email when creating a new village cluster.", parent=self.root)
                        return
                    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
                        messagebox.showwarning("Invalid email", "Enter a valid officer email for the new cluster.", parent=self.root)
                        return
                    cluster_id = conn.execute("INSERT INTO village_clusters(cluster_name, officer_email) VALUES (?, ?)", (cluster, email)).lastrowid
                shg_id = conn.execute("INSERT INTO self_help_groups(cluster_id, shg_name, formation_date) VALUES (?, ?, ?)", (cluster_id, shg, date.today().isoformat())).lastrowid
                conn.execute("INSERT INTO savings_loan_entries(shg_id, entry_type, entry_amount) VALUES (?, ?, ?)", (shg_id, self.entry_type_var.get(), amount))
            for var in (self.cluster_var, self.email_var, self.shg_var, self.amount_var):
                var.set("")
            self.entry_type_var.set(ENTRY_TYPES[0])
            self.refresh_all()
            self.status_var.set(f"Added SHG #{shg_id} and its {amount:,.2f} entry.")
        except sqlite3.Error as exc:
            messagebox.showerror("Database error", f"The record could not be added.\n\n{exc}", parent=self.root)

    def delete_selected(self) -> None:
        label = self.delete_target_var.get()
        if not label:
            messagebox.showinfo("Nothing selected", "There are no records of this type to delete.", parent=self.root)
            return
        match = re.match(r"#(\d+)", label)
        if not match:
            self.refresh_delete_options()
            return
        record_id = int(match.group(1))
        kind = self.delete_kind_var.get()
        table_and_key = {
            "Village Cluster": ("village_clusters", "cluster_id"),
            "Self-Help Group": ("self_help_groups", "shg_id"),
            "Savings/Loan Entry": ("savings_loan_entries", "entry_id"),
        }
        table, key = table_and_key[kind]
        try:
            with closing(connect_db(self.db_path)) as conn, conn:
                cursor = conn.execute(f"DELETE FROM {table} WHERE {key} = ?", (record_id,))
                if cursor.rowcount == 0:
                    self.status_var.set("That record was already removed; the current list has been refreshed.")
                else:
                    self.status_var.set(f"Deleted {kind.lower()} #{record_id}.")
            self.delete_target_var.set("")
            self.refresh_all()
        except sqlite3.Error as exc:
            messagebox.showerror("Database error", f"The record could not be deleted.\n\n{exc}", parent=self.root)
            self.refresh_all()

    def refresh_all(self) -> None:
        queries = {
            "joined": "SELECT g.shg_id, c.cluster_name, g.shg_name, g.formation_date, e.entry_type, e.entry_amount FROM self_help_groups g JOIN village_clusters c ON c.cluster_id=g.cluster_id LEFT JOIN savings_loan_entries e ON e.shg_id=g.shg_id ORDER BY g.shg_id, e.entry_id",
            "clusters": "SELECT cluster_id, cluster_name, officer_email FROM village_clusters ORDER BY cluster_id",
            "groups": "SELECT shg_id, cluster_id, shg_name, formation_date FROM self_help_groups ORDER BY shg_id",
            "entries": "SELECT entry_id, shg_id, entry_type, entry_amount FROM savings_loan_entries ORDER BY entry_id",
        }
        try:
            with closing(connect_db(self.db_path)) as conn:
                self.metric_values["clusters"].configure(text=f"{conn.execute('SELECT COUNT(*) FROM village_clusters').fetchone()[0]:,}")
                self.metric_values["groups"].configure(text=f"{conn.execute('SELECT COUNT(*) FROM self_help_groups').fetchone()[0]:,}")
                self.metric_values["entries"].configure(text=f"{conn.execute('SELECT COUNT(*) FROM savings_loan_entries').fetchone()[0]:,}")
                total = conn.execute("SELECT COALESCE(SUM(entry_amount), 0) FROM savings_loan_entries").fetchone()[0]
                self.metric_values["total"].configure(text=f"₹{total:,.2f}")
                for key, sql in queries.items():
                    tree = self.trees[key]
                    tree.delete(*tree.get_children())
                    for index, row in enumerate(conn.execute(sql)):
                        values = list(row)
                        if key in ("joined", "entries"):
                            amount_index = 5 if key == "joined" else 3
                            if values[amount_index] is not None:
                                values[amount_index] = f"{values[amount_index]:,.2f}"
                        tree.insert("", "end", values=values, tags=("even" if index % 2 == 0 else "odd",))
            self.refresh_delete_options()
        except sqlite3.Error as exc:
            self.status_var.set(f"Could not refresh database views: {exc}")

    def refresh_delete_options(self) -> None:
        kind = self.delete_kind_var.get()
        queries = {
            "Village Cluster": ("SELECT cluster_id, cluster_name FROM village_clusters ORDER BY cluster_name", lambda r: f"#{r['cluster_id']} — {r['cluster_name']}"),
            "Self-Help Group": ("SELECT g.shg_id, g.shg_name, c.cluster_name FROM self_help_groups g JOIN village_clusters c ON c.cluster_id=g.cluster_id ORDER BY g.shg_id", lambda r: f"#{r['shg_id']} — {r['shg_name']} ({r['cluster_name']})"),
            "Savings/Loan Entry": ("SELECT e.entry_id, e.entry_type, e.entry_amount, g.shg_name FROM savings_loan_entries e JOIN self_help_groups g ON g.shg_id=e.shg_id ORDER BY e.entry_id", lambda r: f"#{r['entry_id']} — {r['entry_type']} ₹{r['entry_amount']:,.2f} ({r['shg_name']})"),
        }
        sql, formatter = queries[kind]
        try:
            with closing(connect_db(self.db_path)) as conn:
                options = [formatter(row) for row in conn.execute(sql)]
            self.delete_combo.configure(values=options)
            current = self.delete_target_var.get()
            if current not in options:
                self.delete_target_var.set(options[0] if options else "")
        except sqlite3.Error as exc:
            self.delete_combo.configure(values=())
            self.delete_target_var.set("")
            self.status_var.set(f"Could not refresh delete choices: {exc}")

    def close(self) -> None:
        self.root.destroy()


def main() -> None:
    initialize_database()
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise SystemExit(
            "Tk could not open a desktop window. Run this script in a local Python "
            "desktop session with a graphical display (hosted Colab/Jupyter kernels "
            "do not provide one). Database initialization completed successfully."
        ) from exc
    SHGDashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
