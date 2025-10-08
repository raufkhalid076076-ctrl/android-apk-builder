from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'school_fee.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

MONTHS = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_name = db.Column(db.String(50), nullable=False)
    student_name = db.Column(db.String(100), nullable=False)
    father_name = db.Column(db.String(100), nullable=True)
    parent_phone = db.Column(db.String(20), nullable=True)
    monthly_fee = db.Column(db.Integer, nullable=False, default=0)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    month_index = db.Column(db.Integer, nullable=False)  # 0-11
    amount = db.Column(db.Integer, nullable=False, default=0)
    paid_on = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('Student', backref=db.backref('payments', lazy=True))

def ensure_schema():
    db.create_all()
    try:
        with db.engine.begin() as conn:
            cols = [row[1] for row in conn.execute("PRAGMA table_info('student')").fetchall()]
            if 'father_name' not in cols:
                conn.execute("ALTER TABLE student ADD COLUMN father_name VARCHAR(100)")
    except Exception:
        db.session.rollback()

with app.app_context():
    ensure_schema()

@app.route('/')
def index():
    return send_from_directory('templates', 'index.html')

@app.route('/print/<int:student_id>')
def print_slip(student_id):
    return send_from_directory('templates', 'print.html')

# Admin repair endpoint
@app.route('/admin/repair', methods=['POST'])
def admin_repair():
    ensure_schema()
    class_to_delete = request.args.get('delete_class')
    deleted = 0
    if class_to_delete:
        students = Student.query.filter_by(class_name=class_to_delete).all()
        for s in students:
            Payment.query.filter_by(student_id=s.id).delete()
            db.session.delete(s)
            deleted += 1
        db.session.commit()
    return jsonify({'status': 'ok', 'deleted_students': deleted})

@app.route('/api/classes', methods=['GET'])
def list_classes():
    classes = db.session.query(Student.class_name).distinct().order_by(Student.class_name).all()
    return jsonify([c[0] for c in classes])

@app.route('/api/classes/<path:class_name>', methods=['DELETE'])
def delete_class(class_name):
    students = Student.query.filter_by(class_name=class_name).all()
    for s in students:
        Payment.query.filter_by(student_id=s.id).delete()
        db.session.delete(s)
    db.session.commit()
    return jsonify({'status': 'ok', 'deleted_students': len(students)})

@app.route('/api/students', methods=['GET'])
def list_students():
    class_filter = request.args.get('class')
    query = Student.query
    if class_filter:
        query = query.filter(Student.class_name == class_filter)
    students = query.all()
    result = []
    for s in students:
        result.append({
            'id': s.id,
            'class_name': s.class_name,
            'student_name': s.student_name,
            'father_name': s.father_name,
            'parent_phone': s.parent_phone,
            'monthly_fee': s.monthly_fee
        })
    return jsonify(result)

@app.route('/api/students', methods=['POST'])
def create_student():
    data = request.json or {}
    # validate required fields
    if not data.get('student_name') or not data.get('father_name') or not data.get('class_name'):
        return jsonify({'error': 'class_name, student_name, father_name are required'}), 400
    s = Student(
        class_name=data.get('class_name',''),
        student_name=data.get('student_name',''),
        father_name=data.get('father_name',''),
        parent_phone=data.get('parent_phone',''),
        monthly_fee=int(data.get('monthly_fee') or 0)
    )
    db.session.add(s)
    db.session.commit()
    return jsonify({'id': s.id}), 201

@app.route('/api/students/<int:student_id>', methods=['PUT'])
def update_student(student_id):
    s = Student.query.get_or_404(student_id)
    data = request.json or {}
    # enforce father_name present
    if 'father_name' in data and not data.get('father_name'):
        return jsonify({'error': 'father_name is required'}), 400
    s.class_name = data.get('class_name', s.class_name)
    s.student_name = data.get('student_name', s.student_name)
    s.father_name = data.get('father_name', s.father_name)
    s.parent_phone = data.get('parent_phone', s.parent_phone)
    s.monthly_fee = int(data.get('monthly_fee', s.monthly_fee))
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/students/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    s = Student.query.get_or_404(student_id)
    Payment.query.filter_by(student_id=student_id).delete()
    db.session.delete(s)
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/students/<int:student_id>/payments', methods=['GET'])
def get_payments(student_id):
    s = Student.query.get_or_404(student_id)
    payments = Payment.query.filter_by(student_id=student_id).all()
    base_monthly = s.monthly_fee

    months_map = {m: {'paid': False, 'amount': 0, 'payment_id': None, 'paid_on': None} for m in range(12)}
    for p in payments:
        months_map[p.month_index] = {
            'paid': p.amount > 0,
            'amount': p.amount,
            'payment_id': p.id,
            'paid_on': p.paid_on.isoformat()
        }

    cumulative_expected = 0
    cumulative_paid = 0
    for idx in range(12):
        cumulative_expected += base_monthly
        cumulative_paid += months_map[idx]['amount']
        due = max(0, cumulative_expected - cumulative_paid)
        months_map[idx]['expected_this_month'] = base_monthly
        months_map[idx]['carry_forward_due'] = due

    return jsonify(months_map)

@app.route('/api/students/<int:student_id>/payments', methods=['POST'])
def set_payment(student_id):
    Student.query.get_or_404(student_id)
    data = request.json or {}
    try:
        month_index = int(data.get('month_index'))
        amount = int(data.get('amount'))
    except (TypeError, ValueError):
        return jsonify({'error': 'month_index and amount must be integers'}), 400
    if month_index < 0 or month_index > 11:
        return jsonify({'error': 'month_index must be between 0 and 11'}), 400
    if amount < 0:
        return jsonify({'error': 'amount must be >= 0'}), 400

    p = Payment.query.filter_by(student_id=student_id, month_index=month_index).first()
    if not p:
        p = Payment(student_id=student_id, month_index=month_index, amount=amount)
        db.session.add(p)
    else:
        p.amount = amount
        p.paid_on = datetime.utcnow()
    db.session.commit()
    return jsonify({'status': 'ok', 'payment_id': p.id})

@app.route('/api/notify/<int:student_id>', methods=['POST'])
def notify_parent(student_id):
    s = Student.query.get_or_404(student_id)
    data = request.json or {}
    message = data.get('message') or f"Fee update for {s.student_name} (Class {s.class_name})."
    success = bool(s.parent_phone)
    return jsonify({'status': 'sent' if success else 'no_phone', 'to': s.parent_phone, 'message': message})

@app.route('/templates/<path:path>')
def send_template(path):
    return send_from_directory('templates', path)

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


