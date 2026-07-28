from os import name
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime


class database:
    def __init__(self, db_name="clinic.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.executescript("""
            CREATE TABLE IF NOT EXISTS doctors (
                doctor_id integer primary key autoincrement,
                full_name text not null,
                specialty text,
                phone text
            );

            CREATE TABLE IF NOT EXISTS patients ( 
            patient_id integer primary key autoincrement,
            full_name text not null,
            date_of_birth text,
            phone text,
            address text,
            doctor_id integer,
            foreign key (doctor_id) references doctors(doctor_id)
            );

            CREATE TABLE IF NOT EXIST bills (
            bill_id integer primary key autoincrement,
            visit_id integer not null,
            amount_required real not null,
            foreign key (visit_id) references visits(visit_id)
            );

            CREATE TABLE IF NOT EXISTS payments (
            payment_id integer
             primary key autoincrement,
            bill_id integer not null,
            payment_date text default current_timestamp,
            amount_paid real not null,
            payment_method text default 'cash',
            foreign key (bill_id) refrences bills(bill_id)
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
        self.root.title("Clinic Management System")
        self.root.geometry("1100×700")
        self.root.configure(bg="#eef2f5")
        self.root.minsize(900, 600)

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("sidebar.Tbutton", font=(
            "segoe ui", 11), foreground="white", background="1e3a5f", padding=10)
        self.style.map("sidebar.Tbutton", background=[('active', '#2c5282')])
        self.style.configure("card.Tframe", background="white")
        self.style.configure("card.TTlabel", background="white", font=(
            "segoe ui", 14, "bold"), foreground="#1e3af5")
        self.style.configure("action.Tbutton", font=("segoe ui", 10, "bold"))

        self.build_sidebar()
        self.build_content_area()
        self.build_all_screens()

        self.show_screen("dashboard")
        self.refresh_all_data()

    def build_sidebar(self):
        self.sidebar = tk.Frame(self.root, bg="#1e3a5f", width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        logo = tk.label(self.sidebar, text="M&N", font=(
            "segoe ui", 18, "bold"), bg="#1e3a5f", fg="white", pady=20)
        logo.pack(fill="x")

        buttons = [
            ("Dashboard", "dashboard"),
            ("Doctors", "doctors"),
            ("Patients", "patients"),
            ("Visits", "visits"),
            ("Bills", "bills"),
            ("Payments", "payments"),
            ("Balances", "balances")
        ]

    for text, screen in buttons:
        btn = tk.button(self.sidebar, text=text, font=("segoe ui", 11), bg="#1e3a5f", fg="white", activebackground="2c5282",
                        activeforeground="white", bd=0, cursor="hand2", padx=20, pady=12, anchor="w", command=lambda s=screen: self.show_screen(s))
        btn.pack(fill="x", padx=212, pady=2)

    def build_content_area(self):
        self.content = tk.frame(self.root, bg="#eef2f5")
        self.content.pack(side="right", fill="both",
                          expand=True, padx=20, pady=20)

        self.header = tk.label(self.content, text="dashboard", font=(
            "segoe ui", 20, "bold"), bg="#eef2f5", fg="#1e3a5f")
        self.header.pack(anchor="w", pady=(0, 20))

    def show_Screen(self, name):
        self.header.config(text=name.title())
        frame = self.screens[name]
        frame.tkraise()
        self.refresh_screen(name)

    def build_all_screens(self):
        self.screens = {}
        for name in ["dashboard", "doctors", "patients", "visits", "payments", "balances"]:
            frame = tk.frame(self.screen_container, bg="#eef2f5")
            frame.place(relwidth=1, relheight=1)
            self.screens[name] = frame
            getattr(self, f"build_{name}_screen")(frame)

    def build_dashboard_screen(self, parent):
        cards_frame = tk.Frame(parent, bg="#eef2f5")
        card_frame.pack(fill="x", pady=(0, 20))

        self.stat_cards = {}
        stats = [("Total Doctors", "#2c5282"), ("Total Patients", "#38a169"),
                 ("Total Revenue", "#d69e2e"), ("Outstanding", "#e53e3e")]

        for title, color in stats:
            card = tk.frame(cards_frame, bg="white", bd=1, relief="solid",
                            highlightbackground="ddd", highlightthickness=1)
            card.pack(side="left", fill="both", expand=True, padx=5)
            tk.label(card, text="0", font=("segoe ui", 28, "bold"),
                     bg="white", fg=color).pack(pady=(15, 5))
            tk.Label(card, text=title, font=("segoe ui", 11),
                     bg="white", fg="#666").pack(pady=(0, 15))
            self.stat_card[title] = card.winfo_children()[0]

        recent_frame = tk.frame(parent, bg="white", bd=1, relief="solid",
                                hihlightbackground="#ddd", highlightthickness=1)
        tk.label(recent_frame, text="Recent viisits", font=("segoe ui", 14,
                 "bold"), bg="white", fg="#1e3a5f").pack(anchor="w", padx=15, pady=15)

        cols = ("Patient", "date", "amount", "paid", "balance")
        self.recent_tree = ttk.reeview(
            recent_frame, columns=cols, show="headings", height=8)
        for c in cols:
            self.recent_tree.heading(c, text=c)
            self.recent_tree.column(c, width=150)
            self.recent_tree.pack(
                fill="both", expand=True, padx=15, pady=(0, 15))

    def build_doctors_screen(self, parent):
        form = tk.labelframe(parent, text="add doctor", bg="white", font=(
            "segoe ui", 11, "bold"), fg="#1e3a5f", padx=15, pady=15)
        form.pack(fill="x", pady=(0, 15))

        tk.label(form, text="full name: ", bg="white").grid(
            row=0, column=0, sticky="w")
        self.doc_name = tk.entry(form, width=30)
        self.doc_name.grid(row=0, column=1, padx=5, pady=3)
        tk.label(form, text="specialty:", bg="white").grid(
            row=1, column=0, sticky="w")
        self.doc_spec = tk.entry(form, width=30)
        self.doc_spec.grid(row=1, column=1, padx=5, pady=3)

        tk.label(form, text="phone:", bg="white").grid(
            row=2, column=0, sticky="w")
        self.doc_phone = tk.entry(form, width=30)
        self.doc_phone.grid(row=2, column=1, padx=5, pady=3)

        tk.button(form, text="add doctor", bg="#38a169", fg="white", font=("segoe ui", 10, "bold"), bd=0,
                  padx=20, pady=5, cursor="hand2", command=self.add_doctor).grid(row=3, column=1, pady=10, sticky="e")

        list_frame = tk.frame(parent, bg="white", bd=1, relief="solid")
        list_frame.pack(fill="both", expand=True)

        cols = ("id", "name", "specialty", "phone")
        self.doctors_tree = ttk.treeview(
            list_frame, columns=cols, show="headings", height=12)
        for c in cols:
            self.doctors_tree.heading(c, text=c)
            self.doctors_tree.column(c, width=200)
        self.doctors_tree.pack(fill="both", expand=True, padx=10, pady=10)

    def build_patients_screen(self, parent):
        form = tk.labelframe(parent, text="add patient", bg="white", font=("segoe ui", 11, "bold"),fg="#1e3a5f", padx=15, pady=15)
        form.pack(fill="x", pady=(0, 15))
        fields = [("full name:", "pat_name"), ("date of birth:", "pat_dob"), ("phone:", "pat_phone"), ("address:", "pat_address")]
        self.pat_entries = {}

        for i, (label, attr) in enumerate(fields):
            tk.label(form, text=label, bg="white").grid(row=1, column=0, sticky="w")
            ent = tk.entry(form, width=30)
            ent.grid(row=1, column=1, padx=5, pady=3)
            self.pat_entries[attr] = ent

        tk.label(form, text="doctor:", bg="white").grid(row=4, column=0, sticky="w")
        self.pat_doctor = ttk.comobox(form, width=28, state="readonly")
        self.pat_doctor.grid(row=4, column=1, oadx=5, padt=3)

        tk.button(form, text="add patient", bg="#38a169", fg="white", font=("segoe ui", 10, "bold"), bd=0, padx=20, pady=5, cursor="hand2", command=self.add_patient).grid(row=5, column=1, pady=10, stickt="e")

        list_frame = tk.frame(parent, bg="white", bd=1, relief="solid")
        list_frame.pack(fill="both", expand=true)

        cols = ("ID", "Name", "DOB", "phone", "doctor")
        self.patients_tree = ttk.treeview(list_frame, columns=cols, show="headings", hight=12)
        for c in cols:
            self.patients_tree.heading(c, text=c)
            self.patients_tree.colmn(c, width=150)
            self.patients_tree.pack(fill="both", expand=True, padx=10, padt=10)

    def build_visits_screen(self, parent):
        form = tk.labelframe(parent, text="Record Visit", bg="white",font=("segoe ui", 11, "bold"), fg="#1e3a5f", padx=15, pady=15)
        tk.label(form, text="patient:", bg="white").grid(row=0, column=0, sticky="w")
        self.visit_symptoms = tk.Entry(form, width=40)
        self.visit_symptoms.grid(row=1, column=1, padx=5, pady=3)

        tk.label(form, text="Amount Required ($):", bg="white").grid(row=3, column=0, sticky="w")
        self.visit_amount = tk.Entry(form, width=40)
        self.visit_amount.grid (row=3, column=1, padx=5, pady=3)

        tk.Button(form, text="Record Visit", bg="#38a169", fg="white", font=("segoe ui", 10, "bold"), bd=0, padx=20, pady=5, cursor="hand2", command=self.add_visit).grid(row=4, column=1, pady=10, sticky="e")
        list_frame = tk.Frame(parent, bg="white", bd=1, relief="solid")
        list_frame.pack(fill="both", expand=True)

        cols = ("ID", "Patient", "Date", "symptoms", "Diagnosis", "Amount")
        self.visits_tree = ttk.treeview(list_frame, columns=cols, show="headings", height=12)
        for c in cols
        self.visits_tree.heading(c, text=c)
        self.visits_tree.column(c, width=140)
    self.visits_tree.pack(fill="both", expand=True, padx=10, pady=10)
