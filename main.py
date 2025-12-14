"""
Программа School App создана для работы с базой учителей и учеников.

Nika Sheshko
"""

__author__ = "Nika Sheshko"

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import xml.etree.ElementTree as ET
import datetime
import re
import os
import logging
from xhtml2pdf.default import DEFAULT_FONT
from xml.dom import minidom
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from database import SchoolDatabase
from models import Teacher, Student, GradeRecord

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('school_app_mult.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

app_logger = logging.getLogger("school_app")
app_logger.setLevel(logging.DEBUG)
app_file_handler = logging.FileHandler('school_app.log', encoding='utf-8')
app_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
app_file_handler.setFormatter(app_formatter)
app_logger.addHandler(app_file_handler)
app_logger.propagate = False


class SchoolDataManager:
    """Готовит данные из базы для графического интерфейса."""

    ALLOWED_SUBJECTS = [
        "Начальные классы",
        "Русский язык", "Русская литература", "Иностранный язык",
        "Английский язык", "Немецкий язык", "История России",
        "Всемирная история", "Математика", "Физика", "Химия",
        "Биология", "География", "Информатика", "ОБЖ",
        "Физкультура", "Музыка", "ИЗО", "Человек и мир",
        "Обществознание", "Экономика"
    ]

    CLASS_LETTERS = {
        1: ["А", "Б", "В"],
        2: ["А", "Б", "В"],
        3: ["А", "Б", "В"],
        4: ["А", "Б", "В"],
        5: ["А", "Б"],
        6: ["А", "Б"],
        7: ["А", "Б"],
        8: ["А", "Б"],
        9: ["А", "Б"],
        10: ["А", "Б"],
        11: ["А", "Б"]
    }

    def __init__(self):
        self.db = SchoolDatabase()

    def is_database_empty(self):
        """Проверяет, пустая ли БД"""
        try:
            self.db.DB_CURSOR.execute("SELECT COUNT(*) FROM students")
            student_count = self.db.DB_CURSOR.fetchone()[0]

            self.db.DB_CURSOR.execute("SELECT COUNT(*) FROM teachers")
            teacher_count = self.db.DB_CURSOR.fetchone()[0]

            self.db.DB_CURSOR.execute("SELECT COUNT(*) FROM grades")
            grade_count = self.db.DB_CURSOR.fetchone()[0]

            return student_count == 0 and teacher_count == 0 and grade_count == 0
        except:
            return True

    def get_table_count(self, table_name):
        """Возвращает количество записей в таблице"""
        self.db.DB_CURSOR.execute(f"SELECT COUNT(*) FROM {table_name}")
        return self.db.DB_CURSOR.fetchone()[0]

    def build_student_index(self):
        """Создает словарь ФИО -> id для всех учеников"""
        self.db.DB_CURSOR.execute(
            "SELECT id, last_name, first_name, COALESCE(middle_name, '') FROM students"
        )
        students = self.db.DB_CURSOR.fetchall()
        index = {}
        for student in students:
            student_id, last_name, first_name, middle_name = student
            fio = " ".join(list(filter(None, [last_name, first_name, middle_name]))).strip()
            index[fio] = student_id
        return index


    def parse_fio(self, fio):
        """Разбивает ФИО на составные части"""
        parts = fio.split()
        last_name = parts[0] if len(parts) > 0 else ""
        first_name = parts[1] if len(parts) > 1 else ""
        middle_name = parts[2] if len(parts) > 2 else ""
        return last_name, first_name, middle_name

    def split_classes(self, text):
        """Разбивает строку с классами на список."""
        return [cls.strip() for cls in text.split(",") if cls.strip()]

    def format_fio(self, last_name, first_name, middle_name):
        return " ".join(part for part in [last_name, first_name, middle_name] if part)

    def parse_and_validate_fio(self, fio):
        """Проверяет ФИО и возвращает отдельные части."""
        fio = fio.strip()
        if not fio:
            raise ValueError("Поле ФИО не может быть пустым")
        parts = fio.split()
        if len(parts) < 2:
            raise ValueError("Нужно указать минимум фамилию и имя")
        last_name = parts[0]
        first_name = parts[1]
        middle_name = " ".join(parts[2:]) if len(parts) > 2 else ""
        for chunk in [last_name, first_name] + ([middle_name] if middle_name else []):
            if not self.is_valid_name_part(chunk):
                raise ValueError("Имя и фамилия могут содержать только буквы, пробелы и дефис")
        return last_name, first_name, middle_name

    def is_valid_name_part(self, text):
        """Проверяет имя/фамилию на допустимые символы."""
        pattern = r"^[А-ЯЁа-яё]+([ -][А-ЯЁа-яё]+)*$"
        return re.match(pattern, text) is not None

    def parse_birth_date(self, date_str):
        """Преобразует строку ДД.ММ.ГГГГ в объект date."""
        date_str = date_str.strip()
        if not date_str:
            raise ValueError("Укажите дату рождения в формате ДД.ММ.ГГГГ")
        try:
            value = datetime.datetime.strptime(date_str, "%d.%m.%Y").date()
        except ValueError:
            raise ValueError("Дата должна быть в формате ДД.ММ.ГГГГ")
        if value > datetime.date.today():
            raise ValueError("Дата рождения не может быть в будущем")
        return value

    def calculate_age(self, birth_date):
        """Возвращает возраст на сегодняшний день."""
        today = datetime.date.today()
        age = today.year - birth_date.year
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
        return age

    def validate_teacher_age(self, birth_date):
        """Проверяет, подходит ли возраст для учителя."""
        age = self.calculate_age(birth_date)
        if age < 20:
            raise ValueError("Учитель не может быть младше 20 лет")
        if age > 86:
            raise ValueError("Учитель не может быть старше 86 лет")

    def validate_student_age(self, birth_date, class_name):
        """Проверяет возраст ученика с учётом класса."""
        age = self.calculate_age(birth_date)
        grade = self.extract_grade(class_name)
        
        age_limits = {
            1: (6, 8),
            2: (7, 9),
            3: (8, 10),
            4: (9, 11),
            5: (10, 12),
            6: (11, 13),
            7: (12, 14),
            8: (13, 15),
            9: (14, 16),
            10: (15, 17),
            11: (16, 18)
        }
        
        if grade not in age_limits:
            raise ValueError(f"Некорректный номер класса: {grade}")
        
        min_age, max_age = age_limits[grade]
        
        if age < min_age:
            raise ValueError(f"Для {class_name} минимальный возраст {min_age} лет")
        if age > max_age:
            raise ValueError(f"Для {class_name} максимальный возраст {max_age} лет")

    def extract_grade(self, class_name):
        """Возвращает номер класса из строки вида 5А."""
        digits = "".join(ch for ch in class_name if ch.isdigit())
        if not digits:
            raise ValueError("Некорректный номер класса")
        grade = int(digits)
        if grade not in self.CLASS_LETTERS:
            raise ValueError("Такого класса нет в школе")
        return grade

    def validate_subject(self, subject):
        """Проверяет, что предмет входит в список допустимых."""
        subject = subject.strip()
        if subject not in self.ALLOWED_SUBJECTS:
            raise ValueError("Выберите предмет из списка")
        return subject

    def validate_teacher_classes(self, classes_str):
        """Проверяет набор классов у учителя."""
        if not classes_str.strip():
            raise ValueError("Укажите хотя бы один класс")
        classes = self.split_classes(classes_str)
        if not classes:
            raise ValueError("Укажите хотя бы один класс")
        for cls in classes:
            self.validate_class_name(cls)
        return classes

    def validate_class_name(self, class_name):
        """Проверяет запись класса вроде 5А."""
        class_name = class_name.strip().upper()
        grade = self.extract_grade(class_name)
        letter = class_name[-1]
        if letter not in self.CLASS_LETTERS[grade]:
            raise ValueError(f"В {grade} классе нет литеры {letter}")
        return f"{grade}{letter}"

    def get_allowed_classes(self):
        """Возвращает список всех возможных классов (для ComboBox)."""
        result = []
        for grade, letters in self.CLASS_LETTERS.items():
            for letter in letters:
                result.append(f"{grade}{letter}")
            return result

    def get_subject_list(self):
        try:
            return self.db.get_subject_list()
        except Exception as e:
            self.logger.error(f"Ошибка получения списка предметов: {e}")
            return []

    def get_teacher_list(self):
        try:
            teachers = self.db.get_teacher_fios()
            return [self.format_fio(*teacher).strip() for teacher in teachers]
        except Exception as e:
            self.logger.error(f"Ошибка получения списка учителей: {e}")
            return []

    def get_student_list(self):
        try:
            rows = self.db.fetch_all_students()
            return [self.format_fio(row[1], row[2], row[3]).strip() for row in rows]
        except Exception as e:
            self.logger.error(f"Ошибка получения списка учеников: {e}", exc_info=True)
            return []

    def get_grade_subjects(self):
        return [subject for subject in self.ALLOWED_SUBJECTS if subject != "Начальные классы"]

    def get_class_list(self):
        try:
            return self.db.get_class_list()
        except Exception as e:
            self.logger.error(f"Ошибка получения списка классов: {e}")
            return []

    def get_teachers_by_subject(self, subject):
        try:
            teachers = self.db.get_teachers_by_subject(subject)
            return [self.format_fio(*teacher).strip() for teacher in teachers]
        except Exception as e:
            self.logger.error(f"Ошибка запроса учителей по предмету: {e}", exc_info=True)
            return []

    def get_teacher_classes(self, fio):
        try:
            last_name, first_name, middle_name = self.parse_fio(fio)
            classes = self.db.get_teacher_classes_by_name(last_name, first_name, middle_name)
            return classes if classes else []
        except Exception as e:
            self.logger.error(f"Ошибка получения классов учителя: {e}", exc_info=True)
            return []

    def get_student_count(self, class_name=None):
        try:
            if class_name:
                class_name = class_name.strip()
            return self.db.get_students_count(class_name if class_name else None)
        except Exception as e:
            self.logger.error(f"Ошибка получения количества учеников: {e}", exc_info=True)
            return []

    def get_all_teachers(self):
        """Получение всех учителей в формате для GUI"""
        try:
            rows = self.db.fetch_all_teachers()
            teachers = []
            for teacher_id, last_name, first_name, middle_name, birth_date, subject, classes in rows:
                teacher = Teacher(last_name, first_name, middle_name, subject, classes or [])
                birth_str = birth_date.strftime("%d.%m.%Y") if birth_date else ""
                values = (teacher.full_name, birth_str, teacher.subject, ", ".join(teacher.classes))
                teachers.append({
                    "id": teacher_id,
                    "birth_date": birth_str,
                    "values": values
                })
            return teachers
        except Exception as e:
            self.logger.error(f"Ошибка получения учителей: {e}", exc_info=True)
            return []

    def get_all_students(self):
        """Получение всех учеников в формате для GUI"""
        try:
            rows = self.db.fetch_all_students()
            result = []
            for student_id, last_name, first_name, middle_name, birth_date, classes in rows:
                student = Student(last_name, first_name, middle_name, classes or [])
                birth_str = birth_date.strftime("%d.%m.%Y") if birth_date else ""
                values = (student.full_name, birth_str, ", ".join(student.classes))
                result.append({
                    "id": student_id,
                    "birth_date": birth_str,
                    "values": values
                })
            return result
        except Exception as e:
            self.logger.error(f"Ошибка получения учеников: {e}", exc_info=True)
            return []

    def get_all_grades(self):
        """Получение всех оценок для отображения"""
        try:
            rows = self.db.get_all_grades_rows()
            result = []
            for grade_id, student_id, last_name, first_name, middle_name, class_name, subject_name, grade in rows:
                fio = f"{last_name} {first_name} {middle_name}".strip()
                if class_name:
                    class_str = ", ".join(class_name) if isinstance(class_name, list) else str(class_name)
                else:
                    class_str = ""
                grade_obj = GradeRecord(student_id, subject_name, grade)
                result.append({
                    "id": grade_id,
                    "student_id": student_id,
                    "values": grade_obj.to_display_tuple(fio, class_str)
                })
            return result
        except Exception as e:
            self.logger.error(f"Ошибка получения оценок: {e}", exc_info=True)
            return []

    def add_teacher_gui(self, fio, subject, classes_str, birth_date_str):
        """Добавляет нового учителя после всех проверок."""
        self.logger.info(f"Начало добавления учителя: ФИО='{fio}', предмет='{subject}', классы='{classes_str}', дата рождения='{birth_date_str}'")

        try:
            last_name, first_name, middle_name = self.parse_and_validate_fio(fio)
            self.logger.debug(f"ФИО успешно разобрано: {last_name} {first_name} {middle_name}")

            subject = self.validate_subject(subject)
            self.logger.debug(f"Предмет успешно валидирован: {subject}")

            classes = self.validate_teacher_classes(classes_str)
            self.logger.debug(f"Классы успешно валидированы: {classes}")

            birth_date = self.parse_birth_date(birth_date_str)
            self.logger.debug(f"Дата рождения успешно разобрана: {birth_date}")

            self.validate_teacher_age(birth_date)
            self.logger.debug("Возраст учителя успешно валидирован")

            if self.db.teacher_exists(last_name, first_name, middle_name, subject):
                self.logger.warning(f"Попытка добавить существующего учителя: {last_name} {first_name} {middle_name} - {subject}")
                raise ValueError("Такой учитель уже есть в базе")

            teacher = Teacher(last_name, first_name, middle_name, subject, classes)
            last, first, middle, subj, class_list = teacher.to_db_payload()

            self.db.add_teacher(last, first, subj, class_list, middle, birth_date.isoformat())
            self.logger.info(f"Учитель успешно добавлен в базу данных: {last_name} {first_name} {middle_name} - {subject}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при добавлении учителя {fio}: {e}", exc_info=True)
            raise

    def add_student_gui(self, fio, class_name, birth_date_str):
        """Добавляет ученика после проверок."""
        self.logger.info(f"Начало добавления ученика: ФИО='{fio}', класс='{class_name}', дата рождения='{birth_date_str}'")

        try:
            last_name, first_name, middle_name = self.parse_and_validate_fio(fio)
            self.logger.debug(f"ФИО ученика успешно разобрано: {last_name} {first_name} {middle_name}")

            class_name = self.validate_class_name(class_name)
            self.logger.debug(f"Класс ученика успешно валидирован: {class_name}")

            birth_date = self.parse_birth_date(birth_date_str)
            self.logger.debug(f"Дата рождения ученика успешно разобрана: {birth_date}")

            self.validate_student_age(birth_date, class_name)
            self.logger.debug("Возраст ученика успешно валидирован")

            self.db.add_student(last_name, first_name, [class_name], middle_name, birth_date.isoformat())
            self.logger.info(f"Ученик успешно добавлен в базу данных: {last_name} {first_name} {middle_name} - {class_name}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при добавлении ученика {fio}: {e}", exc_info=True)
            raise

    def add_grade_gui(self, fio, subject, grade_value):
        """Добавляет новую оценку."""
        self.logger.info(f"Начало добавления оценки: ФИО='{fio}', предмет='{subject}', оценка='{grade_value}'")

        try:
            last_name, first_name, middle_name = self.parse_and_validate_fio(fio)
            self.logger.debug(f"ФИО ученика успешно разобрано: {last_name} {first_name} {middle_name}")

            subject = self.validate_subject(subject)
            self.logger.debug(f"Предмет успешно валидирован: {subject}")

            if subject == "Начальные классы":
                self.logger.warning(f"Попытка выставить оценку по предмету 'Начальные классы' для ученика {fio}")
                raise ValueError("Нельзя выставлять оценки по предмету 'Начальные классы'")

            try:
                grade = int(grade_value)
                self.logger.debug(f"Оценка успешно преобразована в число: {grade}")
            except ValueError:
                self.logger.warning(f"Некорректная оценка '{grade_value}' - не является числом")
                raise ValueError("Оценка должна быть числом от 1 до 5")

            if grade < 1 or grade > 5:
                self.logger.warning(f"Некорректная оценка {grade} - должна быть от 1 до 5")
                raise ValueError("Оценка должна быть от 1 до 5")

            student_id = self.db.find_student_id(last_name, first_name, middle_name)
            if not student_id:
                self.logger.warning(f"Ученик не найден: {last_name} {first_name} {middle_name}")
                raise ValueError("Ученик с таким ФИО не найден")

            self.db.add_grade(student_id, subject, grade)
            self.logger.info(f"Оценка успешно добавлена: ученик {last_name} {first_name} {middle_name}, предмет {subject}, оценка {grade}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при добавлении оценки для ученика {fio}: {e}", exc_info=True)
            raise

    def import_teachers(self, teachers_rows):
        """Импортирует учителей из загруженного файла в базу."""
        imported = 0
        for row in teachers_rows:
            if len(row) >= 4:
                fio, birth, subject, classes_str = row[0], row[1], row[2], row[3]
            elif len(row) == 3:
                fio, subject, classes_str = row
                birth = "01.01.1980"
            else:
                continue
            try:
                self.add_teacher_gui(fio, subject, classes_str, birth)
                imported += 1
            except Exception as exc:
                self.logger.error(f"Ошибка импорта учителя: {exc}")
        return imported

    def import_students(self, student_rows):
        """Импортирует учеников из загруженного файла."""
        imported = 0
        for row in student_rows:
            if len(row) >= 3:
                fio, birth, class_str = row[0], row[1], row[2]
            elif len(row) == 2:
                fio, class_str = row
                birth = "01.09.2012"
            else:
                continue
            try:
                self.add_student_gui(fio, class_str, birth)
                imported += 1
            except Exception as exc:
                self.logger.error(f"Ошибка импорта ученика: {exc}", exc_info=True)
                
        return imported

    def import_grades(self, grade_rows):
        """Импортирует оценки из загруженного файла."""
        imported = 0
        for row in grade_rows:
            if len(row) < 3:
                continue
            fio, subject, grade_value = row
            if subject.strip() == "Начальные классы":
                continue
            try:
                self.add_grade_gui(fio, subject, grade_value)
                imported += 1
            except Exception as exc:
                self.logger.error(f"Ошибка импорта оценки: {exc}", exc_info=True)
                
        return imported

    def update_teacher_gui(self, teacher_id, new_fio, new_subject, new_classes_str, birth_date_str):
        """Обновление учителя из GUI"""
        last_name, first_name, middle_name = self.parse_and_validate_fio(new_fio)
        classes = self.validate_teacher_classes(new_classes_str)
        subject = self.validate_subject(new_subject)
        birth_date = self.parse_birth_date(birth_date_str)
        self.validate_teacher_age(birth_date)
        self.db.update_teachers(
            teacher_id, last_name, first_name, subject, classes, middle_name, birth_date.isoformat()
        )
        return True

    def delete_teacher_gui(self, teacher_id):
        """Удаление учителя из GUI"""
        self.logger.info(f"Начало удаления учителя с ID: {teacher_id}")

        try:
            # Получаем информацию об учителе перед удалением для логирования
            teacher_info = self.db.get_teacher_by_id(teacher_id)
            if teacher_info:
                teacher_name = f"{teacher_info[0]} {teacher_info[1]} {teacher_info[2] or ''}".strip()
                self.logger.debug(f"Удаление учителя: {teacher_name} (ID: {teacher_id})")

            self.db.delete_teacher(teacher_id)
            self.logger.info(f"Учитель успешно удален: ID {teacher_id}")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка удаления учителя с ID {teacher_id}: {e}", exc_info=True)
            return False

    def update_student_gui(self, student_id, new_fio, new_class_str, birth_date_str):
        """Обновление ученика из GUI"""
        self.logger.info(f"Начало обновления ученика с ID {student_id}: ФИО='{new_fio}', класс='{new_class_str}', дата рождения='{birth_date_str}'")

        try:
            last_name, first_name, middle_name = self.parse_and_validate_fio(new_fio)
            self.logger.debug(f"Новое ФИО ученика успешно разобрано: {last_name} {first_name} {middle_name}")

            class_name = self.validate_class_name(new_class_str)
            self.logger.debug(f"Новый класс ученика успешно валидирован: {class_name}")

            birth_date = self.parse_birth_date(birth_date_str)
            self.logger.debug(f"Новая дата рождения ученика успешно разобрана: {birth_date}")

            self.validate_student_age(birth_date, class_name)
            self.logger.debug("Новый возраст ученика успешно валидирован")

            self.db.update_students(
                student_id, last_name, first_name, [class_name], middle_name, birth_date.isoformat()
            )
            self.logger.info(f"Ученик успешно обновлен: ID {student_id}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при обновлении ученика с ID {student_id}: {e}", exc_info=True)
            raise

    def delete_student_gui(self, student_id):
        """Удаление ученика из GUI"""
        self.logger.info(f"Начало удаления ученика с ID: {student_id}")

        try:
            # Получаем информацию об ученике перед удалением для логирования
            student_info = self.db.get_student_by_id(student_id)
            if student_info:
                student_name = f"{student_info[0]} {student_info[1]} {student_info[2] or ''}".strip()
                self.logger.debug(f"Удаление ученика: {student_name} (ID: {student_id})")

            self.db.delete_student(student_id)
            self.logger.info(f"Ученик успешно удален: ID {student_id}")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка удаления ученика с ID {student_id}: {e}", exc_info=True)
            return False

    def update_grade_gui(self, grade_id, fio, subject_name, grade_value):
        """Обновление оценки из GUI"""
        self.logger.info(f"Начало обновления оценки с ID {grade_id}: ФИО='{fio}', предмет='{subject_name}', оценка='{grade_value}'")

        try:
            grade_int = int(grade_value)
            if grade_int < 1 or grade_int > 5:
                self.logger.warning(f"Некорректная оценка {grade_int} при обновлении оценки ID {grade_id}")
                raise ValueError("Оценка должна быть от 1 до 5")
            self.logger.debug(f"Оценка успешно валидирована: {grade_int}")

            last_name, first_name, middle_name = self.parse_and_validate_fio(fio)
            self.logger.debug(f"ФИО успешно разобрано: {last_name} {first_name} {middle_name}")

            subject_name = self.validate_subject(subject_name)
            self.logger.debug(f"Предмет успешно валидирован: {subject_name}")

            if subject_name == "Начальные классы":
                self.logger.warning(f"Попытка обновить оценку по предмету 'Начальные классы' для оценки ID {grade_id}")
                raise ValueError("Нельзя выставлять оценки по предмету 'Начальные классы'")

            current_student_id = self.db.get_student_id_by_grade_id(grade_id)
            if not current_student_id:
                self.logger.warning(f"Оценка с ID {grade_id} не найдена в базе")
                raise ValueError("Оценка не найдена в базе")

            current_fio = self.db.get_student_fio_by_id(current_student_id)
            new_fio = f"{last_name} {first_name} {middle_name}".strip()

            new_student_id = self.db.find_student_id(last_name, first_name, middle_name)

            if current_fio != new_fio:
                self.logger.debug(f"Изменение ФИО ученика при обновлении оценки: '{current_fio}' -> '{new_fio}'")
                if new_student_id:
                    self.logger.debug(f"Найден существующий ученик с новым ФИО, обновление оценки для student_id {new_student_id}")
                    self.db.update_grade(grade_id, new_student_id, subject_name, grade_int)
                else:
                    self.logger.debug("Создание нового ученика и обновление оценки")
                    class_name, birth_date = self.db.get_student_data_by_id(current_student_id)
                    if class_name is None:
                        raise ValueError("Ученик не найден в базе")

                    self.db.update_students(
                        current_student_id, last_name, first_name, class_name, middle_name, birth_date
                    )
                    self.db.update_grade(grade_id, current_student_id, subject_name, grade_int)
            else:
                self.logger.debug("Обновление оценки без изменения ученика")
                self.db.update_grade(grade_id, current_student_id, subject_name, grade_int)

            self.logger.info(f"Оценка успешно обновлена: ID {grade_id}")
            return True

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Ошибка обновления оценки с ID {grade_id}: {error_msg}", exc_info=True)
            return ValueError(error_msg)

    def delete_grade_gui(self, grade_id):
        """Удаление оценки из GUI"""
        self.logger.info(f"Начало удаления оценки с ID: {grade_id}")

        try:
            # Получаем информацию об оценке перед удалением для логирования
            grade_info = self.db.get_grade_by_id(grade_id)
            if grade_info:
                self.logger.debug(f"Удаление оценки: ID {grade_id}, ученик ID {grade_info[0]}, предмет '{grade_info[1]}', оценка {grade_info[2]}")

            self.db.delete_grade(grade_id)
            self.logger.info(f"Оценка успешно удалена: ID {grade_id}")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка удаления оценки с ID {grade_id}: {e}", exc_info=True)
            return False

    def get_academic_report(self):
        """Возвращает словарь с данными по отличникам и двоечникам."""
        try:
            return self.db.get_grades()
        except Exception as e:
            self.logger.error(f"Ошибка получения отчета: {e}", exc_info=True)
            return {'good_students': [], 'bad_students': [], 'total_students': 0}


def _pretty_write_xml(root, filename):
    """Красивое сохранение XML"""
    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent=" ")
    with open(filename, 'w', encoding="utf-8") as f:
        f.write(xml_str)


class NoFileChoosen(Exception):
    """Исключение вызывается, когда файл не выбран"""
    pass


class NoFileOpen(Exception):
    """Исключение вызывается, когда файл не открыт для редактирования"""
    pass


class FileOperationError(Exception):
    """Базовое исключение для операций с файлами"""
    pass


class EmptySearchError(Exception):
    """Исключение вызывается, когда поле поиска пустое"""
    pass


class XMLProcessingError(Exception):
    """Исключение для ошибок обработки XML"""
    pass


class NoDataForEdit(Exception):
    """Исключение вызывается, когда нет данных для редактирования"""
    pass


class NoImportFileError(Exception):
    """Исключение вызывается, когда нет файла для импорта в БД"""
    pass


class ReportGenerator:
    """Создаёт PDF-отчёт на основе HTML-шаблона."""

    def __init__(self):
        if not os.path.exists('templates'):
            os.makedirs('templates')
        self.env = Environment(loader=FileSystemLoader('templates'))

    def generate_pdf_report(self, data, report_type, output_file):
        """Генерация PDF отчета с использованием HTML шаблона"""
        self.logger.info(f"Начало генерации PDF отчета: тип '{report_type}', файл '{output_file}', записей: {len(data)}")

        try:
            template = self.env.get_template('report_template_pdf.html')
            self.logger.debug("HTML шаблон успешно загружен")

            if report_type == "Учителя":
                headers = ["ФИО", "Дата рождения", "Предмет", "Классы"]
            elif report_type == "Ученики":
                headers = ["ФИО", "Дата рождения", "Класс"]
            else:
                headers = ["ФИО", "Предмет", "Оценка"]

            self.logger.debug(f"Заголовки отчета: {headers}")
            font_path = os.path.abspath("fonts").replace("\\", "/")
            self.logger.debug(f"Путь к шрифтам: {font_path}")

            html_content = template.render(
                report_type=report_type,
                generation_date=datetime.datetime.now().strftime('%d.%m.%Y %H:%M'),
                headers=headers,
                data=data,
                total_count=len(data),
                font_path=font_path
            )
            self.logger.debug("HTML контент успешно сгенерирован")

            return self.generate_pdf_from_html_template(html_content, output_file)

        except Exception as e:
            self.logger.error(f"Ошибка при генерации PDF отчета '{report_type}': {str(e)}", exc_info=True)
            raise FileOperationError(f"Ошибка при генерации PDF отчета: {str(e)}")

    def generate_pdf_from_html_template(self, html_content, output_file):
        """Создание PDF из HTML контента"""
        self.logger.debug(f"Начало создания PDF файла: '{output_file}'")

        try:
            font_folder = os.path.abspath("fonts")
            self.logger.debug(f"Регистрация шрифтов из папки: {font_folder}")

            pdfmetrics.registerFont(TTFont("DejaVuSans", os.path.join(font_folder, "DejaVuSans.ttf")))
            pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", os.path.join(font_folder, "DejaVuSans-Bold.ttf")))
            self.logger.debug("Шрифты успешно зарегистрированы")

            DEFAULT_FONT["helvetica"] = "DejaVuSans"
            DEFAULT_FONT["Helvetica"] = "DejaVuSans"
            DEFAULT_FONT["helvetica-bold"] = "DejaVuSans-Bold"
            DEFAULT_FONT["Helvetica-Bold"] = "DejaVuSans-Bold"
            self.logger.debug("Настройки шрифтов по умолчанию обновлены")

            with open(output_file, "wb") as output_file_obj:
                self.logger.debug("Создание PDF с помощью pisa")
                pisa_status = pisa.CreatePDF(
                    html_content,
                    dest=output_file_obj,
                    encoding='utf-8'
                )

            if pisa_status.err:
                self.logger.error(f"Ошибка создания PDF: {pisa_status.err}")
                raise Exception(f"Ошибка создания PDF: {pisa_status.err}")

            self.logger.info(f"PDF отчет успешно создан: {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при создании PDF файла '{output_file}': {str(e)}", exc_info=True)
            raise FileOperationError(f"Ошибка при создании PDF: {str(e)}")


class SchoolApp:
    """Главное окно приложения: таблицы, кнопки и вся логика GUI."""

    def __init__(self, root):
        self.logger = app_logger
        """Создаёт окно, настраивает виджеты и загружает данные."""
        self.logger.info("Запуск приложения SchoolApp.")
        self.logger.debug("Инициализация основных атрибутов приложения")

        self.root = root
        self.root.title("Школьная база данных")
        self.root.configure(bg='#f0f0f0')

        self.current_file = None
        self.current_table = "teachers"
        self.data_source = {
            "teachers": "database",
            "students": "database",
            "grades": "database"
        }
        self.loaded_import_data = {"teachers": [], "students": [], "grades": []}
        self.info_window = None
        self.sort_state = {"teachers": {}, "students": {}, "grades": {}}
        self.sort_option_maps = {}

        self.logger.debug("Инициализация менеджера данных")
        self.data_manager = SchoolDataManager()

        self.logger.debug("Настройка стилей интерфейса")
        self.setup_styles()

        self.logger.debug("Настройка генератора отчетов")
        self.setup_report_generator()

        self.logger.debug("Создание верхней панели")
        self.top_frame = self.create_top_panel()

        self.logger.debug("Создание панели управления")
        self.control_frame = self.create_control_panel()

        self.logger.debug("Создание фрейма для таблиц")
        self.table_frame = tk.Frame(root, bg='#f0f0f0')
        self.table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.logger.debug("Создание таблицы учителей")
        self.create_teachers_table()

        self.logger.debug("Создание таблицы учеников")
        self.create_students_table()

        self.logger.debug("Создание таблицы оценок")
        self.create_grades_table()

        self.logger.debug("Отображение таблицы учителей по умолчанию")
        self.show_table("teachers")

        self.logger.info("Приложение SchoolApp успешно инициализировано")

    def create_teachers_table(self):
        """Создаёт таблицу учителей и заполняет её."""
        self.teachers_frame = tk.Frame(self.table_frame, bg='#f0f0f0')

        columns = ("ФИО", "Дата рождения", "Предмет", "Классы")
        self.teachers_tree = ttk.Treeview(self.teachers_frame, columns=columns, show="headings")

        for col in columns:
            self.teachers_tree.heading(col, text=col,
                                       command=lambda c=col: self.on_column_sort("teachers", c))
            if col == "Дата рождения":
                self.teachers_tree.column(col, width=120)
            else:
                self.teachers_tree.column(col, width=180)

        self.teachers_data = self.data_manager.get_all_teachers()

        for teacher in self.teachers_data:
            self.teachers_tree.insert("", "end", iid=str(teacher["id"]), values=teacher["values"])

        scrollbar = ttk.Scrollbar(self.teachers_frame, orient="vertical", command=self.teachers_tree.yview)
        self.teachers_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.teachers_tree.pack(side="left", fill="both", expand=True)

        self.original_teachers_data = [row.copy() for row in self.teachers_data]
        self.teacher_sort_map = {
            "ФИО (А-Я)": (0, False),
            "ФИО (Я-А)": (0, True),
            "Дата рождения (старшие первыми)": (1, False),
            "Дата рождения (младшие первыми)": (1, True),
            "Предмет (А-Я)": (2, False),
            "Предмет (Я-А)": (2, True),
            "Классы (А-Я)": (3, False),
            "Классы (Я-А)": (3, True),
        }
        self.teachers_sort_options = list(self.teacher_sort_map.keys())
        self.sort_option_maps["teachers"] = self.teacher_sort_map
        self.data_source["teachers"] = "database"

    def create_students_table(self):
        """Создаёт таблицу учеников и заполняет её."""
        self.students_frame = tk.Frame(self.table_frame, bg='#f0f0f0')

        columns = ("ФИО", "Дата рождения", "Класс")
        self.students_tree = ttk.Treeview(self.students_frame, columns=columns, show="headings")

        for col in columns:
            self.students_tree.heading(col, text=col,
                                       command=lambda c=col: self.on_column_sort("students", c))
            if col == "Дата рождения":
                self.students_tree.column(col, width=120)
            else:
                self.students_tree.column(col, width=260)

        self.students_data = self.data_manager.get_all_students()

        for student in self.students_data:
            self.students_tree.insert("", "end", iid=str(student["id"]), values=student["values"])

        scrollbar = ttk.Scrollbar(self.students_frame, orient="vertical", command=self.students_tree.yview)
        self.students_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.students_tree.pack(side="left", fill="both", expand=True)

        self.original_students_data = [row.copy() for row in self.students_data]
        self.student_sort_map = {
            "ФИО (А-Я)": (0, False),
            "ФИО (Я-А)": (0, True),
            "Дата рождения (старшие первыми)": (1, False),
            "Дата рождения (младшие первыми)": (1, True),
            "Класс (от меньшего к большему)": (2, False),
            "Класс (от большего к меньшему)": (2, True),
        }
        self.students_sort_options = list(self.student_sort_map.keys())
        self.sort_option_maps["students"] = self.student_sort_map
        self.data_source["students"] = "database"

    def create_grades_table(self):
        """Создаёт таблицу оценок и заполняет её."""
        self.grades_frame = tk.Frame(self.table_frame, bg='#f0f0f0')

        columns = ("ФИО", "Предмет", "Оценка", "Класс")
        self.grades_tree = ttk.Treeview(self.grades_frame, columns=columns, show="headings")

        for col in columns:
            self.grades_tree.heading(col, text=col,
                                     command=lambda c=col: self.on_column_sort("grades", c))
            if col == "Класс":
                self.grades_tree.column(col, width=150)
            else:
                self.grades_tree.column(col, width=200)

        self.grades_data = self.data_manager.get_all_grades()

        for grade in self.grades_data:
            self.grades_tree.insert("", "end", iid=str(grade["id"]), values=grade["values"])

        scrollbar = ttk.Scrollbar(self.grades_frame, orient="vertical", command=self.grades_tree.yview)
        self.grades_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.grades_tree.pack(side="left", fill="both", expand=True)

        self.original_grades_data = [row.copy() for row in self.grades_data]
        self.grade_sort_map = {
            "ФИО (А-Я)": (0, False),
            "ФИО (Я-А)": (0, True),
            "Предмет (А-Я)": (1, False),
            "Предмет (Я-А)": (1, True),
            "Оценка (от меньшей к большей)": (2, False),
            "Оценка (от большей к меньшей)": (2, True),
            "Класс (А-Я)": (3, False),
            "Класс (Я-А)": (3, True),
        }
        self.grades_sort_options = list(self.grade_sort_map.keys())
        self.sort_option_maps["grades"] = self.grade_sort_map
        self.data_source["grades"] = "database"

    def setup_styles(self):
        """Настраивает стили для таблиц."""
        style = ttk.Style()
        style.theme_use('clam')

        style.configure("Treeview",
                        background="#ffffff",
                        foreground="#333333",
                        fieldbackground="#ffffff",
                        rowheight=25,
                        font=('Arial', 10))

        style.configure("Treeview.Heading",
                        font=('Arial', 10, 'bold'),
                        background='#e0e0e0',
                        foreground='#333333')

        style.map("Treeview", background=[('selected', '#4a6984')])

    def create_top_panel(self):
        """Рисует верхнюю панель с кнопками."""
        top_frame = tk.Frame(self.root, bg='#d0d0d0', height=80)
        top_frame.pack(fill="x", padx=5, pady=5)
        top_frame.pack_propagate(False)

        buttons_frame = tk.Frame(top_frame, bg='#d0d0d0')
        buttons_frame.pack(side="right", padx=10, pady=10)

        pdf_btn_frame = tk.Frame(buttons_frame, bg='#d0d0d0')
        pdf_btn_frame.pack(side="left", padx=3)

        pdf_icon = tk.Label(pdf_btn_frame, text="PDF",
                            bg='#ff6b6b', fg='white',
                            relief='raised',
                            width=6, height=2,
                            font=('Arial', 8, 'bold'))
        pdf_icon.pack(side="top", pady=(2, 0))
        pdf_icon.bind('<Button-1>', self.on_generate_pdf)

        pdf_text = tk.Label(pdf_btn_frame, text="PDF отчет",
                            bg='#d0d0d0', fg='#333333',
                            font=('Arial', 8))
        pdf_text.pack(side="top", pady=(0, 2))
        pdf_text.bind('<Button-1>', self.on_generate_pdf)

        button_data = [
            "Сохранить",
            "Открыть файл",
            "Создать файл",
            "Добавить запись",
            "Импорт в БД",
            "Редактировать",
            "Удалить"
        ]

        self.tool_buttons = {}

        icon_files = {
            "Сохранить": "save_button.png",
            "Открыть файл": "open_file.png",
            "Создать файл": "new_file.png",
            "Добавить запись": "new_line_inage.png",
            "Импорт в БД": "db_import.png",
            "Редактировать": "edit_icon.png",
            "Удалить": "delete_icon.png"
        }

        for text in button_data:
            if text == "Сохранить":
                click_handler = self.on_save_click
            elif text == "Открыть файл":
                click_handler = self.on_open_click
            elif text == "Создать файл":
                click_handler = self.on_new_click
            elif text == "Добавить запись":
                click_handler = self.on_add_click
            elif text == "Импорт в БД":
                click_handler = self.on_import_to_db_click
            elif text == "Редактировать":
                click_handler = self.on_edit_click
            elif text == "Удалить":
                click_handler = self.on_delete_click
            else:
                click_handler = self.on_default_click

            btn_frame = tk.Frame(buttons_frame, bg='#d0d0d0')
            btn_frame.pack(side="left", padx=3)

            try:
                image = tk.PhotoImage(file=icon_files[text])
                icon_label = tk.Label(btn_frame, image=image,
                                      bg='#e0e0e0',
                                      relief='raised',
                                      width=40,
                                      height=40)
                icon_label.image = image
                icon_label.pack(side="top", pady=(2, 0))
            except:
                icon_label = tk.Label(btn_frame, text="[Icon]",
                                      bg='#e0e0e0',
                                      relief='raised',
                                      width=6,
                                      height=2)
                icon_label.pack(side="top", pady=(2, 0))

            text_label = tk.Label(btn_frame, text=text,
                                  bg='#d0d0d0',
                                  fg='#333333',
                                  font=('Arial', 8))
            text_label.pack(side="top", pady=(0, 2))

            icon_label.bind('<Button-1>', click_handler)
            text_label.bind('<Button-1>', click_handler)

            self.tool_buttons[text] = (icon_label, text_label)

        return top_frame

    def detect_file_format(self, filename):
        """Определяет формат файла по расширению."""
        _, ext = os.path.splitext(filename)
        ext = ext.lower()

        if ext == '.xml':
            return 'xml'
        elif ext == '.csv' or ext == '.txt':
            return 'csv'
        else:
            return None

    def save_to_file(self, filename):
        """Сохраняет данные текущей таблицы в файл."""
        self.logger.info(f"Начало сохранения файла: '{filename}', таблица: {self.current_table}")

        try:
            file_format = self.detect_file_format(filename)
            self.logger.debug(f"Определен формат файла: {file_format}")

            if file_format == 'xml':
                self.logger.debug("Сохранение в формате XML")
                self.save_to_xml(filename)
            else:
                self.logger.debug("Сохранение в формате CSV")
                self.save_to_csv(filename)

            self.logger.info(f"Файл успешно сохранен: '{filename}'")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении файла '{filename}': {str(e)}", exc_info=True)
            raise FileOperationError(f"Ошибка при сохранении файла: {str(e)}")

    def save_to_csv(self, filename):
        """Сохраняет данные текущей таблицы в CSV."""
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)

                if self.current_table == "teachers":
                    tree = self.teachers_tree
                elif self.current_table == "students":
                    tree = self.students_tree
                else:
                    tree = self.grades_tree

                headers = [tree.heading(col)["text"] for col in tree["columns"]]
                writer.writerow(headers)
                for item in tree.get_children():
                    row = [tree.set(item, col) for col in tree["columns"]]
                    writer.writerow(row)

            return True
        except Exception as e:
            raise FileOperationError(f"Ошибка при сохранении CSV файла: {str(e)}")

    def save_to_xml(self, filename):
        """Сохраняет данные текущей таблицы в XML."""
        try:
            root = ET.Element("school_data")

            if self.current_table == "teachers":
                teachers_element = ET.SubElement(root, "teachers")

                for item in self.teachers_tree.get_children():
                    teacher_element = ET.SubElement(teachers_element, "teacher")
                    values = [self.teachers_tree.set(item, col) for col in self.teachers_tree["columns"]]
                    teacher_element.set("fio", values[0])
                    teacher_element.set("birth_date", values[1])
                    teacher_element.set("subject", values[2])
                    teacher_element.set("classes", values[3])
            elif self.current_table == "students":
                students_element = ET.SubElement(root, "students")

                for item in self.students_tree.get_children():
                    student_element = ET.SubElement(students_element, "student")
                    values = [self.students_tree.set(item, col) for col in self.students_tree["columns"]]
                    student_element.set("fio", values[0])
                    student_element.set("birth_date", values[1])
                    student_element.set("class", values[2])
            else:
                grades_element = ET.SubElement(root, "grades")

                for item in self.grades_tree.get_children():
                    grade_element = ET.SubElement(grades_element, "grade")
                    values = [self.grades_tree.set(item, col) for col in self.grades_tree["columns"]]
                    grade_element.set("fio", values[0])
                    grade_element.set("subject", values[1])
                    grade_element.set("value", values[2])
                    if len(values) > 3:
                        grade_element.set("class", values[3])

            tree = ET.ElementTree(root)
            tree.write(filename, encoding='utf-8', xml_declaration=True)

            return True
        except Exception as e:
            raise XMLProcessingError(f"Ошибка при сохранении XML файла: {str(e)}")

    def load_from_file(self, filename):
        """Загружает данные из XML/CSV в таблицу."""
        self.logger.info(f"Начало загрузки файла: '{filename}', таблица: {self.current_table}")

        try:
            file_format = self.detect_file_format(filename)
            self.logger.debug(f"Определен формат файла: {file_format}")

            if file_format == 'xml':
                self.logger.debug("Загрузка из формата XML")
                self.load_from_xml(filename)
            else:
                self.logger.debug("Загрузка из формата CSV")
                self.load_from_csv(filename)

            self.logger.info(f"Файл успешно загружен: '{filename}'")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке файла '{filename}': {str(e)}", exc_info=True)
            raise FileOperationError(f"Ошибка при загрузке файла: {str(e)}")

    def load_from_csv(self, filename):
        """Загружает CSV в текущую таблицу."""
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                header = next(reader, None)
                rows = [row for row in reader]

                self.apply_loaded_rows(rows)
            return True
        except Exception as e:
            raise FileOperationError(f"Ошибка при загрузке CSV файла: {str(e)}")

    def load_from_xml(self, filename):
        """Загружает XML в текущую таблицу."""
        try:
            tree_xml = ET.parse(filename)
            root = tree_xml.getroot()

            if self.current_table == "teachers":
                teachers_element = root.find("teachers")
                rows = [
                    (
                        teacher_element.get("fio", ""),
                        teacher_element.get("birth_date", ""),
                        teacher_element.get("subject", ""),
                        teacher_element.get("classes", "")
                    )
                    for teacher_element in teachers_element.findall("teacher")
                ] if teachers_element is not None else []
                self.apply_loaded_rows(rows)
            elif self.current_table == "students":
                students_element = root.find("students")
                rows = [
                    (
                        student_element.get("fio", ""),
                        student_element.get("birth_date", ""),
                        student_element.get("class", "")
                    )
                    for student_element in students_element.findall("student")
                ] if students_element is not None else []
                self.apply_loaded_rows(rows)
            else:
                grades_element = root.find("grades")
                rows = [
                    (grade_element.get("fio", ""), grade_element.get("subject", ""), 
                     grade_element.get("value", ""), grade_element.get("class", ""))
                    for grade_element in grades_element.findall("grade")
                ] if grades_element is not None else []
                self.apply_loaded_rows(rows)

            return True
        except Exception as e:
            raise XMLProcessingError(f"Ошибка при загрузке XML файла: {str(e)}")

    def apply_loaded_rows(self, rows):
        """Применяет загруженные строки к текущей таблице."""
        normalized = []

        if self.current_table == "teachers":
            for row in rows:
                if len(row) >= 4:
                    normalized.append((row[0], row[1], row[2], row[3]))
                elif len(row) == 3:
                    normalized.append((row[0], "", row[1], row[2]))
            self.set_table_data_from_rows("teachers", normalized)

        elif self.current_table == "students":
            for row in rows:
                if len(row) >= 3:
                    normalized.append((row[0], row[1], row[2]))
                elif len(row) == 2:
                    normalized.append((row[0], "", row[1]))
            self.set_table_data_from_rows("students", normalized)

        else:
            for row in rows:
                if len(row) >= 4:
                    normalized.append((row[0], row[1], row[2], row[3]))
                elif len(row) >= 3:
                    normalized.append((row[0], row[1], row[2], ""))
            self.set_table_data_from_rows("grades", normalized)

    def set_table_data_from_rows(self, table, rows):
        """Обновляет Treeview списком строк."""
        data_entries = []
        for row in rows:
            entry = {"id": None, "values": tuple(row)}
            if table == "grades":
                entry["student_id"] = None
            data_entries.append(entry)

        if table == "teachers":
            self.teachers_data = data_entries
            self.original_teachers_data = [row.copy() for row in data_entries]
            self.data_source["teachers"] = "file"
            self.loaded_import_data["teachers"] = rows
            self.populate_tree(self.teachers_tree, self.teachers_data)
        elif table == "students":
            self.students_data = data_entries
            self.original_students_data = [row.copy() for row in data_entries]
            self.data_source["students"] = "file"
            self.loaded_import_data["students"] = rows
            self.populate_tree(self.students_tree, self.students_data)
        else:
            self.grades_data = data_entries
            self.original_grades_data = [row.copy() for row in data_entries]
            self.data_source["grades"] = "file"
            self.loaded_import_data["grades"] = rows
            self.populate_tree(self.grades_tree, self.grades_data)

    def on_import_to_db_click(self, _):
        """Импортирует загруженные данные в БД"""
        try:
            imported = self.import_loaded_data_to_db()
            messagebox.showinfo("Импорт в БД", f"Импортировано записей: {imported}")
        except NoImportFileError as e:
            self.logger.warning(f"Попытка импорта без выбранного файла: {e}")
            messagebox.showwarning("Импорт в БД", str(e))
        except Exception as e:
            self.logger.error(f"Ошибка импорта в БД: {e}", exc_info=True)
            messagebox.showerror("Импорт в БД", f"Ошибка импорта: {str(e)}")

    def import_loaded_data_to_db(self):
        table = self.current_table
        self.logger.info(f"Начало импорта данных в таблицу {table}")

        if not self.current_file:
            self.logger.warning(f"Попытка импорта в таблицу {table} без выбранного файла")
            raise NoImportFileError("Сначала выберите файл для загрузки.")

        rows = self.loaded_import_data.get(table) or []
        if not rows:
            self.logger.warning(f"Попытка импорта в таблицу {table} без загруженных данных")
            raise NoImportFileError("Сначала загрузите файл для текущей таблицы.")

        self.logger.debug(f"Найдено {len(rows)} строк для импорта в таблицу {table}")

        if table == "teachers":
            imported = self.data_manager.import_teachers(rows)
        elif table == "students":
            imported = self.data_manager.import_students(rows)
        else:
            imported = self.data_manager.import_grades(rows)

        self.refresh_data(table)
        self.data_source[table] = "database"
        self.logger.info(f"Успешно импортировано {imported} записей в таблицу {table}")
        return imported

    def on_add_click(self, _):
        """Открывает окно добавления новой записи."""
        if self.data_source.get(self.current_table) != "database":
            messagebox.showwarning("Добавление", "Добавлять записи можно только при соединении с базой.")
            return
        self.open_add_dialog()

    def open_add_dialog(self):
        """Рисует диалог добавления."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить запись")
        dialog.geometry("420x320")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        form = tk.Frame(dialog, padx=20, pady=20)
        form.pack(fill="both", expand=True)

        widgets = {}

        if self.current_table == "teachers":
            tk.Label(form, text="ФИО:").grid(row=0, column=0, sticky="w", pady=5)
            fio_entry = tk.Entry(form, width=30)
            fio_entry.grid(row=0, column=1, pady=5)
            widgets["fio"] = fio_entry

            tk.Label(form, text="Предмет:").grid(row=1, column=0, sticky="w", pady=5)
            subject_combo = ttk.Combobox(form, values=self.data_manager.ALLOWED_SUBJECTS, state="readonly", width=27)
            if self.data_manager.ALLOWED_SUBJECTS:
                subject_combo.current(0)
            subject_combo.grid(row=1, column=1, pady=5)
            widgets["subject"] = subject_combo

            tk.Label(form, text="Классы:").grid(row=2, column=0, sticky="w", pady=5)
            classes_entry = tk.Entry(form, width=30)
            classes_entry.grid(row=2, column=1, pady=5)
            widgets["classes"] = classes_entry

            tk.Label(form, text="Дата рождения:").grid(row=3, column=0, sticky="w", pady=5)
            birth_entry = tk.Entry(form, width=30)
            birth_entry.insert(0, "01.01.1980")
            birth_entry.grid(row=3, column=1, pady=5)
            widgets["birth"] = birth_entry

        elif self.current_table == "students":
            tk.Label(form, text="ФИО:").grid(row=0, column=0, sticky="w", pady=5)
            fio_entry = tk.Entry(form, width=30)
            fio_entry.grid(row=0, column=1, pady=5)
            widgets["fio"] = fio_entry

            tk.Label(form, text="Класс:").grid(row=1, column=0, sticky="w", pady=5)
            classes_list = self.data_manager.get_allowed_classes()
            class_combo = ttk.Combobox(form, values=classes_list, state="readonly", width=27)
            if classes_list:
                class_combo.current(0)
            class_combo.grid(row=1, column=1, pady=5)
            widgets["class"] = class_combo

            tk.Label(form, text="Дата рождения:").grid(row=2, column=0, sticky="w", pady=5)
            birth_entry = tk.Entry(form, width=30)
            birth_entry.insert(0, "15.05.2012")
            birth_entry.grid(row=2, column=1, pady=5)
            widgets["birth"] = birth_entry

        else:
            tk.Label(form, text="ФИО ученика:").grid(row=0, column=0, sticky="w", pady=5)
            student_names = self.data_manager.get_student_list()
            fio_combo = ttk.Combobox(form, values=student_names, width=27)
            fio_combo.grid(row=0, column=1, pady=5)
            fio_combo.bind('<KeyRelease>', lambda e: self.on_combo_key_release(fio_combo, student_names))
            widgets["fio"] = fio_combo

            tk.Label(form, text="Предмет:").grid(row=1, column=0, sticky="w", pady=5)
            grade_subjects = self.data_manager.get_grade_subjects()
            subject_combo = ttk.Combobox(form, values=grade_subjects, state="readonly", width=27)
            if grade_subjects:
                subject_combo.current(0)
            subject_combo.grid(row=1, column=1, pady=5)
            widgets["subject"] = subject_combo

            tk.Label(form, text="Оценка (1-5):").grid(row=2, column=0, sticky="w", pady=5)
            grade_entry = tk.Entry(form, width=30)
            grade_entry.grid(row=2, column=1, pady=5)
            widgets["grade"] = grade_entry

        btn_frame = tk.Frame(dialog, pady=10)
        btn_frame.pack()

        tk.Button(btn_frame, text="Сохранить",
                  command=lambda: self.save_new_record(dialog, widgets)).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Отмена", command=dialog.destroy).pack(side="left", padx=5)

    def save_new_record(self, dialog, widgets):
        """Сохраняет данные из диалога добавления."""
        try:
            if self.current_table == "teachers":
                fio = widgets["fio"].get().strip()
                subject = widgets["subject"].get().strip()
                classes = widgets["classes"].get().strip()
                birth = widgets["birth"].get().strip()
                if not fio or not subject or not classes or not birth:
                    raise ValueError("Заполните все поля")
                self.data_manager.add_teacher_gui(fio, subject, classes, birth)
                self.refresh_data("teachers")
            elif self.current_table == "students":
                fio = widgets["fio"].get().strip()
                class_name = widgets["class"].get().strip()
                birth = widgets["birth"].get().strip()
                if not fio or not class_name or not birth:
                    raise ValueError("Заполните все поля")
                self.data_manager.add_student_gui(fio, class_name, birth)
                self.refresh_data("students")
            else:
                fio = widgets["fio"].get().strip()
                subject = widgets["subject"].get().strip()
                grade = widgets["grade"].get().strip()
                if not fio or not subject or not grade:
                    raise ValueError("Заполните все поля")
                self.data_manager.add_grade_gui(fio, subject, grade)
                self.refresh_data("grades")
        except ValueError as exc:
            self.logger.warning(f"Ошибка валидации при добавлении записи: {exc}")
            messagebox.showwarning("Добавление", str(exc))
            return
        except Exception as exc:
            self.logger.error(f"Не удалось добавить запись: {exc}", exc_info=True)
            messagebox.showerror("Добавление", f"Не удалось добавить запись: {exc}")
            return

        dialog.destroy()
        self.logger.info("Запись успешно добавлена")
        messagebox.showinfo("Добавление", "Запись успешно добавлена")

    def validate_search_input(self, search_term):
        """Проверяет, что поле поиска не пустое."""
        if not search_term or not search_term.strip():
            raise EmptySearchError("Поле поиска не может быть пустым")
        return True

    def on_save_click(self, _):
        """Сохраняет текущую таблицу в файл."""
        try:
            file_path = filedialog.asksaveasfilename(
                title="Сохранить файл",
                defaultextension=".csv",
                filetypes=[
                    ("CSV файлы", "*.csv"),
                    ("XML файлы", "*.xml"),
                    ("Текстовые файлы", "*.txt"),
                    ("Все файлы", "*.*")
                ]
            )
            if not file_path:
                raise NoFileChoosen("Не выбран файл для сохранения")

            self.current_file = file_path

            self.save_to_file(self.current_file)
            messagebox.showinfo("Сохранение файла", f"Файл успешно сохранен: {self.current_file}")
            self.logger.info(f"Файл успешно сохранен: {self.current_file}")

        except NoFileChoosen as e:
            messagebox.showerror("Ошибка сохранения", str(e))
            self.logger.warning(f"Попытка сохранения файла без выбора файла: {e}")
        except FileOperationError as e:
            messagebox.showerror("Ошибка операции с файлом", str(e))
            self.logger.error(f"Ошибка операции с файлом при сохранении: {e}")
        except XMLProcessingError as e:
            messagebox.showerror("Ошибка обработки XML", str(e))
            self.logger.error(f"Ошибка обработки XML при сохранении: {e}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка при сохранении файла: {str(e)}")
            self.logger.critical(f"Критическая ошибка при сохранении файла: {e}", exc_info=True)

    def on_open_click(self, _):
        """Загружает таблицу из файла."""
        try:
            file_path = filedialog.askopenfilename(
                title="Выберите файл",
                filetypes=[
                    ("CSV файлы", "*.csv"),
                    ("XML файлы", "*.xml"),
                    ("Текстовые файлы", "*.txt"),
                    ("Все файлы", "*.*")
                ]
            )
            if not file_path:
                raise NoFileChoosen("Файл не выбран")

            self.load_from_file(file_path)
            self.current_file = file_path

            messagebox.showinfo("Открытие файла", f"Файл успешно открыт: {file_path}")

        except NoFileChoosen as e:
            self.logger.warning(f"Файл не выбран для открытия: {e}")
            messagebox.showerror("Ошибка выбора файла", str(e))
        except FileOperationError as e:
            self.logger.error(f"Ошибка операции с файлом при открытии: {e}", exc_info=True)
            messagebox.showerror("Ошибка операции с файлом", str(e))
        except XMLProcessingError as e:
            self.logger.error(f"Ошибка обработки XML при открытии: {e}", exc_info=True)
            messagebox.showerror("Ошибка обработки XML", str(e))
        except Exception as e:
            self.logger.critical(f"Критическая ошибка при открытии файла: {e}", exc_info=True)
            messagebox.showerror("Ошибка", f"Произошла непредвиденная ошибка при открытии файла: {str(e)}")

    def on_new_click(self, _):
        """Создаёт пустой файл и очищает таблицу."""
        try:
            file_path = filedialog.asksaveasfilename(
                title="Создать новый файл",
                defaultextension=".csv",
                filetypes=[
                    ("CSV файлы", "*.csv"),
                    ("XML файлы", "*.xml"),
                    ("Текстовые файлы", "*.txt"),
                    ("Все файлы", "*.*")
                ]
            )

            if not file_path:
                raise NoFileChoosen("Не выбрано место для создания файла")

            if self.current_table == "teachers":
                tree = self.teachers_tree
                for item in tree.get_children():
                    tree.delete(item)
                self.teachers_data = []
                self.original_teachers_data = []
                self.data_source["teachers"] = "file"
            elif self.current_table == "students":
                tree = self.students_tree
                for item in tree.get_children():
                    tree.delete(item)
                self.students_data = []
                self.original_students_data = []
                self.data_source["students"] = "file"
            else:
                tree = self.grades_tree
                for item in tree.get_children():
                    tree.delete(item)
                self.grades_data = []
                self.original_grades_data = []
                self.data_source["grades"] = "file"

            self.save_to_file(file_path)
            self.current_file = file_path

            messagebox.showinfo("Создание файла", f"Новый файл успешно создан: {file_path}")

        except NoFileChoosen as e:
            messagebox.showerror("Ошибка создания файла", str(e))
        except FileOperationError as e:
            messagebox.showerror("Ошибка операции с файлом", str(e))
        except XMLProcessingError as e:
            messagebox.showerror("Ошибка обработки XML", str(e))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка при создании файла: {str(e)}")

    def edit_selected_row(self):
        """Открывает окно редактирования выбранной строки."""
        try:
            if self.current_table == "teachers":
                tree = self.teachers_tree
            elif self.current_table == "students":
                tree = self.students_tree
            else:
                tree = self.grades_tree

            selected_items = tree.selection()
            if not selected_items:
                messagebox.showwarning("Редактирование", "Выберите запись для редактирования")
                return

            selected_item = selected_items[0]

            current_values = tree.item(selected_item, 'values')

            edit_window = tk.Toplevel(self.root)
            edit_window.title("Редактирование записи")
            edit_window.geometry("400x300")
            edit_window.resizable(False, False)
            edit_window.transient(self.root)
            edit_window.grab_set()

            form_frame = tk.Frame(edit_window, padx=20, pady=20)
            form_frame.pack(fill="both", expand=True)

            entry_widgets = {}

            if self.current_table == "teachers":
                tk.Label(form_frame, text="ФИО:").grid(row=0, column=0, sticky="w", pady=5)
                fio_entry = tk.Entry(form_frame, width=30)
                fio_entry.grid(row=0, column=1, pady=5, padx=(10, 0))
                fio_entry.insert(0, current_values[0])
                entry_widgets['fio'] = fio_entry

                tk.Label(form_frame, text="Дата рождения:").grid(row=1, column=0, sticky="w", pady=5)
                birth_entry = tk.Entry(form_frame, width=30)
                birth_entry.grid(row=1, column=1, pady=5, padx=(10, 0))
                birth_entry.insert(0, current_values[1])
                entry_widgets['birth'] = birth_entry

                tk.Label(form_frame, text="Предмет:").grid(row=2, column=0, sticky="w", pady=5)
                subject_entry = tk.Entry(form_frame, width=30)
                subject_entry.grid(row=2, column=1, pady=5, padx=(10, 0))
                subject_entry.insert(0, current_values[2])
                entry_widgets['subject'] = subject_entry

                tk.Label(form_frame, text="Классы:").grid(row=3, column=0, sticky="w", pady=5)
                classes_entry = tk.Entry(form_frame, width=30)
                classes_entry.grid(row=3, column=1, pady=5, padx=(10, 0))
                classes_entry.insert(0, current_values[3])
                entry_widgets['classes'] = classes_entry

            elif self.current_table == "students":
                tk.Label(form_frame, text="ФИО:").grid(row=0, column=0, sticky="w", pady=5)
                fio_entry = tk.Entry(form_frame, width=30)
                fio_entry.grid(row=0, column=1, pady=5, padx=(10, 0))
                fio_entry.insert(0, current_values[0])
                entry_widgets['fio'] = fio_entry

                tk.Label(form_frame, text="Дата рождения:").grid(row=1, column=0, sticky="w", pady=5)
                birth_entry = tk.Entry(form_frame, width=30)
                birth_entry.grid(row=1, column=1, pady=5, padx=(10, 0))
                birth_entry.insert(0, current_values[1])
                entry_widgets['birth'] = birth_entry

                tk.Label(form_frame, text="Класс:").grid(row=2, column=0, sticky="w", pady=5)
                class_entry = tk.Entry(form_frame, width=30)
                class_entry.grid(row=2, column=1, pady=5, padx=(10, 0))
                class_entry.insert(0, current_values[2])
                entry_widgets['class'] = class_entry
            else:
                tk.Label(form_frame, text="ФИО ученика:").grid(row=0, column=0, sticky="w", pady=5)
                student_list = self.data_manager.get_student_list()
                fio_combo = ttk.Combobox(form_frame, values=student_list, width=27)
                fio_combo.grid(row=0, column=1, pady=5, padx=(10, 0))
                fio_combo.set(current_values[0])
                fio_combo.config(state="normal")
                fio_combo.bind('<KeyRelease>', lambda e: self.on_combo_key_release(fio_combo, student_list))
                entry_widgets['fio'] = fio_combo

                tk.Label(form_frame, text="Предмет:").grid(row=1, column=0, sticky="w", pady=5)
                subject_list = self.data_manager.get_grade_subjects()
                subject_combo = ttk.Combobox(form_frame, values=subject_list, state="readonly", width=27)
                subject_combo.grid(row=1, column=1, pady=5, padx=(10, 0))
                subject_combo.set(current_values[1])
                entry_widgets['subject'] = subject_combo

                tk.Label(form_frame, text="Оценка:").grid(row=2, column=0, sticky="w", pady=5)
                grade_entry = tk.Entry(form_frame, width=30)
                grade_entry.grid(row=2, column=1, pady=5, padx=(10, 0))
                grade_entry.insert(0, current_values[2])
                entry_widgets['grade'] = grade_entry

            button_frame = tk.Frame(edit_window, pady=10)
            button_frame.pack(fill="x")

            save_button = tk.Button(button_frame, text="Сохранить",
                                    command=lambda: self.save_edited_row(edit_window, selected_item, entry_widgets,
                                                                         tree))
            save_button.pack(side="left", padx=10)

            cancel_button = tk.Button(button_frame, text="Отмена",
                                      command=edit_window.destroy)
            cancel_button.pack(side="left", padx=10)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка при редактировании: {str(e)}")

    def on_combo_key_release(self, combo, full_list):
        """Обработчик автодополнения для ComboBox"""
        current_text = combo.get().lower()
        if current_text:
            filtered = [item for item in full_list if current_text in item.lower()]
            combo['values'] = filtered
        else:
            combo['values'] = full_list

    def refresh_data(self, table_type=None):
        """Обновляет данные из базы для указанной таблицы."""
        table = table_type or self.current_table

        if table == "teachers":
            self.teachers_data = self.data_manager.get_all_teachers()
            self.original_teachers_data = [row.copy() for row in self.teachers_data]
            self.data_source["teachers"] = "database"
            self.populate_tree(self.teachers_tree, self.teachers_data)
        elif table == "students":
            self.students_data = self.data_manager.get_all_students()
            self.original_students_data = [row.copy() for row in self.students_data]
            self.data_source["students"] = "database"
            self.populate_tree(self.students_tree, self.students_data)
        else:
            self.grades_data = self.data_manager.get_all_grades()
            self.original_grades_data = [row.copy() for row in self.grades_data]
            self.data_source["grades"] = "database"
            self.populate_tree(self.grades_tree, self.grades_data)

    def format_field_error(self, table, message):
        """Добавляет подсказку по полю, в котором возникла ошибка."""
        msg_lower = str(message).lower()
        if table == "teachers":
            mapping = [
                ("фио", "ФИО"),
                ("предмет", "Предмет"),
                ("класс", "Классы"),
                ("дата", "Дата рождения"),
                ("возраст", "Дата рождения"),
            ]
        elif table == "students":
            mapping = [
                ("фио", "ФИО"),
                ("класс", "Класс"),
                ("дата", "Дата рождения"),
                ("возраст", "Дата рождения"),
            ]
        else:
            mapping = [
                ("фио", "ФИО ученика"),
                ("предмет", "Предмет"),
                ("оцен", "Оценка"),
                ("класс", "Класс"),
            ]
        for key, label in mapping:
            if key in msg_lower:
                return f"Ошибка в поле '{label}': {message}"
        return str(message)

    def confirm_delete(self):
        """Двойное подтверждение удаления записи."""
        first = messagebox.askyesno("Удаление", "Вы действительно хотите удалить запись?")
        if not first:
            return False
        second = messagebox.askyesno("Удаление", "Удаление необратимо. Подтвердите удаление.")
        return second

    def save_edited_row(self, edit_window, selected_item, entry_widgets, tree):
        """Сохранение отредактированных данных В БД"""
        try:
            if self.current_table == "teachers":
                new_fio = entry_widgets['fio'].get().strip()
                new_birth = entry_widgets['birth'].get().strip()
                new_subject = entry_widgets['subject'].get().strip()
                new_classes = entry_widgets['classes'].get().strip()

                if not new_fio:
                    raise EmptySearchError("Поле 'ФИО' не может быть пустым")

                if self.data_source["teachers"] == "database":
                    teacher_id = int(selected_item)
                    try:
                        success = self.data_manager.update_teacher_gui(
                            teacher_id, new_fio, new_subject, new_classes, new_birth
                        )
                    except ValueError as e:
                        raise FileOperationError(self.format_field_error("teachers", str(e)))
                    if not success:
                        raise FileOperationError("Не удалось обновить запись учителя")
                    self.refresh_data("teachers")
                else:
                    new_values = (new_fio, new_birth, new_subject, new_classes)
                    tree.item(selected_item, values=new_values)
                    self.sync_table_from_tree("teachers")

            elif self.current_table == "students":
                new_fio = entry_widgets['fio'].get().strip()
                new_class = entry_widgets['class'].get().strip()
                new_birth = entry_widgets['birth'].get().strip()

                if not new_fio:
                    raise EmptySearchError("Поле 'ФИО' не может быть пустым")

                if self.data_source["students"] == "database":
                    student_id = int(selected_item)
                    try:
                        success = self.data_manager.update_student_gui(student_id, new_fio, new_class, new_birth)
                    except ValueError as e:
                        raise FileOperationError(self.format_field_error("students", str(e)))
                    if not success:
                        raise FileOperationError("Не удалось обновить запись ученика")
                    self.refresh_data("students")
                    self.refresh_data("grades")
                else:
                    new_values = (new_fio, new_birth, new_class)
                    tree.item(selected_item, values=new_values)
                    self.sync_table_from_tree("students")

            else:
                new_fio = entry_widgets['fio'].get().strip()
                new_subject = entry_widgets['subject'].get().strip()
                new_grade = entry_widgets['grade'].get().strip()

                if not new_fio or not new_subject or not new_grade:
                    raise EmptySearchError("Все поля должны быть заполнены")

                if self.data_source["grades"] == "database":
                    grade_id = int(selected_item)
                    current_grade_values = tree.item(selected_item, 'values')
                    current_fio = current_grade_values[0] if current_grade_values else ""
                    
                    try:
                        success = self.data_manager.update_grade_gui(grade_id, new_fio, new_subject, new_grade)
                        if not success:
                            raise FileOperationError("Не удалось обновить запись об оценке")
                    except ValueError as e:
                        raise FileOperationError(self.format_field_error("grades", str(e)))

                    if current_fio != new_fio:
                        self.refresh_data("students")
                    self.refresh_data("grades")
                else:
                    current_grade_values = tree.item(selected_item, 'values')
                    current_class = current_grade_values[3] if len(current_grade_values) > 3 else ""
                    new_values = (new_fio, new_subject, new_grade, current_class)
                    tree.item(selected_item, values=new_values)
                    self.sync_table_from_tree("grades")

            edit_window.destroy()
            messagebox.showinfo("Успех", "Данные успешно обновлены")

        except EmptySearchError as e:
            messagebox.showwarning("Ошибка заполнения", str(e))
        except FileOperationError as e:
            messagebox.showerror("Ошибка", str(e))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при сохранении: {str(e)}")

    def on_edit_click(self, _):
        """Обработчик событий для кнопки "Редактировать"""
        try:
            self.edit_selected_row()

        except NoDataForEdit as e:
            messagebox.showwarning("Редактирование", str(e))
        except FileOperationError as e:
            messagebox.showerror("Ошибка операции с файлом", str(e))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка при редактировании файла: {str(e)}")

    def on_delete_click(self, _):
        """Обработчик событий для кнопки "Удалить"""
        try:
            if self.current_table == "teachers":
                selected_item = self.teachers_tree.selection()
                if not selected_item:
                    messagebox.showwarning("Удаление", "Выберите запись для удаления")
                    return
                if not self.confirm_delete():
                    return
                self.handle_delete(selected_item)
            elif self.current_table == "students":
                selected_item = self.students_tree.selection()
                if not selected_item:
                    messagebox.showwarning("Удаление", "Выберите запись для удаления")
                    return
                if not self.confirm_delete():
                    return
                self.handle_delete(selected_item)
            else:
                selected_item = self.grades_tree.selection()
                if not selected_item:
                    messagebox.showwarning("Удаление", "Выберите запись для удаления")
                    return
                if not self.confirm_delete():
                    return
                self.handle_delete(selected_item)

            messagebox.showinfo("Удаление", "Запись успешно удалена")

        except FileOperationError as e:
            messagebox.showerror("Ошибка операции с файлом", str(e))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка при удалении файла: {str(e)}")

    def on_default_click(self, _):
        """Обработчик событий для нажатия любой кнопки"""
        pass

    def create_control_panel(self):
        """Создание панели управления"""
        control_frame = tk.Frame(self.root, bg='#f0f0f0')
        control_frame.pack(fill="x", padx=10, pady=5)

        top_controls = tk.Frame(control_frame, bg='#f0f0f0')
        top_controls.pack(fill="x", expand=True)

        tk.Label(top_controls, text="Просмотр:", bg='#f0f0f0', font=('Arial', 9)).grid(row=0, column=0, padx=(0, 5), sticky="w")

        self.table_var = tk.StringVar(value="Учителя")
        self.table_combo = ttk.Combobox(top_controls,
                                        textvariable=self.table_var,
                                        values=["Учителя", "Ученики", "Оценки"],
                                        state="readonly",
                                        width=12)
        self.table_combo.grid(row=0, column=1, padx=(0, 20), pady=2, sticky="w")
        self.table_combo.bind('<<ComboboxSelected>>', self.on_table_change)

        tk.Label(top_controls, text="Поиск:", bg='#f0f0f0', font=('Arial', 9)).grid(row=0, column=2, padx=(0, 5), sticky="w")

        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(top_controls, textvariable=self.search_var, width=20)
        self.search_entry.grid(row=0, column=3, padx=(0, 5), pady=2, sticky="w")
        self.search_entry.bind('<KeyRelease>', self.on_search)

        self.search_btn = ttk.Button(top_controls, text="Найти", command=self.on_search_button)
        self.search_btn.grid(row=0, column=4, padx=(5, 0), pady=2, sticky="w")

        tk.Label(top_controls, text="Сортировка:", bg='#f0f0f0', font=('Arial', 9)).grid(row=0, column=5, padx=(20, 5), sticky="w")

        self.sort_var = tk.StringVar()
        self.sort_combo = ttk.Combobox(top_controls,
                                       textvariable=self.sort_var,
                                       state="readonly",
                                       width=15)
        self.sort_combo.grid(row=0, column=6, padx=(0, 5), pady=2, sticky="w")
        self.sort_combo.bind('<<ComboboxSelected>>', self.on_sort_change)

        self.reset_btn = ttk.Button(top_controls, text="Сбросить", command=self.reset_filters)
        self.reset_btn.grid(row=0, column=7, padx=(10, 0), pady=2, sticky="w")

        self.info_btn = ttk.Button(top_controls, text="Инфо для завуча", command=self.open_info_center)
        self.info_btn.grid(row=0, column=8, padx=(20, 0), pady=2, sticky="e")

        top_controls.columnconfigure(3, weight=1)

        return control_frame

    def open_info_center(self):
        """Открывает окно с дополнительной информацией для завуча"""
        if self.info_window and tk.Toplevel.winfo_exists(self.info_window):
            self.info_window.lift()
            return

        self.info_window = tk.Toplevel(self.root)
        self.info_window.title("Информация для завуча")
        self.info_window.geometry("560x520")
        self.info_window.transient(self.root)
        self.info_window.grab_set()
        self.info_window.protocol("WM_DELETE_WINDOW", self.close_info_center)

        notebook = ttk.Notebook(self.info_window)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.build_subject_tab(notebook)
        self.build_teacher_tab(notebook)
        self.build_students_tab(notebook)
        self.build_performance_tab(notebook)

        refresh_btn = ttk.Button(self.info_window, text="Обновить данные", command=self.refresh_info_center_data)
        refresh_btn.pack(pady=(0, 10))

        self.refresh_info_center_data()

    def close_info_center(self):
        if self.info_window and tk.Toplevel.winfo_exists(self.info_window):
            self.info_window.destroy()
        self.info_window = None

    def build_subject_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=10)
        notebook.add(frame, text="Предметы")

        ttk.Label(frame, text="Предмет:").grid(row=0, column=0, sticky="w")
        self.subject_query_var = tk.StringVar()
        self.subject_combo = ttk.Combobox(frame, textvariable=self.subject_query_var, width=35)
        self.subject_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        subject_btn = ttk.Button(frame, text="Показать", command=self.handle_subject_lookup)
        subject_btn.grid(row=0, column=2, padx=5, pady=5)

        self.subject_result_box = tk.Listbox(frame, height=8)
        self.subject_result_box.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=(10, 0))

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)

    def build_teacher_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=10)
        notebook.add(frame, text="Учителя")

        ttk.Label(frame, text="Учитель:").grid(row=0, column=0, sticky="w")
        self.teacher_query_var = tk.StringVar()
        self.teacher_combo = ttk.Combobox(frame, textvariable=self.teacher_query_var, width=35)
        self.teacher_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        teacher_btn = ttk.Button(frame, text="Показать классы", command=self.handle_teacher_classes_lookup)
        teacher_btn.grid(row=0, column=2, padx=5, pady=5)

        self.teacher_classes_var = tk.StringVar(value="Классы: —")
        ttk.Label(frame, textvariable=self.teacher_classes_var, wraplength=400, justify="left").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(10, 0))

        frame.columnconfigure(1, weight=1)

    def build_students_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=10)
        notebook.add(frame, text="Ученики")

        self.total_students_var = tk.StringVar(value="Всего учеников: —")
        ttk.Label(frame, textvariable=self.total_students_var, font=('Arial', 10, 'bold')).grid(
            row=0, column=0, columnspan=3, sticky="w")

        ttk.Label(frame, text="Класс:").grid(row=1, column=0, sticky="w", pady=(15, 0))
        self.class_query_var = tk.StringVar()
        self.student_class_combo = ttk.Combobox(frame, textvariable=self.class_query_var, width=15)
        self.student_class_combo.grid(row=1, column=1, padx=5, pady=(15, 0), sticky="w")

        class_btn = ttk.Button(frame, text="Посчитать", command=self.handle_class_count_lookup)
        class_btn.grid(row=1, column=2, padx=5, pady=(15, 0))

        self.class_count_var = tk.StringVar(value="Ученики в выбранном классе: —")
        ttk.Label(frame, textvariable=self.class_count_var).grid(row=2, column=0, columnspan=3, sticky="w", pady=(10, 0))

    def build_performance_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=10)
        notebook.add(frame, text="Успеваемость")

        self.good_count_var = tk.StringVar(value="Отличники: —")
        self.bad_count_var = tk.StringVar(value="Двоечники: —")

        ttk.Label(frame, textvariable=self.good_count_var, font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky="w")
        ttk.Label(frame, textvariable=self.bad_count_var, font=('Arial', 10, 'bold')).grid(row=0, column=1, sticky="w", padx=(20, 0))

        ttk.Label(frame, text="Список отличников").grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Label(frame, text="Список двоечников").grid(row=1, column=1, sticky="w", pady=(10, 0))

        self.good_students_list = tk.Listbox(frame, height=8)
        self.good_students_list.grid(row=2, column=0, sticky="nsew", pady=(5, 0))

        self.bad_students_list = tk.Listbox(frame, height=8)
        self.bad_students_list.grid(row=2, column=1, sticky="nsew", pady=(5, 0), padx=(20, 0))

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(2, weight=1)

    def handle_subject_lookup(self):
        subject = self.subject_query_var.get().strip() if hasattr(self, 'subject_query_var') else ""
        if not subject:
            messagebox.showwarning("Поиск предмета", "Выберите или введите предмет.")
            return

        teachers = self.data_manager.get_teachers_by_subject(subject)
        self.subject_result_box.delete(0, tk.END)

        if teachers:
            for teacher in teachers:
                self.subject_result_box.insert(tk.END, teacher)
        else:
            self.subject_result_box.insert(tk.END, "Нет данных по выбранному предмету")

    def handle_teacher_classes_lookup(self):
        teacher = self.teacher_query_var.get().strip() if hasattr(self, 'teacher_query_var') else ""
        if not teacher:
            messagebox.showwarning("Поиск учителя", "Введите или выберите учителя.")
            return

        classes = self.data_manager.get_teacher_classes(teacher)
        if classes:
            self.teacher_classes_var.set(f"Классы: {', '.join(classes)}")
        else:
            self.teacher_classes_var.set("Классы: нет данных")

    def handle_class_count_lookup(self):
        class_name = self.class_query_var.get().strip() if hasattr(self, 'class_query_var') else ""
        if not class_name:
            messagebox.showwarning("Поиск класса", "Введите или выберите класс.")
            return

        count = self.data_manager.get_student_count(class_name)
        self.class_count_var.set(f"Ученики в классе {class_name}: {count}")

    def refresh_info_center_data(self):
        if not self.info_window or not tk.Toplevel.winfo_exists(self.info_window):
            return

        subjects = self.data_manager.get_subject_list()
        if hasattr(self, 'subject_combo'):
            self.subject_combo['values'] = subjects

        teachers = self.data_manager.get_teacher_list()
        if hasattr(self, 'teacher_combo'):
            self.teacher_combo['values'] = teachers

        classes = self.data_manager.get_class_list()
        if hasattr(self, 'student_class_combo'):
            self.student_class_combo['values'] = classes

        total_students = self.data_manager.get_student_count()
        if hasattr(self, 'total_students_var'):
            self.total_students_var.set(f"Всего учеников: {total_students}")

        report = self.data_manager.get_academic_report()
        if hasattr(self, 'good_count_var'):
            self.good_count_var.set(f"Отличники: {len(report.get('good_students', []))}")
        if hasattr(self, 'bad_count_var'):
            self.bad_count_var.set(f"Двоечники: {len(report.get('bad_students', []))}")

        if hasattr(self, 'good_students_list'):
            self.populate_student_listbox(self.good_students_list, report.get('good_students', []))
        if hasattr(self, 'bad_students_list'):
            self.populate_student_listbox(self.bad_students_list, report.get('bad_students', []))

    def populate_student_listbox(self, listbox, students):
        listbox.delete(0, tk.END)
        if not students:
            listbox.insert(tk.END, "Нет данных")
            return
        for student in students:
            listbox.insert(tk.END, self.format_student_record(student))

    def format_student_record(self, student_row):
        last_name, first_name, middle_name, class_name = student_row
        fio = " ".join(part for part in [last_name, first_name, middle_name] if part)
        if isinstance(class_name, (list, tuple)):
            class_str = ", ".join(class_name)
        else:
            class_str = class_name or ""
        return f"{fio} ({class_str})" if class_str else fio

    def on_search_button(self):
        """Обработчик нажатия кнопки поиска с проверкой пустого поле"""
        try:
            search_term = self.search_var.get().strip()
            self.validate_search_input(search_term)
            self.perform_search(search_term)
        except EmptySearchError as e:
            messagebox.showwarning("Пустой поиск", str(e))
            self.search_entry.focus_set()
        except Exception as e:
            messagebox.showerror("Ошибка поиска", f"Произошла ошибка при поиске: {str(e)}")

    def get_tree_and_data(self):
        """Возвращает виджет Treeview и копию исходных данных."""
        if self.current_table == "teachers":
            return self.teachers_tree, self.original_teachers_data
        elif self.current_table == "students":
            return self.students_tree, self.original_students_data
        else:
            return self.grades_tree, self.original_grades_data

    def populate_tree(self, tree, data_rows):
        """Перерисовывает содержимое Treeview."""
        for item in tree.get_children():
            tree.delete(item)

        for row in data_rows:
            row_id = row.get("id")
            if row_id is not None:
                tree.insert("", "end", iid=str(row_id), values=row["values"])
            else:
                tree.insert("", "end", values=row["values"])

    def sync_table_from_tree(self, table):
        """Сохраняет текущие значения из Treeview в кэш."""
        if table == "teachers":
            tree = self.teachers_tree
            rows = [{"id": None, "values": tree.item(item, 'values')} for item in tree.get_children()]
            self.teachers_data = rows
            self.original_teachers_data = [row.copy() for row in rows]
        elif table == "students":
            tree = self.students_tree
            rows = [{"id": None, "values": tree.item(item, 'values')} for item in tree.get_children()]
            self.students_data = rows
            self.original_students_data = [row.copy() for row in rows]
        else:
            tree = self.grades_tree
            rows = [{"id": None, "student_id": None, "values": tree.item(item, 'values')} for item in tree.get_children()]
            self.grades_data = rows
            self.original_grades_data = [row.copy() for row in rows]

    def handle_delete(self, selected_items):
        """Удаляет строки из таблицы и БД (если нужно)."""
        if self.current_table == "teachers":
            tree = self.teachers_tree
            source = self.data_source["teachers"]
            if source == "database":
                for item in selected_items:
                    success = self.data_manager.delete_teacher_gui(int(item))
                    if not success:
                        raise FileOperationError("Не удалось удалить запись учителя")
                self.refresh_data("teachers")
            else:
                for item in selected_items:
                    tree.delete(item)
                self.sync_table_from_tree("teachers")

        elif self.current_table == "students":
            tree = self.students_tree
            source = self.data_source["students"]
            if source == "database":
                for item in selected_items:
                    success = self.data_manager.delete_student_gui(int(item))
                    if not success:
                        raise FileOperationError("Не удалось удалить запись ученика")
                self.refresh_data("students")
            else:
                for item in selected_items:
                    tree.delete(item)
                self.sync_table_from_tree("students")

        else:
            tree = self.grades_tree
            source = self.data_source["grades"]
            if source == "database":
                for item in selected_items:
                    success = self.data_manager.delete_grade_gui(int(item))
                    if not success:
                        raise FileOperationError("Не удалось удалить запись об оценке")
                self.refresh_data("grades")
            else:
                for item in selected_items:
                    tree.delete(item)
                self.sync_table_from_tree("grades")

    def perform_search(self, search_term):
        """Выполняет поиск по таблице"""
        self.logger.info(f"Выполнение поиска в таблице {self.current_table}: '{search_term}'")

        tree, data = self.get_tree_and_data()
        self.logger.debug(f"Поиск среди {len(data)} записей")

        filtered = []
        search_term_lower = search_term.lower()

        for row in data:
            if any(search_term_lower in str(field).lower() for field in row["values"]):
                filtered.append(row)

        self.logger.info(f"Найдено {len(filtered)} записей по запросу '{search_term}'")
        self.populate_tree(tree, filtered)

    def on_search(self, event):
        """Обработчик поиска по таблице при вводе текста"""
        try:
            search_term = self.search_var.get().strip()

            if not search_term:
                self.reset_filters()
                return

            self.validate_search_input(search_term)
            self.perform_search(search_term)

        except EmptySearchError:
            pass
        except Exception as e:
            messagebox.showerror("Ошибка поиска", f"Произошла ошибка при поиске: {str(e)}")

    def show_table(self, table_type):
        """Переключает отображение между таблицами учителей и учеников"""
        for frame in [self.teachers_frame, self.students_frame, self.grades_frame]:
            frame.pack_forget()

        if table_type == "teachers":
            self.teachers_frame.pack(fill="both", expand=True)
            self.current_table = "teachers"
            self.update_sort_options(self.teachers_sort_options)
        elif table_type == "students":
            self.students_frame.pack(fill="both", expand=True)
            self.current_table = "students"
            self.update_sort_options(self.students_sort_options)
        else:
            self.grades_frame.pack(fill="both", expand=True)
            self.current_table = "grades"
            self.update_sort_options(self.grades_sort_options)

        self.current_file = None

    def update_sort_options(self, options):
        """Обновляет доступные опции для сортировки текущей таблицы"""
        self.sort_combo['values'] = options
        if options:
            self.sort_var.set(options[0])
        else:
            self.sort_var.set("")

    def on_table_change(self, _):
        """Обработчик изменения выбранной таблицы"""
        selection = self.table_var.get()
        if selection == "Учителя":
            self.show_table("teachers")
        elif selection == "Ученики":
            self.show_table("students")
        else:
            self.show_table("grades")
        self.reset_filters()

    def on_sort_change(self, _):
        """Изменение критерия сортировки"""
        self.apply_sorting()

    def apply_sorting(self):
        """Применяет сортировку к текущей таблице"""
        sort_by = self.sort_var.get()
        if not sort_by:
            return

        if self.current_table == "teachers":
            tree = self.teachers_tree
            sort_map = self.teacher_sort_map
        elif self.current_table == "students":
            tree = self.students_tree
            sort_map = self.student_sort_map
        else:
            tree = self.grades_tree
            sort_map = self.grade_sort_map

        column_info = sort_map.get(sort_by)
        if not column_info:
            return
        column_index, reverse = column_info
        self.sort_treeview(tree, column_index, reverse)

    def parse_single_class(self, class_str):
        """Парсинг строки с классами для более точной сортировки"""
        if not class_str:
            return 0, ''

        class_str = str(class_str).strip().upper()

        digits = ''
        letters = ''

        for char in class_str:
            if char.isdigit():
                digits += char
            else:
                letters += char

        class_num = int(digits) if digits else 0

        return class_num, letters

    def parse_teacher_classes(self, classes_str):
        """Разбитие строки для точной сортировки учителей по классам"""
        if not classes_str:
            return 0, classes_str

        classes_str = str(classes_str).strip().upper()

        numbers = []
        current_number = ''

        for char in classes_str:
            if char.isdigit():
                current_number += char
            else:
                if current_number:
                    numbers.append(int(current_number))
                    current_number = ''

        if current_number:
            numbers.append(int(current_number))

        if numbers:
            min_class = min(numbers)
            return min_class, classes_str
        else:
            return 0, classes_str

    def get_sort_key(self, value, column_index):
        """Возвращает ключ сортировки для значения в зависимости от типа колонки"""
        if value is None:
            value_str = ""
        else:
            value_str = str(value).strip()

        if self.current_table in ("teachers", "students") and column_index == 1:
            try:
                if value_str:
                    dt = datetime.datetime.strptime(value_str, "%d.%m.%Y")
                    return (dt,)
                else:
                    return (datetime.datetime.min,)
            except ValueError:
                return (value_str.lower() if value_str else "",)

        if self.current_table == "students" and column_index == 2:
            return self.parse_single_class(value_str)

        if self.current_table == "teachers" and column_index == 3:
            return self.parse_teacher_classes(value_str)

        if self.current_table == "grades" and column_index == 3:
            return self.parse_single_class(value_str)

        if self.current_table == "grades" and column_index == 2:
            try:
                if value_str:
                    return (int(value_str),)
                else:
                    return (0,)
            except (TypeError, ValueError):
                return (value_str.lower() if value_str else "",)

        return (value_str.lower() if value_str else "",)


    def on_column_sort(self, table, column_id):
        """Переключает направление сортировки при клике по заголовку."""
        if table == "teachers":
            tree = self.teachers_tree
        elif table == "students":
            tree = self.students_tree
        else:
            tree = self.grades_tree

        state = self.sort_state[table]
        reverse = state.get(column_id, False)
        self.sort_treeview(tree, column_id, reverse)
        state[column_id] = not reverse

    def sort_treeview(self, tree, column, reverse=False):
        """Выполняет сортировку данных по указанной колонке"""
        if isinstance(column, str):
            columns = tree['columns']
            if column in columns:
                column_index = columns.index(column)
            else:
                return
        else:
            column_index = column

        columns = tree['columns']
        if column_index < 0 or column_index >= len(columns):
            return
        column_id = columns[column_index]

        items = []
        for item in tree.get_children(''):
            value = tree.set(item, column_id)
            sort_key = self.get_sort_key(value, column_index)
            items.append((sort_key, item))

        try:
            items.sort(key=lambda x: x[0], reverse=reverse)
        except (TypeError, ValueError):
            items.sort(key=lambda x: str(x[0]).lower(), reverse=reverse)

        for index, (_, item) in enumerate(items):
            tree.move(item, '', index)

    def reset_filters(self):
        """Сбрасывает все фильтры и сортировку к исходному состоянию"""
        self.logger.info(f"Сброс фильтров и сортировки для таблицы {self.current_table}")
        self.search_var.set("")
        tree, data = self.get_tree_and_data()
        self.logger.debug(f"Восстановлено {len(data)} записей")
        self.populate_tree(tree, data)

        if self.current_table == "teachers" and self.teachers_sort_options:
            self.sort_var.set(self.teachers_sort_options[0])
            self.apply_sorting()
        elif self.current_table == "students" and self.students_sort_options:
            self.sort_var.set(self.students_sort_options[0])
            self.apply_sorting()
        elif self.current_table == "grades" and self.grades_sort_options:
            self.sort_var.set(self.grades_sort_options[0])
            self.apply_sorting()

    def setup_report_generator(self):
        """Инициализация генератора отчетов"""
        self.report_generator = ReportGenerator()

    def generate_pdf_report(self):
        """Генерация PDF отчета"""
        try:
            if self.current_table == "teachers":
                data = [row["values"] for row in self.original_teachers_data]
                report_type = "Учителя"
            elif self.current_table == "students":
                data = [row["values"] for row in self.original_students_data]
                report_type = "Ученики"
            else:
                data = [row["values"] for row in self.original_grades_data]
                report_type = "Оценки"

            if not data:
                messagebox.showwarning("Генерация отчета", "Нет данных для отчета")
                return

            file_path = filedialog.asksaveasfilename(
                title="Сохранить PDF отчет",
                defaultextension=".pdf",
                filetypes=[("PDF файлы", "*.pdf")]
            )

            if not file_path:
                return

            success = self.report_generator.generate_pdf_report(data, report_type, file_path)

            if success:
                messagebox.showinfo("Успех", "PDF отчет сохранен!")

        except FileOperationError as e:
            messagebox.showerror("Ошибка", str(e))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка генерации отчета: {str(e)}")

    def on_generate_pdf(self, _=None):
        """Обработчик кнопки PDF"""
        self.generate_pdf_report()


"""
Запуск программы, создание главного окна, установка размера окна
"""
if __name__ == "__main__":
    app_logger.info("Запуск основного приложения")
    app_logger.debug("Создание главного окна Tkinter")

    root = tk.Tk()
    app = SchoolApp(root)
    root.geometry("950x650")

    app_logger.info("Запуск главного цикла приложения")
    root.mainloop()

    app_logger.info("Приложение завершено")
