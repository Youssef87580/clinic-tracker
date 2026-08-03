import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import csv
import os
import shutil
import subprocess
import sys
import time
import json

UPLOADS_DIR = "patient_uploads"
SETTINGS_FILE = "clinic_Settings.json"


def get_theme(dark):
    if dark:
        return {
            "app_bg": "#0d1117", "sidebar_bg": "#161b22", "sidebar_active": "#1f6feb",
            "header_fg": "#f0f6fc", "card_bg": "#21262d", "card_border": "#30363d",
            "text_primary": "#ffffff", "text_secondary": "#8b949e", "text_muted": "#6e7681",
            "entry_bg": "#161b22", "entry_fg": "#f0f6fc",
            "owe_bg": "#3d1107", "owe_fg": "#ff7b72",
            "paid_bg": "#0e2f19", "paid_fg": "#7ee787",
            "tag_bg": "#0d1f45", "tag_fg": "#79c0ff",
            "muted_tag_bg": "#21622d", "muted_tag_fg": "#8b949e",
            "list_row_bg": "#1c2128",
            "visit_card_bg": "#1a2332", "visit_card_border": "#2c3a4f"
        }
    return {
        "app_bg": "#eefef5", "sidebar_bg": "#1e3a5f", "sidebar_active": "#2c5282",
        "header_fg": "#1e3a5f", "card_bg": "#ffffff", "card_border": "#e2e8f0",
        "text_primary": "#1e3a5f", "text_secondary": "#444444", "text_muted": "#888888",
        "entry_bg": "#ffffff", "entry_fg": "#000000",
        "owe_bg": "#fdecec", "owe_fg": "#e53e3e",
        "paid_bg": "#e6f6ec", "paid_fg": "#38a169",
        "tag_bg": "#eaf4fb", "tag_fg": "#2c5282",
        "muted_tag_bg": "#f4f4f4", "muted_tag_fg": "#666666",
        "list_row_bg": "#f7fafc",
        "visit_card_bg": "#eaf4fb", "visit_card_border": "#666666"
    }


class Database:
    def __init__(self, db_name="clinic.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.executescript("""
            CREATE TABLE IF NOT EXISTS doctors (
                doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                specialty TEXT,
                phone TEXT
            );

            CREATE TABLE IF NOT EXISTS patients (
                patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                date_of_birth TEXT,
                phone TEXT,
                address TEXT,
                doctor_id INTEGER,
                FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
            );

            CREATE TABLE IF NOT EXISTS visits (
                visit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                visit_date TEXT DEFAULT CURRENT_TIMESTAMP,
                symptoms TEXT,
                diagnosis TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
            );

            CREATE TABLE IF NOT EXISTS bills (
                bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                visit_id INTEGER NOT NULL,
                amount_required REAL NOT NULL,
                FOREIGN KEY (visit_id) REFERENCES visits(visit_id)
            );

            CREATE TABLE IF NOT EXISTS payments (
                payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id INTEGER NOT NULL,
                payment_date TEXT DEFAULT CURRENT_TIMESTAMP,
                amount_paid REAL NOT NULL,
                payment_method TEXT DEFAULT 'cash',
                FOREIGN KEY (bill_id) REFERENCES bills(bill_id)
            );

             CREATE TABLE IF NOT EXISTS patient_files (
                file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                visit_id INTEGER,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
                FOREIGN KEY (visit_id) REFERENCES visits(visit_id)
            );
        """)
        self.conn.commit()

    def execute(self, query, params=()):
        self.cursor.execute(query, params)
        self.conn.commit()
        return self.cursor

    def fetchall(self, query, params=()):
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def fetchone(self, query, params=()):
        self.cursor.execute(query, params)
        return self.cursor.fetchone()


class ClinicApp:
    def __init__(self, root):
        self.db = Database()
        self.root = root
        self.current_patient_id = None
        self.root.title("Clinic Management System")
        self.root.geometry("1100x700")
        self.settings = self.load_settings()
        self.theme = get_theme(self.settings["dark"])
        self.root.configure(bg=self.theme["app_bg"])
        self.root.minsize(900, 600)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.configure_ttk_styles()

        self.build_sidebar()
        self.build_content_area()
        self.build_all_screens()

        self.show_screen("dashboard")
        self.refresh_all_data()

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    loaded.setdefault("dark", False)
                    loaded.setdefault("language", "en")
                    return loaded
            except Exception:
                pass
        return {"dark": False, "language": "en"}

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def on_close(self):
        self.save_settings()
        self.root.destroy()

    def apply_settings_change(self):
        self.theme = get_theme(self.settings["dark"])
        self.root.configure(bg=self.theme["app_bg"])
        self.configure_ttk_styles()
        self.save_settings()
        self.rebuild_ui()

    def rebuild_ui(self):
        active = getattr(self, "_active_screen_name", "dashboard")
        self.sidebar.destroy()
        self.content.destroy()
        self.build_sidebar()
        self.build_content_area()
        self.build_all_screens()
        self.show_screen(active)
        self.refresh_all_data()

    def configure_ttk_styles(self):
        t = self.theme
        self.style.configure("Sidebar.TButton", font=(
            "sefoe ui", 13), fg="white", bg=t["sidebar_bg"], padding=10)
        self.style.map("Sidebat.TButton", bg=[("active", t["sidebar_active"])])
        self.style.configure("Card.TFrame", bg=t["card_bg"])
        self.style.configure("Card.TLabel", bg=t["card_bg"], font=(
            "segoe ui", 16, "bold"), fg=t["text_primary"])
        self.style.configure("Action.TButton", font=("segpe ui", 12, "bold"))
        self.style.configure(
            "RCombobox", fieldbackground=t["entry_bg"], bg=t["entry_bg"], fg=t["entry_fg"], arrowcolor=t["text_primary"])
        self.style.map("TCombobox", fieldbackground=[
                       ("readonly", t["entry_bg"])], fg=[("readonly", t["entry_fg"])])
        self.style.configure("TScrollbar", bg="#6b7280", troughcolor="#374151",
                             bordercolor="#374151", arrowcolor="#f3f4f6")
        self.style.configure("Treeview.heading", bg=t["sidebar_bg"],  foreground="white", font=(
            "segoe ui", 11, "bold"))
        self.style.map("Treeview", bg=[("selected", t["sidebar_active"])], fg=[
                       ("selected", "white")])

    def build_sidebar(self):
        t = self.theme
        self.sidebar = tk.Frame(self.root, bg=t["sidebar_bg"], width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="ClinicPro", font=("Segoe UI", 20,
                 "bold"), bg=t["sidebar_bg"], fg="white", pady=20).pack(fill="x")

        buttons = [
            ("Dashboard", "dashboard"),
            ("Doctors", "doctors"),
            ("Patients", "patients"),
            ("Visits", "visits"),
            ("Payments", "payments"),
            ("Balances", "balances"),
        ]

        for text, screen in buttons:
            tk.Button(self.sidebar, text=text, font=("Segoe UI", 13), bg=t["sidebar_bg"], fg="white", activebackground=t["sidebar_active"],
                      activeforeground="white", bd=0, cursor="hand2", padx=20, pady=12, anchor="w", command=lambda s=screen: self.show_screen(s)).pack(fill="x", padx=0, pady=2)

    def build_content_area(self):
        t = self.theme
        self.content = tk.Frame(self.root, bg=t["app_bg"])
        self.content.pack(side="right", fill="both",
                          expand=True, padx=20, pady=20)

        header_row = tk.Frame(self.content, bg=t["app_bg"])
        header_row.pack(fill="x", pady=(0, 20))

        self.header = tk.Label(header_row, text="Dashboard", font=(
            "Segoe UI", 22, "bold"), bg=t["app_bg"], fg=t["header_fg"])
        self.header.pack(side="left", anchor="w")

        self.screen_container = tk.Frame(self.content, bg=t["app_bg"])
        self.screen_container.pack(fill="both", expand=True)

    def show_screen(self, name, header_override=None):
        self.header.config(
            text=header_override if header_override else name.replace("_", " ").title())
        Frame = self.screens[name]
        Frame.tkraise()
        self.refresh_screen(name)

    def build_all_screens(self):
        t = self.theme
        self.screens = {}
        for name in ["dashboard", "doctors", "patients", "visits", "payments", "balances", "patient_detail"]:
            Frame = tk.Frame(self.screen_container, bg=t["app_bg"])
            Frame.place(relwidth=1, relheight=1)
            self.screens[name] = Frame
            getattr(self, f"build_{name}_screen")(Frame)

    def build_dashboard_screen(self, parent):
        t = self.theme
        cards_row = tk.Frame(parent, bg=t["app_bg"])
        cards_row.pack(fill="x", pady=(0, 20))

        self.stat_cards = {}
        stats = [("Total Doctors", "#2c5282"), ("Total Patients", "#38a169"),
                 ("Total Revenue", "#d69e2e"), ("Outstanding", "#e53e3e")]

        for title, color in stats:
            card = tk.Frame(cards_row, bg=t["card_bg"], bd=1, relief="solid",
                            highlightbackground=t["card_border"], highlightthickness=1)
            card.pack(side="left", fill="both", expand=True, padx=5)
            value_lbl = tk.Label(card, text="0", font=(
                "Segoe UI", 28, "bold"), bg=t["card_bg"], fg=color)

            value_lbl.pack(pady=(15, 5))

            title_lbl = tk.Label(card, text=title, font=("Segoe UI", 11),
                                 bg=t["card_bg"], fg=t["text_muted"])
            title_lbl.pack(pady=(0, 15))
            self.stat_cards[title] = value_lbl

        recent = tk.Frame(parent, bg=t["card_bg"], bd=1, relief="solid",
                          highlightbackground=t["card_border"], highlightthickness=1)
        recent.pack(fill="both", expand=True)
        tk.Label(recent, text="Recent Visits", font=("Segoe UI", 14, "bold"),
                 bg=t["card_bg"], fg=t["text_primary"]).pack(anchor="w", padx=15, pady=15)

        cols = ("Patient", "Date", "Amount", "Paid", "Balance")
        self.recent_tree = ttk.Treeview(
            recent, columns=cols, show="headings", height=8)
        for c in cols:
            self.recent_tree.heading(c, text=c)
            self.recent_tree.column(c, width=150)
        self.recent_tree.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    def build_doctors_screen(self, parent):
        t = self.theme
        form = tk.LabelFrame(parent, text="Add Doctor", bg=t["card_bg"], font=(
            "Segoe UI", 11, "bold"), fg=t["text_primary"], padx=15, pady=15)
        form.pack(fill="x", pady=(0, 15))

        tk.Label(form, text="Full Name:", bg=t["card_bg"]).grid(
            row=0, column=0, sticky="w")
        self.doc_name = tk.Entry(form, width=30)
        self.doc_name.grid(row=0, column=1, padx=5, pady=3)

        tk.Label(form, text="Specialty:", bg=t["card_bg"]).grid(
            row=1, column=0, sticky="w")
        self.doc_spec = tk.Entry(form, width=30)
        self.doc_spec.grid(row=1, column=1, padx=5, pady=3)

        tk.Label(form, text="Phone:", bg=t["card_bg"]).grid(
            row=2, column=0, sticky="w")
        self.doc_phone = tk.Entry(form, width=30)
        self.doc_phone.grid(row=2, column=1, padx=5, pady=3)

        tk.Button(form, text="Add Doctor", bg="#38a169", fg="white", font=("Segoe UI", 10, "bold"), bd=0,
                  padx=20, pady=5, cursor="hand2", command=self.add_doctor).grid(row=3, column=1, pady=10, sticky="e")

        search_row = tk.Frame(parent, bg=t["app_bg"])
        search_row.pack(fill="x", pady=(0, 10))
        tk.Label(search_row, text="Search:", bg=t["app_bg"]).pack(side="left")
        self.doc_search = tk.Entry(search_row, width=30)
        self.doc_search.pack(side="left", padx=5)
        self.doc_search.bind("<KeyRelease>", lambda e: self.refresh_doctors())
        tk.Button(search_row, text="Delete Selected", bg="#e53e3e", fg="white", font=("Segoe UI", 10, "bold"),
                  bd=0, padx=15, pady=4, cursor="hand2", command=self.delete_doctor).pack(side="right")

        list_Frame = tk.Frame(parent, bg=t["card_bg"], bd=1, relief="solid")
        list_Frame.pack(fill="both", expand=True)

        cols = ("ID", "Name", "Specialty", "Phone", "Patients")
        self.doctors_tree = ttk.Treeview(
            list_Frame, columns=cols, show="headings", height=12)
        for c in cols:
            self.doctors_tree.heading(c, text=c)
            self.doctors_tree.column(c, width=170)
        self.doctors_tree.pack(fill="both", expand=True, padx=10, pady=10)

    def build_patients_screen(self, parent):
        t = self.theme
        top_bar = tk.Frame(parent, bg=t["app_bg"])
        top_bar.pack(fill="x", pady=(0, 15))
        tk.Label(top_bar, text="Search:", bg=t["app_bg"]).pack(side="left")
        self.pat_search = tk.Entry(top_bar, width=30)
        self.pat_search.pack(side="left", padx=5)
        self.pat_search.bind("<KeyRelease>", lambda e: self.refresh_patients())
        tk.Button(top_bar, text="+ Add Patient", bg="#38a169", fg="white", font=("Segoe UI", 10, "bold"),
                  bd=0, padx=15, pady=6, cursor="hand2", command=self.open_add_patient_modal).pack(side="right")
        canvas_holder = tk.Frame(parent, bg=t["app_bg"])
        canvas_holder.pack(fill="both", expand=True)
        self.patients_canvas = tk.Canvas(
            canvas_holder, bg=t["app_bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            canvas_holder, orient="vertical", command=self.patients_canvas.yview)
        self.patients_list_frame = tk.Frame(
            self.patients_canvas, bg=t["app_bg"])
        window_id = self.patients_canvas.create_window(
            (0, 0), window=self.patients_list_frame, anchor="nw")
        self.patients_list_frame.bind("<Configure>", lambda e: self.patients_canvas.configure(
            scrollregion=self.patients_canvas.bbox("all")))
        self.patients_canvas.bind(
            "<Configure>", lambda e: self.patients_canvas.itemconfig(window_id, width=e.width))
        self.patients_canvas.configure(yscrollcommand=scrollbar.set)
        self.patients_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def open_add_patient_modal(self):
        t = self.theme
        win = tk.Toplevel(self.root)
        win.title("Add patient")
        win.geometry("380x430")
        win.configure(bg=t["card_bg"])
        win.grab_set()
        tk.Label(win, text="Add New Patient", font=("Segoe UI", 14, "bold"),
                 bg=t["card_bg"], fg=t["text_primary"]).pack(anchor="w", padx=20, pady=(20, 15))
        fields = [("Full Name:", "name"), ("Date of Birth:", "dob"),
                  ("Phone:", "phone"), ("Address:", "address")]
        entries = {}
        for label, key in fields:
            tk.Label(win, text=label, bg=t["card_bg"], font=(
                "Segoe UI", 9), fg=t["text_secondary"]).pack(anchor="w", padx=20)
            ent = tk.Entry(win, width=36)
            ent.pack(padx=20, pady=(2, 10))
            entries[key] = ent
        tk.Label(win, text="Doctor:", bg=t["card_bg"], font=(
            "Segoe UI", 9), fg=t["text_secondary"]).pack(anchor="w", padx=20)
        doctors = self.db.fetchall(
            "SELECT doctor_id, full_name FROM doctors ORDER BY full_name")
        doctor_box = ttk.Combobox(win, width=34, state="readonly", values=[
                                  f"{d[0]} - {d[1]}" for d in doctors])
        doctor_box.pack(padx=20, pady=(2, 15))

        def submit():
            name = entries["name"].get().strip()
            if not name:
                messagebox.showwarning("Missing", "Please enter a name")
                return
            doctor_id = doctor_box.get().split(
                " - ")[0] if doctor_box.get() else None
            self.db.execute("INSERT INTO patients (full_name, date_of_birth, phone, address, doctor_id) VALUES (?, ?, ?, ?, ?)",
                            (name, entries["dob"].get(), entries["phone"].get(), entries["address"].get(), doctor_id))
            self.refresh_all_data()
            win.destroy()
            messagebox.showinfo("Success", "Patient added!")
        tk.Button(win, text="Add Patient", bg="#38a169", fg="white", font=(
            "Segoe UI", 10, "bold"), bd=0, padx=20, pady=8, cursor="hand2", command=submit).pack(pady=10)

    def build_patient_card(self, parent, patient_id, full_name, dob, phone, address, doctor_name, balance):
        t = self.theme
        card = tk.Frame(parent, bg=t["card_bg"], bd=1, relief="solid",
                        highlightbackground="#e2e8f0", highlightthickness=1)
        card.pack(fill="x", pady=6, padx=2)

        inner = tk.Frame(card, bg=t["card_bg"])
        inner.pack(fill="x", padx=15, pady=12)

        initials = "".join([w[0]for w in full_name.split()[:2]]).upper() or "?"

        avatar = tk.Frame(inner, bg="#2c5282", width=56, height=56)
        avatar.pack(side="left", padx=(0, 15))
        avatar.pack_propagate(False)
        tk.Label(avatar, text=initials, bg="#2c5282", fg="white",
                 font=("Segoe UI", 16, "bold")).pack(expand=True)

        mid = tk.Frame(inner, bg=t["card_bg"])
        mid.pack(side="left", fill="both", expand=True)

        top_row = tk.Frame(mid, bg=t["card_bg"])
        top_row.pack(fill="x")
        tk.Label(top_row, text=full_name, font=("Segoe UI", 13, "bold"),
                 bg=t["card_bg"], fg=t["text_primary"]).pack(side="left")

        if balance and balance > 0:
            badge = tk.Label(top_row, text=f"Owes ${balance:.2f}", font=(
                "Segoe UI", 9, "bold"), bg="#fdecec", fg="#e53e3e", padx=8, pady=2)
        else:
            badge = tk.Label(top_row, text="Paid Up", font=(
                "Segoe UI", 9, "bold"), bg="#e6f6ec", fg="#38a169", padx=8, pady=2)
        badge.pack(side="right")

        info_row = tk.Label(
            mid, text=f"\U0001F4DE {phone or 'N/A'}     \U0001F382 {dob or 'N/A'}", font=("Segoe UI", 9), bg=t["card_bg"], fg=t["text_muted"])
        info_row.pack(anchor="w", pady=(4, 4))

        tag_row = tk.Frame(mid, bg=t["card_bg"])
        tag_row.pack(anchor="w")
        tk.Label(tag_row, text=f"Dr. {doctor_name}" if doctor_name else "Unassigned", font=(
            "Segoe UI", 8, "bold"), bg="#eaf4fb", fg="#2c5282", padx=6, pady=2).pack(side="left", padx=(0, 6))
        if address:
            tk.Label(tag_row, text=f"\U0001F4CD {address}", font=(
                "Segoe UI", 8), bg="#f4f4f4", fg=t["text_muted"], padx=6, pady=2).pack(side="left")

        action_col = tk.Frame(inner, bg=t["card_bg"])
        action_col.pack(side="right", padx=(15, 0))
        tk.Button(action_col, text="Open File", bg="#5b6bf5", fg="white", font=("Segoe UI", 9, "bold"), bd=0,
                  padx=14, pady=6, cursor="hand2", command=lambda pid=patient_id: self.open_patient_file(pid)).pack()

        for w in (card, inner, mid, top_row, info_row, tag_row):
            w.bind("<Double-Button-1>", lambda e,
                   pid=patient_id: self.open_patient_file(pid))
            w.configure(cursor="hand2")

    def build_visits_screen(self, parent):
        t = self.theme
        form = tk.LabelFrame(parent, text="Record Visit", bg=t["card_bg"], font=(
            "Segoe UI", 11, "bold"), fg=t["text_primary"], padx=15, pady=15)
        form.pack(fill="x", pady=(0, 15))
        tk.Label(form, text="Patient:", bg=t["card_bg"]).grid(
            row=0, column=0, sticky="w")
        self.visit_patient = ttk.Combobox(form, width=38, state="readonly")
        self.visit_patient.grid(row=0, column=1, padx=5, pady=3)

        tk.Label(form, text="Symptoms:", bg=t["card_bg"]).grid(
            row=1, column=0, sticky="w")
        self.visit_symptoms = tk.Entry(form, width=40)
        self.visit_symptoms.grid(row=1, column=1, padx=5, pady=3)

        tk.Label(form, text="Diagnosis:", bg=t["card_bg"]).grid(
            row=2, column=0, sticky="w")
        self.visit_diagnosis = tk.Entry(form, width=40)
        self.visit_diagnosis.grid(row=2, column=1, padx=5, pady=3)

        tk.Label(form, text="Amount Required ($):", bg=t["card_bg"]).grid(
            row=3, column=0, sticky="w")
        self.visit_amount = tk.Entry(form, width=40)
        self.visit_amount.grid(row=3, column=1, padx=5, pady=3)

        tk.Button(form, text="Record Visit", bg="#38a169", fg="white", font=("Segoe UI", 10, "bold"), bd=0,
                  padx=20, pady=5, cursor="hand2", command=self.add_visit).grid(row=4, column=1, pady=10, sticky="e")

        tk.Button(parent, text="Delete Selected Visit", bg="#e53e3e", fg="white", font=("Segoe UI", 10, "bold"),
                  bd=0, padx=15, pady=4, cursor="hand2", command=self.delete_visit).pack(anchor="e", pady=(0, 10))

        list_Frame = tk.Frame(parent, bg=t["card_bg"], bd=1, relief="solid")
        list_Frame.pack(fill="both", expand=True)

        cols = ("ID", "Patient", "Date", "Symptoms", "Diagnosis", "Amount")
        self.visits_tree = ttk.Treeview(
            list_Frame, columns=cols, show="headings", height=12)
        for c in cols:
            self.visits_tree.heading(c, text=c)
            self.visits_tree.column(c, width=140)
        self.visits_tree.pack(fill="both", expand=True, padx=10, pady=10)

    def build_payments_screen(self, parent):
        t = self.theme
        form = tk.LabelFrame(parent, text="Record Payment", bg=t["card_bg"], font=(
            "Segoe UI", 11, "bold"), fg=t["text_primary"], padx=15, pady=15)
        form.pack(fill="x", pady=(0, 15))

        tk.Label(form, text="Visit (Patient - Date - Balance):",
                 bg=t["card_bg"]).grid(row=0, column=0, sticky="w")
        self.pay_visit = ttk.Combobox(form, width=50, state="readonly")
        self.pay_visit.grid(row=0, column=1, padx=5, pady=3)

        tk.Label(form, text="Amount Paid ($):", bg=t["card_bg"]).grid(
            row=1, column=0, sticky="w")
        self.pay_amount = tk.Entry(form, width=50)
        self.pay_amount.grid(row=1, column=1, padx=5, pady=3)

        tk.Label(form, text="Method:", bg=t["card_bg"]).grid(
            row=2, column=0, sticky="w")
        self.pay_method = ttk.Combobox(form, values=["Cash", "Card", "Insurance", "Bank Transfer"],
                                       width=48, state="readonly")
        self.pay_method.set("Cash")
        self.pay_method.grid(row=2, column=1, padx=5, pady=3)

        tk.Button(form, text="Record Payment", bg="#38a169", fg="white", font=("Segoe UI", 10, "bold"), bd=0,
                  padx=20, pady=5, cursor="hand2", command=self.add_payment).grid(row=3, column=1, pady=10, sticky="e")

        tk.Button(parent, text="Delete Selected Payment", bg="#e53e3e", fg="white", font=("Segoe UI", 10, "bold"),
                  bd=0, padx=15, pady=4, cursor="hand2", command=self.delete_payment).pack(anchor="e", pady=(0, 10))

        list_Frame = tk.Frame(parent, bg=t["card_bg"], bd=1, relief="solid")
        list_Frame.pack(fill="both", expand=True)

        cols = ("ID", "Patient", "Visit Date",
                "Amount Paid", "Method", "Payment Date")
        self.payments_tree = ttk.Treeview(
            list_Frame, columns=cols, show="headings", height=12)
        for c in cols:
            self.payments_tree.heading(c, text=c)
            self.payments_tree.column(c, width=150)
        self.payments_tree.pack(fill="both", expand=True, padx=10, pady=10)

    def build_balances_screen(self, parent):
        t = self.theme
        list_Frame = tk.Frame(parent, bg=t["card_bg"], bd=1, relief="solid")
        list_Frame.pack(fill="both", expand=True)

        header_row = tk.Frame(list_Frame, bg=t["card_bg"])
        header_row.pack(fill="x", padx=15, pady=15)
        tk.Label(header_row, text="Outstanding Balances", font=(
            "Segoe UI", 14, "bold"), bg=t["card_bg"], fg=t["text_primary"]).pack(side="left")
        tk.Button(header_row, text="Export to CSV", bg="#2c5282", fg="white", font=("Segoe UI", 10, "bold"),
                  bd=0, padx=15, pady=4, cursor="hand2", command=self.export_balances).pack(side="right")

        cols = ("Patient", "Total Required", "Total Paid", "Balance", "Doctor")
        self.balances_tree = ttk.Treeview(
            list_Frame, columns=cols, show="headings", height=18)
        for c in cols:
            self.balances_tree.heading(c, text=c)
            self.balances_tree.column(c, width=170)
        self.balances_tree.pack(
            fill="both", expand=True, padx=15, pady=(0, 15))

    def build_patient_detail_screen(self, parent):
        t = self.theme
        top_bar = tk.Frame(parent, bg=t["app_bg"])
        top_bar.pack(fill="x", pady=(0, 10))

        tk.Button(top_bar, text="\u2190 Back to Patients", 	bg=t["sidebar_bg"], fg="white",
                  font=("Segoe UI", 10, "bold"), bd=0, padx=15, pady=6, cursor="hand2",
                  command=lambda: self.show_screen("patients")).pack(side="left")
        tk.Button(top_bar, text="Delete Patient", bg="#e53e3e", fg="white", font=("Segoe UI", 10, "bold"),
                  bd=0, padx=15, pady=6, cursor="hand2", command=self.delete_current_patient).pack(side="right")

        tk.Button(top_bar, text="Upload Image to Patient File", bg="#38a169", fg="white",
                  font=("Segoe UI", 10, "bold"), bd=0, padx=15, pady=6, cursor="hand2",
                  command=lambda: self.upload_image(self.current_patient_id, None)).pack(side="right", padx=(0, 8))

        info_card = tk.Frame(parent, bg=t["card_bg"], bd=1, relief="solid",
                             highlightbackground=t["card_border"], highlightthickness=1)
        info_card.pack(fill="x", pady=(0, 15))
        self.pd_name_label = tk.Label(info_card, text="", font=(
            "Segoe UI", 16, "bold"), bg=t["card_bg"], fg=t["text_primary"])
        self.pd_name_label.pack(anchor="w", padx=15, pady=(15, 5))
        self.pd_info_label = tk.Label(info_card, text="", font=(
            "Segoe UI", 10), bg=t["card_bg"], fg="#555", justify="left")
        self.pd_info_label.pack(anchor="w", padx=15, pady=(0, 15))
        files_card = tk.Frame(parent, bg=t["card_bg"], bd=1, relief="solid",
                              highlightbackground=t["card_border"], highlightthickness=1)
        files_card.pack(fill="x", pady=(0, 15))
        tk.Label(files_card, text="Uploaded Files", font=("Segoe UI", 12, "bold"),
                 bg=t["card_bg"], fg=t["text_primary"]).pack(anchor="w", padx=15, pady=(10, 5))
        self.pd_files_list = tk.Frame(files_card, bg=t["card_bg"])
        self.pd_files_list.pack(fill="x", padx=15, pady=(0, 12))
        visits_card = tk.Frame(parent, bg=t["card_bg"], bd=1, relief="solid",
                               highlightbackground=t["card_border"], highlightthickness=1)
        visits_card.pack(fill="both", expand=True)
        tk.Label(visits_card, text="Visits", font=("segoe ui", 12, "bold"),
                 bg=t["card_bg"], fg=t["text_primary"]).pack(anchor="w", padx=15, pady=(10, 5))
        canvas_holder = tk.Frame(visits_card, bg=t["card_bg"])
        canvas_holder.pack(fill="both", expand=True, padx=14, pady=(0, 15))
        self.pd_canvas = tk.Canvas(
            canvas_holder, bg=t["card_bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            canvas_holder, orient="vertical", command=self.pd_canvas.yview)
        self.pd_cards_frame = tk.Frame(self.pd_canvas, bg=t["card_bg"])
        self.pd_cards_frame.bind(
            "<Configure>",
            lambda e: self.pd_canvas.configure(
                scrollregion=self.pd_canvas.bbox("all"))
        )
        self.pd_canvas.create_window(
            (0, 0), window=self.pd_cards_frame, anchor="nw")
        self.pd_canvas.configure(yscrollcommand=scrollbar.set)
        self.pd_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def open_patient_file(self, patient_id):
        self.current_patient_id = patient_id
        patient = self.db.fetchone("""
            SELECT p.full_name, p.date_of_birth, p.phone, p.address, d.full_name
            FROM patients p LEFT JOIN doctors d ON p.doctor_id = d.doctor_id
            WHERE p.patient_id = ?
        """, (patient_id,))
        if not patient:
            messagebox.showerror("Error", "Patient not found.")
            return
        self.show_screen("patient_detail",
                         header_override=f"Patient File \u2013 {patient[0]}")

    def build_file_card(self, parent, file_id, file_name, file_path, tag_text=None):
        t = self.theme
        row = tk.Frame(parent, bg=t["card_bg"], bd=1, relief="solid",
                       highlightbackground="#eee", highlightthickness=1)
        row.pack(fill="x", pady=4)

        inner = tk.Frame(row, bg=t["card_bg"])
        inner.pack(fill="x", padx=10, pady=8)

        thumb = tk.Frame(inner, bg="#eaf4fb", width=40, height=40)
        thumb.pack(side="left")
        thumb.pack_propagate(False)
        tk.Label(thumb, text="\U0001F5BC", bg="#eaf4fb",
                 font=("Segoe UI", 16)).pack(expand=True)

        text_col = tk.Frame(inner, bg=t["card_bg"])
        text_col.pack(side="left", fill="x", expand=True, padx=10)
        tk.Label(text_col, text=file_name, font=("Segoe UI", 10, "bold"),
                 bg=t["card_bg"], fg="#333", anchor="w").pack(anchor="w")
        if tag_text:
            tk.Label(text_col, text=tag_text, font=("Segoe UI", 8),
                     bg=t["card_bg"], fg="#999", anchor="w").pack(anchor="w")

        btns = tk.Frame(inner, bg=t["card_bg"])
        btns.pack(side="right")
        tk.Button(btns, text="Open", bg="#2c5282", fg="white", bd=0, padx=10, pady=3, cursor="hand2",
                  command=lambda p=file_path: self.open_file_external(p)).pack(side="left", padx=4)
        tk.Button(btns, text="Delete", bg="#e53e3e", fg="white", bd=0, padx=10, pady=3, cursor="hand2",
                  command=lambda fid=file_id: self.delete_patient_file(fid)).pack(side="left")

    def refresh_patient_detail(self):
        t = self.theme
        if self.current_patient_id is None:
            return
        patient_id = self.current_patient_id
        patient = self.db.fetchone("""
            SELECT p.full_name, p.date_of_birth, p.phone, p.address, d.full_name
            FROM patients p LEFT JOIN doctors d ON p.doctor_id = d.doctor_id
            WHERE p.patient_id = ?
        """, (patient_id,))
        if not patient:
            self.show_screen("patients")
            return

        self.pd_name_label.config(text=patient[0])
        self.pd_info_label.config(
            text=f"DOB: {patient[1] or 'N/A'}    |    Phone: {patient[2] or 'N/A'}\n" f"Address: {patient[3] or 'N/A'}    |    Doctor: {patient[4] or 'Unassigned'}")
        for w in self.pd_files_list.winfo_children():
            w.destroy()
        files = self.db.fetchall("""
            SELECT pf.file_id, pf.file_name, pf.file_path, v.visit_date
            FROM patient_files pf
            LEFT JOIN visits v ON pf.visit_id = v.visit_id
            WHERE pf.patient_id = ?
            ORDER BY pf.uploaded_at DESC
        """, (patient_id,))

        if not files:
            tk.Label(self.pd_files_list, text="No files uploaded yet.",
                     bg=t["card_bg"], fg="#999").pack(anchor="w")
        else:
            for file_id, file_name, file_path, visit_date in files:
                tag = f"From visit: {visit_date}" if visit_date else "General patient file"
                self.build_file_card(self.pd_files_list,
                                     file_id, file_name, file_path, tag)

        for w in self.pd_cards_frame.winfo_children():
            w.destroy()
        visits = self.db.fetchall("""
            SELECT v.visit_id, v.visit_date, v.symptoms, v.diagnosis, b.amount_required
            FROM visits v LEFT JOIN bills b ON v.visit_id = b.visit_id
            WHERE v.patient_id = ?
            ORDER BY v.visit_date DESC
        """, (patient_id,))
        cols_per_row = 3
        if not visits:
            tk.Label(self.pd_cards_frame, text="No visits recorded yet.",
                     bg=t["card_bg"], fg="#999").grid(row=0, column=0, sticky="w", pady=10)
        else:
            for idx, (visit_id, visit_date, symptoms, diagnosis, amount) in enumerate(visits):
                r, c = divmod(idx, cols_per_row)
                self.build_visit_card(
                    self.pd_cards_frame, r, c, visit_id, visit_date, symptoms, diagnosis, amount)

    def build_visit_card(self, parent, row, col, visit_id, visit_date, symptoms, diagnosis, amount):
        t = self.theme
        card = tk.Frame(parent, bg="#eaf4fb", bd=1, relief="solid",
                        highlightbackground="#cfe3f0", highlightthickness=1, width=220, height=120)
        card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        card.grid_propagate(False)

        date_lbl = tk.Label(card, text=str(visit_date), font=(
            "Segoe UI", 11, "bold"), bg="#eaf4fb", fg=t["text_primary"], anchor="w")
        date_lbl.pack(fill="x", padx=10, pady=(10, 2))
        symptoms_text = (symptoms or "No symptoms noted")
        diagnosis_text = (diagnosis or "No diagnosis noted")

        sym_lbl = tk.Label(card, text=f"Symptoms: {symptoms_text}", font=(
            "Segoe UI", 9), bg="#eaf4fb", fg=t["text_secondary"], anchor="w", wraplength=190, justify="left")
        sym_lbl.pack(fill="x", padx=10)

        diag_lbl = tk.Label(card, text=f"Diagnosis: {diagnosis_text}", font=(
            "Segoe UI", 9), bg="#eaf4fb", fg=t["text_secondary"], anchor="w", wraplength=190, justify="left")
        diag_lbl.pack(fill="x", padx=10)

        amt_text = f"${amount:.2f}" if amount is not None else "N/A"
        amt_lbl = tk.Label(card, text=f"Amount: {amt_text}", font=(
            "Segoe UI", 9, "bold"), bg="#eaf4fb", fg="#2c5282", anchor="w")
        amt_lbl.pack(fill="x", padx=10, pady=(2, 10))

        for widget in (card, date_lbl, sym_lbl, diag_lbl, amt_lbl):
            widget.bind("<Button-1>", lambda e,
                        vid=visit_id: self.show_visit_details(vid))
            widget.configure(cursor="hand2")

    def show_visit_details(self, visit_id):
        t = self.theme
        visit = self.db.fetchone("""
            SELECT v.visit_id, v.visit_date, v.symptoms, v.diagnosis, b.amount_required, p.full_name, p.patient_id
            FROM visits v
            JOIN patients p ON v.patient_id = p.patient_id
            LEFT JOIN bills b ON v.visit_id = b.visit_id
            WHERE v.visit_id = ?
        """, (visit_id,))
        if not visit:
            messagebox.showerror("Error", "Visit not found.")
            return
        _, visit_date, symptoms, diagnosis, amount, patient_name, patient_id = visit
        win = tk.Toplevel(self.root)
        win.title(f"Visit Details \u2013 {patient_name}")
        win.geometry("450x450")
        win.configure(bg=t["card_bg"])

        tk.Label(win, text=f"{patient_name}", font=("Segoe UI", 14, "bold"),
                 bg=t["card_bg"], fg=t["text_primary"]).pack(anchor="w", padx=15, pady=(15, 5))
        tk.Label(win, text=f"Visit Date: {visit_date}", bg=t["card_bg"], fg=t["text_secondary"]).pack(
            anchor="w", padx=15)
        tk.Label(win, text=f"Symptoms: {symptoms or 'N/A'}", bg=t["card_bg"], fg=t["text_secondary"],
                 wraplength=400, justify="left").pack(anchor="w", padx=15, pady=(5, 0))
        tk.Label(win, text=f"Diagnosis: {diagnosis or 'N/A'}", bg=t["card_bg"], fg=t["text_secondary"],
                 wraplength=400, justify="left").pack(anchor="w", padx=15, pady=(5, 0))
        amt_text = f"${amount:.2f}" if amount is not None else "N/A"
        tk.Label(win, text=f"Amount Required: {amt_text}", bg=t["card_bg"], fg="#2c5282", font=(
            "Segoe UI", 10, "bold")).pack(anchor="w", padx=15, pady=(5, 15))

        tk.Button(win, text="Upload Image for this Visit", bg="#38a169", fg="white",
                  font=("Segoe UI", 10, "bold"), bd=0, padx=15, pady=6, cursor="hand2",
                  command=lambda: self.upload_image(patient_id, visit_id, refresh_window=win)).pack(anchor="w", padx=15, pady=(0, 10))
        tk.Label(win, text="Files for this visit:", font=("Segoe UI", 11, "bold"),
                 bg=t["card_bg"], fg=t["text_primary"]).pack(anchor="w", padx=15, pady=(5, 5))

        files_frame = tk.Frame(win, bg=t["card_bg"])
        files_frame.pack(fill="both", expand=True, padx=15)

        def render_files():
            t = self.theme
            for w in files_frame.winfo_children():
                w.destroy()
            files = self.db.fetchall(
                "SELECT file_id, file_name, file_path FROM patient_files WHERE visit_id = ? ORDER BY uploaded_at DESC",
                (visit_id,)
            )
            if not files:
                tk.Label(files_frame, text="No files uploaded for this visit yet.",
                         bg=t["card_bg"], fg="#999").pack(anchor="w")
            for file_id, file_name, file_path in files:
                row = tk.Frame(files_frame, bg=t["card_bg"])
                row.pack(fill="x", pady=2)
                tk.Label(row, text=f"\U0001F4CE {file_name}", bg=t["card_bg"], fg="#333").pack(
                    side="left")
                tk.Button(row, text="Open", bg="#2c5282", fg="white", bd=0, padx=8, pady=1, cursor="hand2",
                          command=lambda p=file_path: self.open_file_external(p)).pack(side="left", padx=6)
                tk.Button(row, text="Delete", bg="#e53e3e", fg="white", bd=0, padx=8, pady=1, cursor="hand2",
                          command=lambda fid=file_id: (self.delete_patient_file(fid), render_files())).pack(side="left")

        render_files()
        win.render_files = render_files

    def upload_image(self, patient_id, visit_id, refresh_window=None):
        if patient_id is None:
            messagebox.showwarning("No Patient", "No patient selected.")
            return
        filepath = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[
                ("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"), ("All Files", "*.*")]
        )
        if not filepath:
            return

        patient_folder = os.path.join(UPLOADS_DIR, str(patient_id))
        os.makedirs(patient_folder, exist_ok=True)

        original_name = os.path.basename(filepath)
        unique_name = f"{int(time.time() * 1000)}_{original_name}"
        dest_path = os.path.join(patient_folder, unique_name)

        try:
            shutil.copy2(filepath, dest_path)
        except Exception as e:
            messagebox.showerror("Upload Failed", f"Could not copy file: {e}")
            return

        self.db.execute(
            "INSERT INTO patient_files (patient_id, visit_id, file_name, file_path) VALUES (?, ?, ?, ?)",
            (patient_id, visit_id, original_name, dest_path)
        )

        messagebox.showinfo("Success", "Image uploaded successfully.")

        # refresh whichever view needs it
        if refresh_window is not None and hasattr(refresh_window, "render_files"):
            refresh_window.render_files()
        if self.current_patient_id == patient_id:
            self.refresh_patient_detail()

    def delete_patient_file(self, file_id):
        row = self.db.fetchone(
            "SELECT file_path FROM patient_files WHERE file_id = ?", (file_id,))
        if not row:
            return
        if not messagebox.askyesno("Confirm Delete", "Delete this file? This cannot be undone."):
            return
        file_path = row[0]
        self.db.execute(
            "DELETE FROM patient_files WHERE file_id = ?", (file_id,))
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
        if self.current_patient_id is not None:
            self.refresh_patient_detail()

    def open_file_external(self, path):
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}")

    def add_doctor(self):
        name = self.doc_name.get().strip()
        if not name:
            messagebox.showwarning("Missing", "Please enter a name")
            return
        self.db.execute("INSERT INTO doctors (full_name, specialty, phone) VALUES (?, ?, ?)",
                        (name, self.doc_spec.get(), self.doc_phone.get()))
        self.doc_name.delete(0, tk.END)
        self.doc_spec.delete(0, tk.END)
        self.doc_phone.delete(0, tk.END)
        self.refresh_all_data()
        messagebox.showinfo("Success", "Doctor added!")

    def add_visit(self):
        patient = self.visit_patient.get()
        amount = self.visit_amount.get()
        if not patient or not amount:
            messagebox.showwarning(
                "Missing", "Please select a patient and enter an amount")
            return
        try:
            amount = float(amount)
        except ValueError:
            messagebox.showwarning("Invalid", "Amount must be a number")
            return

        patient_id = patient.split(" - ")[0]
        self.db.execute("INSERT INTO visits (patient_id, symptoms, diagnosis) VALUES (?, ?, ?)",
                        (patient_id, self.visit_symptoms.get(), self.visit_diagnosis.get()))
        visit_id = self.db.cursor.lastrowid
        self.db.execute(
            "INSERT INTO bills (visit_id, amount_required) VALUES (?, ?)", (visit_id, amount))

        self.visit_patient.set("")
        self.visit_symptoms.delete(0, tk.END)
        self.visit_diagnosis.delete(0, tk.END)
        self.visit_amount.delete(0, tk.END)
        self.refresh_all_data()
        messagebox.showinfo("Success", "Visit recorded!")

    def add_payment(self):
        visit = self.pay_visit.get()
        amount = self.pay_amount.get()
        if not visit or not amount:
            messagebox.showwarning(
                "Missing", "Please select a visit and enter an amount")
            return
        try:
            amount = float(amount)
        except ValueError:
            messagebox.showwarning("Invalid", "Amount must be a number")
            return
        bill_id = visit.split(" - ")[0]

        balance = self.db.fetchone("""
            SELECT b.amount_required - COALESCE(SUM(p.amount_paid), 0)
            FROM bills b LEFT JOIN payments p ON b.bill_id = p.bill_id
            WHERE b.bill_id = ? GROUP BY b.bill_id
        """, (bill_id,))[0]

        if amount > balance:
            messagebox.showwarning(
                "Overpayment", f"Balance is only ${balance:.2f}")
            return
        self.db.execute("INSERT INTO payments (bill_id, amount_paid, payment_method) VALUES (?, ?, ?)",
                        (bill_id, amount, self.pay_method.get()))
        self.pay_visit.set("")
        self.pay_amount.delete(0, tk.END)
        self.refresh_all_data()
        messagebox.showinfo("Success", "Payment recorded!")

    def refresh_all_data(self):
        self.refresh_doctors()
        self.refresh_patients()
        self.refresh_visits()
        self.refresh_payments()
        self.refresh_balances()
        self.refresh_dashboard()
        if self.current_patient_id is not None:
            self.refresh_patient_detail()

    def refresh_screen(self, name):
        if name == "dashboard":
            self.refresh_dashboard()
        elif name == "doctors":
            self.refresh_doctors()
        elif name == "patients":
            self.refresh_patients()
        elif name == "visits":
            self.refresh_visits()
        elif name == "payments":
            self.refresh_payments()
        elif name == "balances":
            self.refresh_balances()
        elif name == "patient_detail":
            self.refresh_patient_detail()

    def refresh_dashboard(self):
        counts = self.db.fetchone(
            "SELECT (SELECT COUNT(*) FROM doctors), (SELECT COUNT(*) FROM patients), "
            "(SELECT COALESCE(SUM(amount_paid), 0) FROM payments)"
        )
        outstanding = self.db.fetchone("""
            SELECT (SELECT COALESCE(SUM(amount_required), 0) FROM bills)
                 - (SELECT COALESCE(SUM(amount_paid), 0) FROM payments)
        """)[0]

        self.stat_cards["Total Doctors"].config(text=str(counts[0]))
        self.stat_cards["Total Patients"].config(text=str(counts[1]))
        self.stat_cards["Total Revenue"].config(text=f"${counts[2]:.0f}")
        self.stat_cards["Outstanding"].config(text=f"${outstanding:.0f}")

        for item in self.recent_tree.get_children():
            self.recent_tree.delete(item)
        rows = self.db.fetchall("""
            SELECT p.full_name, v.visit_date, b.amount_required,
                   COALESCE(SUM(pa.amount_paid), 0), b.amount_required - \
                            COALESCE(SUM(pa.amount_paid), 0)
            FROM visits v JOIN patients p ON v.patient_id = p.patient_id
            JOIN bills b ON v.visit_id = b.visit_id
            LEFT JOIN payments pa ON b.bill_id = pa.bill_id
            GROUP BY v.visit_id ORDER BY v.visit_date DESC LIMIT 10
        """)
        for r in rows:
            self.recent_tree.insert("", "end", values=(
                r[0], r[1], f"${r[2]:.2f}", f"${r[3]:.2f}", f"${r[4]:.2f}"))

    def refresh_doctors(self):
        for item in self.doctors_tree.get_children():
            self.doctors_tree.delete(item)
        term = self.doc_search.get().strip() if hasattr(self, "doc_search") else ""
        rows = self.db.fetchall("""
            SELECT d.doctor_id, d.full_name, d.specialty, d.phone, COUNT(p.patient_id)
            FROM doctors d LEFT JOIN patients p ON p.doctor_id = d.doctor_id
            WHERE d.full_name LIKE ? OR d.specialty LIKE ?
            GROUP BY d.doctor_id
        """, (f"%{term}%", f"%{term}%"))
        for row in rows:
            self.doctors_tree.insert("", "end", values=row)

    def refresh_patients(self):
        t = self.theme
        for w in self.patients_list_frame.winfo_children():
            w.destroy()

        term = self.pat_search.get().strip() if hasattr(self, "pat_search") else ""

        rows = self.db.fetchall("""
            SELECT p.patient_id, p.full_name, p.date_of_birth, p.phone, p.address,
                   d.full_name AS doctor_name,
                   COALESCE(bt.total_required, 0) - COALESCE(pt.total_paid, 0) AS balance
            FROM patients p
            LEFT JOIN doctors d ON p.doctor_id = d.doctor_id
            LEFT JOIN (
                SELECT v.patient_id, SUM(b.amount_required) AS total_required
                FROM visits v JOIN bills b ON v.visit_id = b.visit_id
                GROUP BY v.patient_id
            ) bt ON bt.patient_id = p.patient_id
            LEFT JOIN (
                SELECT v.patient_id, SUM(pay.amount_paid) AS total_paid
                FROM visits v
                JOIN bills b ON v.visit_id = b.visit_id
                JOIN payments pay ON pay.bill_id = b.bill_id
                GROUP BY v.patient_id
            ) pt ON pt.patient_id = p.patient_id
            WHERE p.full_name LIKE ?
            ORDER BY p.full_name
        """, (f"%{term}%",))

        if not rows:
            tk.Label(self.patients_list_frame, text="No patients found.",
                     bg=t["app_bg"], fg="#999").pack(pady=20)
        else:
            for patient_id, full_name, dob, phone, address, doctor_name, balance in rows:
                self.build_patient_card(self.patients_list_frame, patient_id, full_name,
                                        dob, phone, address, doctor_name, balance)

    def refresh_payments(self):
        for item in self.payments_tree.get_children():
            self.payments_tree.delete(item)
        rows = self.db.fetchall("""
            SELECT pay.payment_id, p.full_name, v.visit_date, pay.amount_paid, pay.payment_method, pay.payment_date
            FROM payments pay
            JOIN bills b ON pay.bill_id = b.bill_id
            JOIN visits v ON b.visit_id = v.visit_id
            JOIN patients p ON v.patient_id = p.patient_id
            ORDER BY pay.payment_date DESC
        """)
        for r in rows:
            self.payments_tree.insert("", "end", values=(
                r[0], r[1], r[2], f"${r[3]:.2f}", r[4], r[5]))

        visit_rows = self.db.fetchall("""
            SELECT b.bill_id, p.full_name, v.visit_date,
                   b.amount_required - COALESCE(SUM(pa.amount_paid), 0) AS balance
            FROM bills b
            JOIN visits v ON b.visit_id = v.visit_id
            JOIN patients p ON v.patient_id = p.patient_id
            LEFT JOIN payments pa ON b.bill_id = pa.bill_id
            GROUP BY b.bill_id
            HAVING balance > 0
        """)
        self.pay_visit["values"] = [
            f"{r[0]} - {r[1]} - {r[2]} - ${r[3]:.2f}" for r in visit_rows]

    def refresh_balances(self):
        for item in self.balances_tree.get_children():
            self.balances_tree.delete(item)
        rows = self.db.fetchall("""
            SELECT p.full_name,
                   COALESCE(bt.total_required, 0) AS total_required,
                   COALESCE(pt.total_paid, 0) AS total_paid,
                   COALESCE(bt.total_required, 0) - COALESCE(pt.total_paid, 0) AS balance,
                   d.full_name
            FROM patients p
            LEFT JOIN doctors d ON p.doctor_id = d.doctor_id
            LEFT JOIN (
                SELECT v.patient_id, SUM(b.amount_required) AS total_required
                FROM visits v JOIN bills b ON v.visit_id = b.visit_id
                GROUP BY v.patient_id
            ) bt ON bt.patient_id = p.patient_id
            LEFT JOIN (
                SELECT v.patient_id, SUM(pay.amount_paid) AS total_paid
                FROM visits v
                JOIN bills b ON v.visit_id = b.visit_id
                JOIN payments pay ON pay.bill_id = b.bill_id
                GROUP BY v.patient_id
            ) pt ON pt.patient_id = p.patient_id
            WHERE COALESCE(bt.total_required, 0) > 0
            ORDER BY balance DESC
        """)
        for r in rows:
            self.balances_tree.insert("", "end", values=(r[0], f"${r[1]:.2f}", f"${r[2]:.2f}",
                                                         f"${r[3]:.2f}", r[4] or "None"))

    def refresh_visits(self):
        for item in self.visits_tree.get_children():
            self.visits_tree.delete(item)

        rows = self.db.fetchall("""
            SELECT v.visit_id,
                   p.full_name,
                   v.visit_date,
                   v.symptoms,
                   v.diagnosis,
                   b.amount_required
            FROM visits v
            JOIN patients p ON v.patient_id = p.patient_id
            JOIN bills b ON v.visit_id = b.visit_id
            ORDER BY v.visit_date DESC
        """)

        for row in rows:
            self.visits_tree.insert("", "end", values=(
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
                f"${row[5]:.2f}"
            ))

        patients = self.db.fetchall("""
            SELECT patient_id, full_name
            FROM patients
            ORDER BY full_name
        """)

        self.visit_patient["values"] = [
            f"{p[0]} - {p[1]}" for p in patients
        ]

    def delete_doctor(self):
        selected = self.doctors_tree.selection()

        if not selected:
            messagebox.showwarning("No Selection", "Please select a doctor.")
            return

        doctor_id = self.doctors_tree.item(selected[0])["values"][0]

        patients = self.db.fetchone(
            "SELECT COUNT(*) FROM patients WHERE doctor_id = ?",
            (doctor_id,)
        )[0]

        if patients > 0:
            messagebox.showwarning(
                "Cannot Delete",
                "This doctor still has patients assigned."
            )
            return

        if not messagebox.askyesno(
            "Confirm Delete",
            "Are you sure you want to delete this doctor?"
        ):
            return

        self.db.execute(
            "DELETE FROM doctors WHERE doctor_id = ?",
            (doctor_id,)
        )

        self.refresh_all_data()
        messagebox.showinfo("Success", "Doctor deleted successfully.")

    def delete_current_patient(self):
        if self.current_patient_id is None:
            return
        patient_id = self.current_patient_id

        if not messagebox.askyesno(
            "Confirm Delete",
            "Delete this patient and all associated visits, bills, payments, and files?"
        ):
            return

        visits = self.db.fetchall(
            "SELECT visit_id FROM visits WHERE patient_id = ?",
            (patient_id,)
        )

        for visit in visits:
            visit_id = visit[0]

            bills = self.db.fetchall(
                "SELECT bill_id FROM bills WHERE visit_id = ?",
                (visit_id,)
            )

            for bill in bills:
                self.db.execute(
                    "DELETE FROM payments WHERE bill_id = ?",
                    (bill[0],)
                )

            self.db.execute(
                "DELETE FROM bills WHERE visit_id = ?",
                (visit_id,)
            )

        files = self.db.fetchall(
            "SELECT file_id, file_path FROM patient_files WHERE patient_id = ?",
            (patient_id,)
        )
        for file_id, file_path in files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
        self.db.execute(
            "DELETE FROM patient_files WHERE patient_id = ?", (patient_id,))

        self.db.execute(
            "DELETE FROM visits WHERE patient_id = ?",
            (patient_id,)
        )

        self.db.execute(
            "DELETE FROM patients WHERE patient_id = ?",
            (patient_id,)
        )

        self.current_patient_id = None
        self.show_screen("patients")
        self.refresh_all_data()
        messagebox.showinfo("Success", "Patient deleted successfully.")

    def delete_visit(self):
        selected = self.visits_tree.selection()

        if not selected:
            messagebox.showwarning("No Selection", "Please select a visit.")
            return

        visit_id = self.visits_tree.item(selected[0])["values"][0]

        if not messagebox.askyesno(
            "Confirm Delete",
            "Are you sure you want to delete this visit?"
        ):
            return

        bills = self.db.fetchall(
            "SELECT bill_id FROM bills WHERE visit_id = ?",
            (visit_id,)
        )

        for bill in bills:
            self.db.execute(
                "DELETE FROM payments WHERE bill_id = ?",
                (bill[0],)
            )

        self.db.execute(
            "DELETE FROM bills WHERE visit_id = ?",
            (visit_id,)
        )

        files = self.db.fetchall(
            "SELECT file_id, file_path FROM patient_files WHERE visit_id = ?", (visit_id,))
        for file_id, file_path in files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
        self.db.execute(
            "DELETE FROM patient_files WHERE visit_id = ?", (visit_id,))

        self.db.execute(
            "DELETE FROM visits WHERE visit_id = ?",
            (visit_id,)
        )

        self.refresh_all_data()
        messagebox.showinfo("Success", "Visit deleted successfully.")

    def delete_payment(self):
        selected = self.payments_tree.selection()

        if not selected:
            messagebox.showwarning("No Selection", "Please select a payment.")
            return

        payment_id = self.payments_tree.item(selected[0])["values"][0]

        if not messagebox.askyesno(
            "Confirm Delete",
            "Are you sure you want to delete this payment?"
        ):
            return

        self.db.execute(
            "DELETE FROM payments WHERE payment_id = ?",
            (payment_id,)
        )

        self.refresh_all_data()
        messagebox.showinfo("Success", "Payment deleted successfully.")

    def export_balances(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            title="Export Balances"
        )

        if not filename:
            return

        with open(filename, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)

            writer.writerow([
                "Patient",
                "Total Required",
                "Total Paid",
                "Balance",
                "Doctor"
            ])

            for item in self.balances_tree.get_children():
                writer.writerow(self.balances_tree.item(item)["values"])

        messagebox.showinfo(
            "Success",
            "Balances exported successfully."
        )


if __name__ == "__main__":
    root = tk.Tk()
    app = ClinicApp(root)
    root.mainloop()
