from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from . import db  # Импортируем db после его определения в __init__.py
from datetime import datetime
from datetime import date

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'dean', 'teacher', 'student'
    full_name = db.Column(db.String(150), nullable=True)  # Полное имя
    group_name = db.Column(db.String(100), nullable=True)  # Группа студента
    course = db.Column(db.Integer, nullable=True)  # Курс
    record_book_number = db.Column(db.String(50), nullable=True)  # Номер зачетной книжки

class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_name = db.Column(db.String(100), nullable=False)
    course_name = db.Column(db.String(100), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session = db.Column(db.String(100), nullable=False)  # Например, "Зимняя 2024-2025" nullable=False)
    type = db.Column(db.String(50), nullable=False)  # Например, "зачет", "дифференцированный зачет", "экзамен"

    teacher = db.relationship('User', backref='records', lazy=True)

class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    record_id = db.Column(db.Integer, db.ForeignKey('record.id', ondelete='CASCADE'), nullable=False)
    grade = db.Column(db.String(10), nullable=True)
    exam_date = db.Column(db.Date, nullable=True)  # Дата сдачи

    student = db.relationship('User', backref='grades', lazy=True)
    record = db.relationship('Record', backref=db.backref('grades', cascade='all, delete-orphan', lazy=True))
