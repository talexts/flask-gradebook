from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from .models import User, Record, Grade
from . import db
from datetime import datetime
from datetime import date
from flask import Response
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from io import BytesIO
import os

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
from urllib.parse import quote

main = Blueprint('main', __name__)

font_path = os.path.join(os.path.dirname(__file__), 'static/fonts/DejaVuSans.ttf')
pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))

# Главная страница
@main.route('/')
def home():
    return render_template('index.html')

@main.route('/dashboard')
# Личный кабинет в зависимости от роли
@login_required
def dashboard():
    if current_user.role == 'dean':
        return redirect(url_for('main.dean_dashboard'))
    elif current_user.role == 'teacher':
        return redirect(url_for('main.teacher_dashboard'))
    elif current_user.role == 'student':
        return redirect(url_for('main.student_dashboard'))
    else:
        flash('Нет доступа.')
        return redirect(url_for('main.home'))

# --- Личный кабинет деканата ---
@main.route('/dean/dashboard')
@login_required
def dean_dashboard():
    if current_user.role != 'dean':
        flash('Доступ запрещен.')
        return redirect(url_for('main.dashboard'))
    return render_template('dean_dashboard.html')



@main.route('/dean/manage_records', methods=['GET', 'POST'])
@login_required
def manage_records():
    if current_user.role != 'dean':
        flash('Доступ запрещен.')
        return redirect(url_for('main.dashboard'))

    records = Record.query.all()
    teachers = User.query.filter_by(role='teacher').all()  # Получаем всех преподавателей

    if request.method == 'POST':
        group_name = request.form['group_name']
        course_name = request.form['course_name']
        teacher_id = request.form['teacher_id']
        session = request.form['session']
        record_type = request.form['type']
        new_record = Record(
            group_name=group_name,
            course_name=course_name,
            teacher_id=teacher_id,
            session=session,
            type=record_type
        )
        db.session.add(new_record)
        db.session.commit()
        flash('Ведомость добавлена.')
        return redirect(url_for('main.manage_records'))

    return render_template('manage_records.html', records=records, teachers=teachers)

@main.route('/dean/reports', methods=['GET', 'POST'])
@login_required
def dean_reports():
    if current_user.role != 'dean':
        flash('Доступ запрещён.')
        return redirect(url_for('main.dashboard'))

    # Получение списка групп
    groups = User.query.filter_by(role='student').with_entities(User.group_name).distinct().all()
    groups = [group[0] for group in groups]  # Преобразуем список кортежей в список строк

    if request.method == 'POST':
        selected_group = request.form.get('group_name')
        if not selected_group:
            flash('Выберите группу для создания отчёта.')
            return redirect(url_for('main.dean_reports'))

        # Перенаправляем на маршрут генерации отчёта
        return redirect(url_for('main.generate_report_dean', group_name=selected_group))

    return render_template('dean_reports.html', groups=groups)

# --- Личный кабинет преподавателя ---
@main.route('/teacher/dashboard', methods=['GET', 'POST'])
@login_required
def teacher_dashboard():
    if current_user.role != 'teacher':
        flash('Доступ запрещен.')
        return redirect(url_for('main.dashboard'))

    # Получаем все доступные сессии
    sessions = db.session.query(Record.session).distinct().all()
    selected_session = request.form.get('session')  # Получаем выбранную сессию из формы

    # Фильтруем записи по сессии, если она выбрана, иначе берём все
    if selected_session:
        records = Record.query.filter_by(teacher_id=current_user.id, session=selected_session) \
            .order_by(Record.session.desc(), Record.course_name).all()
    else:
        records = Record.query.filter_by(teacher_id=current_user.id) \
            .order_by(Record.session.desc(), Record.course_name).all()

    return render_template('teacher_dashboard.html', records=records, sessions=sessions, selected_session=selected_session)

@main.route('/teacher/grade/<int:record_id>', methods=['GET', 'POST'])
@login_required
def grade_students(record_id):
    if current_user.role != 'teacher':
        flash('Доступ запрещен.')
        return redirect(url_for('main.dashboard'))

    record = Record.query.get_or_404(record_id)
    students = User.query.filter_by(role='student', group_name=record.group_name).all()

    student_data = []
    for student in students:
        grade = next((g for g in student.grades if g.record_id == record_id), None)
        student_data.append({
            'student': student,
            'grade': grade,
            'exam_date': grade.exam_date.strftime('%Y-%m-%d') if grade and grade.exam_date else date.today().strftime('%Y-%m-%d')
        })


    grade_options = {
        "зачет": ["Зачтено", "Не зачтено", "Н/Я"],
        "дифференцированный зачет": ["Неудовлетворительно", "Удовлетворительно", "Хорошо", "Отлично", "Н/Я"],
        "экзамен": ["Неудовлетворительно", "Удовлетворительно", "Хорошо", "Отлично", "Н/Я"]
    }
    options = grade_options.get(record.type, [])
    
    print('wefwefdddddw')

    if request.method == 'POST':
        for student in students:
            grade = request.form.get(f'grade_{student.id}')
            exam_date_str = request.form.get(f'exam_date_{student.id}')
            exam_date = datetime.strptime(exam_date_str, '%Y-%m-%d').date() if exam_date_str else datetime.strptime(date.today, '%Y-%m-%d')

            print(exam_date_str)

            existing_grade = Grade.query.filter_by(student_id=student.id, record_id=record_id).first()
            if existing_grade:
                existing_grade.grade = grade
                existing_grade.exam_date = exam_date
            else:
                new_grade = Grade(student_id=student.id, record_id=record_id, grade=grade, exam_date=exam_date)
                db.session.add(new_grade)
        db.session.commit()
        flash('Оценки и даты сдачи обновлены.')
        return redirect(url_for('main.teacher_dashboard'))

    return render_template('grade_students.html', record=record, students=student_data, options=options, today=date.today())


# --- Личный кабинет студента ---
@main.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        flash('Доступ запрещен.')
        return redirect(url_for('main.dashboard'))

    # Получаем все оценки студента
    grades = Grade.query.filter_by(student_id=current_user.id).all()

    # Группируем оценки по сессиям
    grouped_data = {}
    for grade in grades:
        record = grade.record
        teacher = User.query.get(record.teacher_id) if record.teacher_id else None
        session = record.session  # Сессия из таблицы Record
        if session not in grouped_data:
            grouped_data[session] = []
        grouped_data[session].append({
            'course_name': record.course_name,
            'grade': grade.grade,
            'exam_date': grade.exam_date.strftime('%Y-%m-%d') if grade.exam_date else "Не указана",
            'type': record.type,
            'teacher_name': teacher.full_name if teacher else "Не назначен"
        })

    return render_template('student_dashboard.html', grouped_data=grouped_data)



@main.route('/dean/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if current_user.role != 'dean':
        flash('Доступ запрещен.')
        return redirect(url_for('main.dashboard'))

    users = User.query.filter(User.role == 'student').all()  # Только студенты

    if request.method == 'POST':
        # Добавление нового студента
        full_name = request.form['full_name']
        group_name = request.form['group_name']
        course = int(request.form['course'])
        record_book_number = request.form['record_book_number']
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        new_student = User(
            username=username,
            password=hashed_password,
            role='student',
            full_name=full_name,
            group_name=group_name,
            course=course,
            record_book_number=record_book_number
        )
        db.session.add(new_student)
        db.session.commit()
        flash('Студент успешно добавлен.')
        return redirect(url_for('main.manage_users'))

    return render_template('manage_users.html', users=users)


@main.route('/dean/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.role != 'dean':
        flash('Доступ запрещен.')
        return redirect(url_for('main.dashboard'))

    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        user.full_name = request.form['full_name']
        user.group_name = request.form['group_name']
        user.course = int(request.form['course'])
        user.record_book_number = request.form['record_book_number']
        db.session.commit()
        flash('Данные студента обновлены.')
        return redirect(url_for('main.manage_users'))

    return render_template('edit_user.html', user=user)


@main.route('/dean/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'dean':
        flash('Доступ запрещен.')
        return redirect(url_for('main.dashboard'))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Пользователь удален.')
    return redirect(url_for('main.manage_users'))

@main.route('/dean/manage_teachers', methods=['GET', 'POST'])
@login_required
def manage_teachers():
    if current_user.role != 'dean':
        flash('Доступ запрещен.')
        return redirect(url_for('main.dashboard'))

    teachers = User.query.filter(User.role == 'teacher').all()  # Только преподаватели

    if request.method == 'POST':
        full_name = request.form['full_name']
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        new_teacher = User(
            username=username,
            password=hashed_password,
            role='teacher',
            full_name=full_name
        )
        db.session.add(new_teacher)
        db.session.commit()
        flash('Преподаватель успешно добавлен.')
        return redirect(url_for('main.manage_teachers'))

    return render_template('manage_teachers.html', teachers=teachers)


@main.route('/dean/delete_teacher/<int:teacher_id>', methods=['POST'])
@login_required
def delete_teacher(teacher_id):
    if current_user.role != 'dean':
        flash('Доступ запрещен.')
        return redirect(url_for('main.dashboard'))

    teacher = User.query.get_or_404(teacher_id)
    if teacher.role != 'teacher':
        flash('Можно удалять только преподавателей.')
        return redirect(url_for('main.manage_teachers'))

    db.session.delete(teacher)
    db.session.commit()
    flash('Преподаватель удалён.')
    return redirect(url_for('main.manage_teachers'))

@main.route('/dean/edit_record/<int:record_id>', methods=['GET', 'POST'])
@login_required
def edit_record(record_id):
    if current_user.role != 'dean':
        flash('Доступ запрещен.')
        return redirect(url_for('main.dashboard'))

    record = Record.query.get_or_404(record_id)
    teachers = User.query.filter_by(role='teacher').all()

    if request.method == 'POST':
        record.group_name = request.form['group_name']
        record.course_name = request.form['course_name']
        record.teacher_id = request.form['teacher_id']
        record.session = request.form['session']
        record.type = request.form['type']
        db.session.commit()
        flash('Ведомость обновлена.')
        return redirect(url_for('main.manage_records'))

    return render_template('edit_record.html', record=record, teachers=teachers)


@main.route('/dean/delete_record/<int:record_id>', methods=['POST'])
@login_required
def delete_record(record_id):
    if current_user.role != 'dean':
        flash('Доступ запрещен.')
        return redirect(url_for('main.dashboard'))

    record = Record.query.get_or_404(record_id)
    db.session.delete(record)
    db.session.commit()
    flash('Ведомость удалена.')
    return redirect(url_for('main.manage_records'))


styles = getSampleStyleSheet()

# Заголовок документа
styles.add(ParagraphStyle(name='DocumentTitle',
                           fontName='DejaVuSans',
                           fontSize=18,
                           leading=22,
                           alignment=1))  # Центрирование

# Заголовок таблицы
styles.add(ParagraphStyle(name='TableHeader',
                           fontName='DejaVuSans',
                           fontSize=14,
                           leading=18,
                           textColor='white',
                           alignment=1))  # Центрирование

# Основной текст
styles.add(ParagraphStyle(name='CustomBodyText',
                           fontName='DejaVuSans',
                           fontSize=12,
                           leading=16))


def generate_pdf(group_name, records, students):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    # Заголовок документа
    elements.append(Paragraph(f"Сводный отчёт по группе: {group_name}", styles['DocumentTitle']))
    elements.append(Spacer(1, 12))

    for record in records:
        # Заголовок таблицы
        elements.append(Paragraph(f"Предмет: {record.course_name}", styles['CustomBodyText']))
        elements.append(Spacer(1, 6))

        # Таблица с данными
        data = [["ФИО студента", "Оценка", "Дата сдачи"]]
        for student in students:
            grade = Grade.query.filter_by(student_id=student.id, record_id=record.id).first()
            grade_text = grade.grade if grade and grade.grade else "Нет оценки"
            date_text = grade.exam_date.strftime('%d.%m.%Y') if grade and grade.exam_date else "Нет даты"
            data.append([student.full_name, grade_text, date_text])

        table = Table(data, colWidths=[200, 100, 100])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 12))

    # Генерация PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

@main.route('/dean/report/<group_name>', methods=['GET'])
@login_required
def generate_report_dean(group_name):
    if current_user.role != 'dean':
        flash('Доступ запрещён.')
        return redirect(url_for('main.dashboard'))

    # Получаем данные
    students = User.query.filter_by(role='student', group_name=group_name).all()
    records = Record.query.filter_by(group_name=group_name).all()

    # Генерация PDF
    pdf_data = generate_pdf(group_name, records, students)

    # Возвращаем PDF
    response = Response(pdf_data, content_type='application/pdf')
    response.headers['Content-Disposition'] = f"inline; filename*=UTF-8''{quote(f'report_{group_name}.pdf')}"
    return response    