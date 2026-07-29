import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3


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
        self.root.geometry("1100x700")
        self.root.configure(bg="#eef2f5")
        self.root.minsize(900, 600)

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("Sidebar.TButton", font=("Segoe UI", 11), foreground="white",
                              background="#1e3a5f", padding=10)
        self.style.map("Sidebar.TButton", background=[("active", "#2c5282")])
        self.style.configure("Card.TFrame", background="white")
        self.style.configure("Card.TLabel", background="white", font=("Segoe UI", 14, "bold"),
                              foreground="#1e3a5f")
        self.style.configure("Action.TButton", font=("Segoe UI", 10, "bold"))

        self.build_sidebar()
        self.build_content_area()
        self.build_all_screens()

        self.show_screen("dashboard")
        self.refresh_all_data()

    def build_sidebar(self):
        self.sidebar = tk.Frame(self.root, bg="#1e3a5f", width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        logo = tk.Label(self.sidebar, text="ClinicPro", font=("Segoe UI", 18, "bold"),
                         bg="#1e3a5f", fg="white", pady=20)
        logo.pack(fill="x")

        buttons = [
            ("Dashboard", "dashboard"),
            ("Doctors", "doctors"),
            ("Patients", "patients"),
            ("Visits", "visits"),
            ("Payments", "payments"),
            ("Balances", "balances"),
        ]

        for text, screen in buttons:
            btn = tk.Button(self.sidebar, text=text, font=("Segoe UI", 11), bg="#1e3a5f", fg="white",
                             activebackground="#2c5282", activeforeground="white", bd=0, cursor="hand2",
                             padx=20, pady=12, anchor="w", command=lambda s=screen: self.show_screen(s))
            btn.pack(fill="x", padx=0, pady=2)

    def build_content_area(self):
        self.content = tk.Frame(self.root, bg="#eef2f5")
        self.content.pack(side="right", fill="both", expand=True, padx=20, pady=20)

        self.header = tk.Label(self.content, text="Dashboard", font=("Segoe UI", 20, "bold"),
                                bg="#eef2f5", fg="#1e3a5f")
        self.header.pack(anchor="w", pady=(0, 20))

        self.screen_container = tk.Frame(self.content, bg="#eef2f5")
        self.screen_container.pack(fill="both", expand=True)

    def show_screen(self, name):
        self.header.config(text=name.title())
        frame = self.screens[name]
        frame.tkraise()
        self.refresh_screen(name)

    def build_all_screens(self):
        self.screens = {}
        for name in ["dashboard", "doctors", "patients", "visits", "payments", "balances"]:
            frame = tk.Frame(self.screen_container, bg="#eef2f5")
            frame.place(relwidth=1, relheight=1)
            self.screens[name] = frame
            getattr(self, f"build_{name}_screen")(frame)

    def build_dashboard_screen(self, parent):
        cards_frame = tk.Frame(parent, bg="#eef2f5")
        cards_frame.pack(fill="x", pady=(0, 20))

        self.stat_cards = {}
        stats = [("Total Doctors", "#2c5282"), ("Total Patients", "#38a169"),
                 ("Total Revenue", "#d69e2e"), ("Outstanding", "#e53e3e")]

        for title, color in stats:
            card = tk.Frame(cards_frame, bg="white", bd=1, relief="solid",
                             highlightbackground="#ddd", highlightthickness=1)
            card.pack(side="left", fill="both", expand=True, padx=5)
            tk.Label(card, text="0", font=("Segoe UI", 28, "bold"), bg="white", fg=color).pack(pady=(15, 5))
            tk.Label(card, text=title, font=("Segoe UI", 11), bg="white", fg="#666").pack(pady=(0, 15))
            self.stat_cards[title] = card.winfo_children()[0]

        recent_frame = tk.Frame(parent, bg="white", bd=1, relief="solid",
                                 highlightbackground="#ddd", highlightthickness=1)
        recent_frame.pack(fill="both", expand=True)
        tk.Label(recent_frame, text="Recent Visits", font=("Segoe UI", 14, "bold"),
                 bg="white", fg="#1e3a5f").pack(anchor="w", padx=15, pady=15)

        cols = ("Patient", "Date", "Amount", "Paid", "Balance")
        self.recent_tree = ttk.Treeview(recent_frame, columns=cols, show="headings", height=8)
        for c in cols:
            self.recent_tree.heading(c, text=c)
            self.recent_tree.column(c, width=150)
        self.recent_tree.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    def build_doctors_screen(self, parent):
        form = tk.LabelFrame(parent, text="Add Doctor", bg="white", font=("Segoe UI", 11, "bold"),
                              fg="#1e3a5f", padx=15, pady=15)
        form.pack(fill="x", pady=(0, 15))

        tk.Label(form, text="Full Name:", bg="white").grid(row=0, column=0, sticky="w")
        self.doc_name = tk.Entry(form, width=30)
        self.doc_name.grid(row=0, column=1, padx=5, pady=3)

        tk.Label(form, text="Specialty:", bg="white").grid(row=1, column=0, sticky="w")
        self.doc_spec = tk.Entry(form, width=30)
        self.doc_spec.grid(row=1, column=1, padx=5, pady=3)

        tk.Label(form, text="Phone:", bg="white").grid(row=2, column=0, sticky="w")
        self.doc_phone = tk.Entry(form, width=30)
        self.doc_phone.grid(row=2, column=1, padx=5, pady=3)

        tk.Button(form, text="Add Doctor", bg="#38a169", fg="white", font=("Segoe UI", 10, "bold"), bd=0,
                  padx=20, pady=5, cursor="hand2", command=self.add_doctor).grid(row=3, column=1, pady=10, sticky="e")

        list_frame = tk.Frame(parent, bg="white", bd=1, relief="solid")
        list_frame.pack(fill="both", expand=True)

        cols = ("ID", "Name", "Specialty", "Phone")
        self.doctors_tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=12)
        for c in cols:
            self.doctors_tree.heading(c, text=c)
            self.doctors_tree.column(c, width=200)
        self.doctors_tree.pack(fill="both", expand=True, padx=10, pady=10)

    def build_patients_screen(self, parent):
        form = tk.LabelFrame(parent, text="Add Patient", bg="white", font=("Segoe UI", 11, "bold"),
                              fg="#1e3a5f", padx=15, pady=15)
        form.pack(fill="x", pady=(0, 15))

        fields = [("Full Name:", "pat_name"), ("Date of Birth:", "pat_dob"),
                  ("Phone:", "pat_phone"), ("Address:", "pat_address")]
        self.pat_entries = {}

        for i, (label, attr) in enumerate(fields):
            tk.Label(form, text=label, bg="white").grid(row=i, column=0, sticky="w")
            ent = tk.Entry(form, width=30)
            ent.grid(row=i, column=1, padx=5, pady=3)
            self.pat_entries[attr] = ent

        tk.Label(form, text="Doctor:", bg="white").grid(row=4, column=0, sticky="w")
        self.pat_doctor = ttk.Combobox(form, width=28, state="readonly")
        self.pat_doctor.grid(row=4, column=1, padx=5, pady=3)

        tk.Button(form, text="Add Patient", bg="#38a169", fg="white", font=("Segoe UI", 10, "bold"), bd=0,
                  padx=20, pady=5, cursor="hand2", command=self.add_patient).grid(row=5, column=1, pady=10, sticky="e")

        list_frame = tk.Frame(parent, bg="white", bd=1, relief="solid")
        list_frame.pack(fill="both", expand=True)

        cols = ("ID", "Name", "DOB", "Phone", "Doctor")
        self.patients_tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=12)
        for c in cols:
            self.patients_tree.heading(c, text=c)
            self.patients_tree.column(c, width=150)
        self.patients_tree.pack(fill="both", expand=True, padx=10, pady=10)

    def build_visits_screen(self, parent):
        form = tk.LabelFrame(parent, text="Record Visit", bg="white", font=("Segoe UI", 11, "bold"),
                              fg="#1e3a5f", padx=15, pady=15)
        form.pack(fill="x", pady=(0, 15))

        tk.Label(form, text="Patient:", bg="white").grid(row=0, column=0, sticky="w")
        self.visit_patient = ttk.Combobox(form, width=38, state="readonly")
        self.visit_patient.grid(row=0, column=1, padx=5, pady=3)

        tk.Label(form, text="Symptoms:", bg="white").grid(row=1, column=0, sticky="w")
        self.visit_symptoms = tk.Entry(form, width=40)
        self.visit_symptoms.grid(row=1, column=1, padx=5, pady=3)

        tk.Label(form, text="Diagnosis:", bg="white").grid(row=2, column=0, sticky="w")
        self.visit_diagnosis = tk.Entry(form, width=40)
        self.visit_diagnosis.grid(row=2, column=1, padx=5, pady=3)

        tk.Label(form, text="Amount Required ($):", bg="white").grid(row=3, column=0, sticky="w")
        self.visit_amount = tk.Entry(form, width=40)
        self.visit_amount.grid(row=3, column=1, padx=5, pady=3)

        tk.Button(form, text="Record Visit", bg="#38a169", fg="white", font=("Segoe UI", 10, "bold"), bd=0,
                  padx=20, pady=5, cursor="hand2", command=self.add_visit).grid(row=4, column=1, pady=10, sticky="e")

        list_frame = tk.Frame(parent, bg="white", bd=1, relief="solid")
        list_frame.pack(fill="both", expand=True)

        cols = ("ID", "Patient", "Date", "Symptoms", "Diagnosis", "Amount")
        self.visits_tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=12)
        for c in cols:
            self.visits_tree.heading(c, text=c)
            self.visits_tree.column(c, width=140)
        self.visits_tree.pack(fill="both", expand=True, padx=10, pady=10)

    def build_payments_screen(self, parent):
        form = tk.LabelFrame(parent, text="Record Payment", bg="white", font=("Segoe UI", 11, "bold"),
                              fg="#1e3a5f", padx=15, pady=15)
        form.pack(fill="x", pady=(0, 15))

        tk.Label(form, text="Visit (Patient - Date - Balance):", bg="white").grid(row=0, column=0, sticky="w")
        self.pay_visit = ttk.Combobox(form, width=50, state="readonly")
        self.pay_visit.grid(row=0, column=1, padx=5, pady=3)

        tk.Label(form, text="Amount Paid ($):", bg="white").grid(row=1, column=0, sticky="w")
        self.pay_amount = tk.Entry(form, width=50)
        self.pay_amount.grid(row=1, column=1, padx=5, pady=3)

        tk.Label(form, text="Method:", bg="white").grid(row=2, column=0, sticky="w")
        self.pay_method = ttk.Combobox(form, values=["Cash", "Card", "Insurance", "Bank Transfer"],
                                        width=48, state="readonly")
        self.pay_method.set("Cash")
        self.pay_method.grid(row=2, column=1, padx=5, pady=3)

        tk.Button(form, text="Record Payment", bg="#38a169", fg="white", font=("Segoe UI", 10, "bold"), bd=0,
                  padx=20, pady=5, cursor="hand2", command=self.add_payment).grid(row=3, column=1, pady=10, sticky="e")

        list_frame = tk.Frame(parent, bg="white", bd=1, relief="solid")
        list_frame.pack(fill="both", expand=True)

        cols = ("ID", "Patient", "Visit Date", "Amount Paid", "Method", "Payment Date")
        self.payments_tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=12)
        for c in cols:
            self.payments_tree.heading(c, text=c)
            self.payments_tree.column(c, width=150)
        self.payments_tree.pack(fill="both", expand=True, padx=10, pady=10)

    def build_balances_screen(self, parent):
        list_frame = tk.Frame(parent, bg="white", bd=1, relief="solid")
        list_frame.pack(fill="both", expand=True)

        tk.Label(list_frame, text="Outstanding Balances", font=("Segoe UI", 14, "bold"),
                 bg="white", fg="#1e3a5f").pack(anchor="w", padx=15, pady=15)

        cols = ("Patient", "Total Required", "Total Paid", "Balance", "Doctor")
        self.balances_tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=18)
        for c in cols:
            self.balances_tree.heading(c, text=c)
            self.balances_tree.column(c, width=170)
        self.balances_tree.pack(fill="both", expand=True, padx=15, pady=(0, 15))

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

    def add_patient(self):
        name = self.pat_entries["pat_name"].get().strip()
        if not name:
            messagebox.showwarning("Missing", "Please enter a name")
            return
        doctor_id = self.pat_doctor.get().split(" - ")[0] if self.pat_doctor.get() else None
        self.db.execute(
            "INSERT INTO patients (full_name, date_of_birth, phone, address, doctor_id) VALUES (?, ?, ?, ?, ?)",
            (name, self.pat_entries["pat_dob"].get(), self.pat_entries["pat_phone"].get(),
             self.pat_entries["pat_address"].get(), doctor_id)
        )
        for ent in self.pat_entries.values():
            ent.delete(0, tk.END)
        self.refresh_all_data()
        messagebox.showinfo("Success", "Patient added!")

    def add_visit(self):
        patient = self.visit_patient.get()
        amount = self.visit_amount.get()
        if not patient or not amount:
            messagebox.showwarning("Missing", "Please select a patient and enter an amount")
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
        self.db.execute("INSERT INTO bills (visit_id, amount_required) VALUES (?, ?)", (visit_id, amount))

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
            messagebox.showwarning("Missing", "Please select a visit and enter an amount")
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
            messagebox.showwarning("Overpayment", f"Balance is only ${balance:.2f}")
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

    def refresh_dashboard(self):
        counts = self.db.fetchone(
            "SELECT (SELECT COUNT(*) FROM doctors), (SELECT COUNT(*) FROM patients), "
            "(SELECT COALESCE(SUM(amount_paid), 0) FROM payments)"
        )
        outstanding = self.db.fetchone("""
            SELECT COALESCE(SUM(b.amount_required), 0) - COALESCE(SUM(p.amount_paid), 0)
            FROM bills b LEFT JOIN payments p ON b.bill_id = p.bill_id
        """)[0]

        self.stat_cards["Total Doctors"].config(text=str(counts[0]))
        self.stat_cards["Total Patients"].config(text=str(counts[1]))
        self.stat_cards["Total Revenue"].config(text=f"${counts[2]:.0f}")
        self.stat_cards["Outstanding"].config(text=f"${outstanding:.0f}")

        for item in self.recent_tree.get_children():
            self.recent_tree.delete(item)
        rows = self.db.fetchall("""
            SELECT p.full_name, v.visit_date, b.amount_required,
                   COALESCE(SUM(pa.amount_paid), 0), b.amount_required - COALESCE(SUM(pa.amount_paid), 0)
            FROM visits v JOIN patients p ON v.patient_id = p.patient_id
            JOIN bills b ON v.visit_id = b.visit_id
            LEFT JOIN payments pa ON b.bill_id = pa.bill_id
            GROUP BY v.visit_id ORDER BY v.visit_date DESC LIMIT 10
        """)
        for r in rows:
            self.recent_tree.insert("", "end", values=(r[0], r[1], f"${r[2]:.2f}", f"${r[3]:.2f}", f"${r[4]:.2f}"))

    def refresh_doctors(self):
        for item in self.doctors_tree.get_children():
            self.doctors_tree.delete(item)
        for row in self.db.fetchall("SELECT * FROM doctors"):
            self.doctors_tree.insert("", "end", values=row)

    def refresh_patients(self):
        for item in self.patients_tree.get_children():
            self.patients_tree.delete(item)
        doctors = {str(d[0]): d[1] for d in self.db.fetchall("SELECT doctor_id, full_name FROM doctors")}
        for row in self.db.fetchall("SELECT patient_id, full_name, date_of_birth, phone, doctor_id FROM patients"):
            doc_name = doctors.get(str(row[4]), "None")
            self.patients_tree.insert("", "end", values=(row[0], row[1], row[2], row[3], doc_name))

        self.pat_doctor["values"] = [
            f"{d[0]} - {d[1]}" for d in self.db.fetchall("SELECT doctor_id, full_name FROM doctors")
        ]

    def refresh_visits(self):
        for item in self.visits_tree.get_children():
            self.visits_tree.delete(item)
        rows = self.db.fetchall("""
            SELECT v.visit_id, p.full_name, v.visit_date, v.symptoms, v.diagnosis, b.amount_required
            FROM visits v JOIN patients p ON v.patient_id = p.patient_id
            JOIN bills b ON v.visit_id = b.visit_id ORDER BY v.visit_date DESC
        """)
        for r in rows:
            self.visits_tree.insert("", "end", values=(r[0], r[1], r[2], r[3], r[4], f"${r[5]:.2f}"))
        self.visit_patient["values"] = [
            f"{p[0]} - {p[1]}" for p in self.db.fetchall("SELECT patient_id, full_name FROM patients")
        ]

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
            self.payments_tree.insert("", "end", values=(r[0], r[1], r[2], f"${r[3]:.2f}", r[4], r[5]))

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
        self.pay_visit["values"] = [f"{r[0]} - {r[1]} - {r[2]} - ${r[3]:.2f}" for r in visit_rows]

    def refresh_balances(self):
        for item in self.balances_tree.get_children():
            self.balances_tree.delete(item)
        rows = self.db.fetchall("""
            SELECT p.full_name, COALESCE(SUM(b.amount_required), 0), COALESCE(SUM(pa.amount_paid), 0),
                   COALESCE(SUM(b.amount_required), 0) - COALESCE(SUM(pa.amount_paid), 0), d.full_name
            FROM patients p
            LEFT JOIN visits v ON p.patient_id = v.patient_id
            LEFT JOIN bills b ON v.visit_id = b.visit_id
            LEFT JOIN payments pa ON b.bill_id = pa.bill_id
            LEFT JOIN doctors d ON p.doctor_id = d.doctor_id
            GROUP BY p.patient_id HAVING COALESCE(SUM(b.amount_required), 0) > 0
            ORDER BY (COALESCE(SUM(b.amount_required), 0) - COALESCE(SUM(pa.amount_paid), 0)) DESC
        """)
        for r in rows:
            self.balances_tree.insert("", "end", values=(r[0], f"${r[1]:.2f}", f"${r[2]:.2f}", f"${r[3]:.2f}", r[4] or "None"))


if __name__ == "__main__":
    root = tk.Tk()
    app = ClinicApp(root)
    root.mainloop()