from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivymd.uix.list import OneLineListItem, ThreeLineListItem
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivy.metrics import dp
import sqlite3
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request

# Database setup
DB_PATH = 'school_fee.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS student (
        id INTEGER PRIMARY KEY,
        class_name TEXT NOT NULL,
        student_name TEXT NOT NULL,
        father_name TEXT,
        parent_phone TEXT,
        monthly_fee INTEGER NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS payment (
        id INTEGER PRIMARY KEY,
        student_id INTEGER NOT NULL,
        month_index INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        paid_on TEXT,
        FOREIGN KEY (student_id) REFERENCES student (id)
    )''')
    conn.commit()
    conn.close()

# Models
class Student:
    def __init__(self, id, class_name, student_name, father_name, parent_phone, monthly_fee):
        self.id = id
        self.class_name = class_name
        self.student_name = student_name
        self.father_name = father_name
        self.parent_phone = parent_phone
        self.monthly_fee = monthly_fee

class Payment:
    def __init__(self, id, student_id, month_index, amount, paid_on):
        self.id = id
        self.student_id = student_id
        self.month_index = month_index
        self.amount = amount
        self.paid_on = paid_on

# DB functions
def get_students(class_filter=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if class_filter:
        c.execute("SELECT * FROM student WHERE class_name = ?", (class_filter,))
    else:
        c.execute("SELECT * FROM student")
    rows = c.fetchall()
    conn.close()
    return [Student(*row) for row in rows]

def add_student(class_name, student_name, father_name, parent_phone, monthly_fee):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO student (class_name, student_name, father_name, parent_phone, monthly_fee) VALUES (?, ?, ?, ?, ?)",
              (class_name, student_name, father_name, parent_phone, monthly_fee))
    conn.commit()
    id = c.lastrowid
    conn.close()
    return id

def update_student(id, class_name, student_name, father_name, parent_phone, monthly_fee):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE student SET class_name=?, student_name=?, father_name=?, parent_phone=?, monthly_fee=? WHERE id=?",
              (class_name, student_name, father_name, parent_phone, monthly_fee, id))
    conn.commit()
    conn.close()

def delete_student(id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM payment WHERE student_id=?", (id,))
    c.execute("DELETE FROM student WHERE id=?", (id,))
    conn.commit()
    conn.close()

def get_payments(student_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM payment WHERE student_id=?", (student_id,))
    rows = c.fetchall()
    conn.close()
    payments = {}
    for row in rows:
        p = Payment(*row)
        payments[p.month_index] = p
    return payments

def set_payment(student_id, month_index, amount):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM payment WHERE student_id=? AND month_index=?", (student_id, month_index))
    row = c.fetchone()
    if row:
        c.execute("UPDATE payment SET amount=?, paid_on=datetime('now') WHERE id=?", (amount, row[0]))
    else:
        c.execute("INSERT INTO payment (student_id, month_index, amount, paid_on) VALUES (?, ?, ?, datetime('now'))",
                  (student_id, month_index, amount))
    conn.commit()
    conn.close()

def get_classes():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT class_name FROM student ORDER BY class_name")
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

class SyncHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/db':
            self.send_response(200)
            self.send_header('Content-type', 'application/octet-stream')
            self.end_headers()
            with open(DB_PATH, 'rb') as f:
                self.wfile.write(f.read())

    def do_POST(self):
        if self.path == '/db':
            content_length = int(self.headers['Content-Length'])
            data = self.rfile.read(content_length)
            with open(DB_PATH, 'wb') as f:
                f.write(data)
            self.send_response(200)
            self.end_headers()

# Kivy App
KV = '''
ScreenManager:
    MainScreen:

<MainScreen>:
    name: 'main'
    BoxLayout:
        orientation: 'vertical'
        MDTopAppBar:
            title: 'School Fee Manager'
            right_action_items: [["sync", lambda x: app.show_sync()]]
        BoxLayout:
            orientation: 'horizontal'
            ScrollView:
                size_hint_x: 0.3
                MDList:
                    id: class_list
            BoxLayout:
                orientation: 'vertical'
                size_hint_x: 0.7
                MDBoxLayout:
                    orientation: 'vertical'
                    size_hint_y: 0.5
                    MDLabel:
                        text: 'Add/Edit Student'
                    MDTextField:
                        id: class_name
                        hint_text: 'Class'
                    MDTextField:
                        id: student_name
                        hint_text: 'Student Name'
                    MDTextField:
                        id: father_name
                        hint_text: 'Father Name'
                    MDTextField:
                        id: parent_phone
                        hint_text: 'Parent Phone'
                    MDTextField:
                        id: monthly_fee
                        hint_text: 'Monthly Fee'
                    MDRaisedButton:
                        text: 'Save'
                        on_release: app.save_student()
                    MDRaisedButton:
                        text: 'Reset'
                        on_release: app.reset_form()
                ScrollView:
                    size_hint_y: 0.5
                    MDList:
                        id: student_list
'''

class MainScreen(Screen):
    pass

class SchoolFeeApp(MDApp):
    def build(self):
        init_db()
        self.sm = ScreenManager()
        self.sm.add_widget(MainScreen())
        return Builder.load_string(KV)

    def on_start(self):
        self.load_classes()
        self.load_students()

    def load_classes(self):
        classes = get_classes()
        class_list = self.root.get_screen('main').ids.class_list
        class_list.clear_widgets()
        # Add All
        item = OneLineListItem(text='All')
        item.bind(on_release=lambda x: self.filter_class(''))
        class_list.add_widget(item)
        for c in classes:
            item = OneLineListItem(text=c)
            item.bind(on_release=lambda x, c=c: self.filter_class(c))
            class_list.add_widget(item)

    def filter_class(self, class_name):
        self.current_class = class_name
        self.load_students()

    def load_students(self):
        students = get_students(self.current_class if hasattr(self, 'current_class') else None)
        student_list = self.root.get_screen('main').ids.student_list
        student_list.clear_widgets()
        for s in students:
            item = ThreeLineListItem(
                text=s.student_name,
                secondary_text=f"Class: {s.class_name}, Fee: {s.monthly_fee}",
                tertiary_text=f"Father: {s.father_name or '-'}, Phone: {s.parent_phone or '-'}"
            )
            item.bind(on_release=lambda x, s=s: self.show_student_actions(s))
            student_list.add_widget(item)

    def save_student(self):
        screen = self.root.get_screen('main')
        class_name = screen.ids.class_name.text
        student_name = screen.ids.student_name.text
        father_name = screen.ids.father_name.text
        parent_phone = screen.ids.parent_phone.text
        monthly_fee = int(screen.ids.monthly_fee.text or 0)
        if hasattr(self, 'editing_student'):
            update_student(self.editing_student.id, class_name, student_name, father_name, parent_phone, monthly_fee)
            del self.editing_student
        else:
            add_student(class_name, student_name, father_name, parent_phone, monthly_fee)
        self.reset_form()
        self.load_students()
        self.load_classes()

    def reset_form(self):
        screen = self.root.get_screen('main')
        screen.ids.class_name.text = ''
        screen.ids.student_name.text = ''
        screen.ids.father_name.text = ''
        screen.ids.parent_phone.text = ''
        screen.ids.monthly_fee.text = ''
        if hasattr(self, 'editing_student'):
            del self.editing_student

    def edit_student(self, s):
        screen = self.root.get_screen('main')
        screen.ids.class_name.text = s.class_name
        screen.ids.student_name.text = s.student_name
        screen.ids.father_name.text = s.father_name or ''
        screen.ids.parent_phone.text = s.parent_phone or ''
        screen.ids.monthly_fee.text = str(s.monthly_fee)
        self.editing_student = s

    def delete_student(self, s):
        delete_student(s.id)
        self.load_students()
        self.load_classes()

    def show_student_actions(self, s):
        content = MDBoxLayout(orientation='vertical')
        content.add_widget(MDLabel(text=f"Actions for {s.student_name}"))
        buttons = MDBoxLayout(orientation='horizontal')
        edit_btn = MDRaisedButton(text='Edit')
        edit_btn.bind(on_release=lambda x: self.edit_student(s))
        delete_btn = MDRaisedButton(text='Delete')
        delete_btn.bind(on_release=lambda x: self.delete_student(s))
        pay_btn = MDRaisedButton(text='Payments')
        pay_btn.bind(on_release=lambda x: self.show_payments(s))
        buttons.add_widget(edit_btn)
        buttons.add_widget(delete_btn)
        buttons.add_widget(pay_btn)
        content.add_widget(buttons)
        self.action_dialog = MDDialog(
            title="Student Actions",
            type="custom",
            content_cls=content,
            buttons=[MDFlatButton(text="Close", on_release=lambda x: self.action_dialog.dismiss())]
        )
        self.action_dialog.open()

    def show_payments(self, s):
        months = ['January','February','March','April','May','June','July','August','September','October','November','December']
        payments = get_payments(s.id)
        content = MDBoxLayout(orientation='vertical')
        self.payment_inputs = {}
        for i, m in enumerate(months):
            box = MDBoxLayout(orientation='horizontal')
            box.add_widget(MDLabel(text=m))
            input = MDTextField(text=str(payments.get(i, Payment(None, None, None, 0, None)).amount), input_filter='int')
            self.payment_inputs[i] = input
            box.add_widget(input)
            content.add_widget(box)
        self.payment_dialog = MDDialog(
            title=f"Payments for {s.student_name}",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="Cancel", on_release=lambda x: self.payment_dialog.dismiss()),
                MDFlatButton(text="Save", on_release=lambda x, s=s: self.save_payments(s))
            ]
        )
        self.payment_dialog.open()

    def save_payments(self, s):
        for i, input in self.payment_inputs.items():
            amount = int(input.text or 0)
            set_payment(s.id, i, amount)
        self.payment_dialog.dismiss()
        self.load_students()

    def show_sync(self):
        content = MDBoxLayout(orientation='vertical')
        self.sync_mode = MDTextField(hint_text='Mode: server or client')
        self.sync_ip = MDTextField(hint_text='Server IP')
        content.add_widget(self.sync_mode)
        content.add_widget(self.sync_ip)
        self.sync_dialog = MDDialog(
            title="Sync",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="Cancel", on_release=lambda x: self.sync_dialog.dismiss()),
                MDFlatButton(text="Start", on_release=self.start_sync)
            ]
        )
        self.sync_dialog.open()

    def start_sync(self, *args):
        mode = self.sync_mode.text.lower()
        ip = self.sync_ip.text
        if mode == 'server':
            self.start_server()
        elif mode == 'client':
            self.start_client(ip)
        self.sync_dialog.dismiss()

    def start_server(self):
        def run_server():
            server = HTTPServer(('0.0.0.0', 8080), SyncHandler)
            server.serve_forever()
        threading.Thread(target=run_server, daemon=True).start()

    def start_client(self, ip):
        try:
            with urllib.request.urlopen(f'http://{ip}:8080/db') as response:
                data = response.read()
            with open(DB_PATH, 'wb') as f:
                f.write(data)
            # Then post back
            with open(DB_PATH, 'rb') as f:
                data = f.read()
            req = urllib.request.Request(f'http://{ip}:8080/db', data=data, method='POST')
            with urllib.request.urlopen(req) as response:
                pass
        except Exception as e:
            print(e)

if __name__ == '__main__':
    SchoolFeeApp().run()
