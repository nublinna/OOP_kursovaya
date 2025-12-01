"""
Программа School App создана для работы с базой учителей и учеников.

Nika Sheshko
"""

___author__ = "Nika Sheshko"

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import xml.etree.ElementTree as ET
import datetime
import os
from xhtml2pdf.default import DEFAULT_FONT
from xml.dom import minidom
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from database import SchoolDatabase
from models import Teacher, Student, GradeRecord


class SchoolDataManager:
    """Класс для интеграции БД с GUI - соответствует требованиям ООП"""

    def __init__(self):
        self.db = SchoolDatabase()
        self._setup_initial_data()

    def _setup_initial_data(self):
        """Инициализация начальных данных при первом запуске"""
        try:
            demo_teachers, demo_students, demo_grades = self._get_demo_data()
            self._seed_teachers_if_needed(demo_teachers)
            self._seed_students_if_needed(demo_students)
            self._seed_grades_if_needed(demo_grades)
        except Exception as e:
            print(f"Ошибка инициализации БД: {e}")

    def _is_database_empty(self):
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

    def _get_demo_data(self):
        """Возвращает наборы демо-данных"""
        demo_teachers = [
            {"last_name": "Иванова", "first_name": "Анна", "middle_name": "Петровна",
             "subject": "Математика", "classes": ["5А", "6Б", "9В"]},
            {"last_name": "Петров", "first_name": "Сергей", "middle_name": "Владимирович",
             "subject": "Физика", "classes": ["7А", "8Б", "10А"]},
            {"last_name": "Сидорова", "first_name": "Ольга", "middle_name": "Михайловна",
             "subject": "Литература", "classes": ["5А", "6А", "7А", "8А"]},
        ]

        demo_students = [
            {"last_name": "Алексеев", "first_name": "Александр", "middle_name": "Сергеевич",
             "class_name": ["5А"]},
            {"last_name": "Борисова", "first_name": "Екатерина", "middle_name": "Игоревна",
             "class_name": ["6Б"]},
            {"last_name": "Васильев", "first_name": "Максим", "middle_name": "Дмитриевич",
             "class_name": ["7А"]},
            {"last_name": "Григорьева", "first_name": "София", "middle_name": "Андреевна",
             "class_name": ["8Б"]},
        ]

        demo_grades = [
            ("Алексеев Александр Сергеевич", "Математика", 5),
            ("Борисова Екатерина Игоревна", "Физика", 4),
            ("Васильев Максим Дмитриевич", "Литература", 3),
            ("Григорьева София Андреевна", "Информатика", 5),
        ]

        return demo_teachers, demo_students, demo_grades

    def _get_table_count(self, table_name):
        """Возвращает количество записей в таблице"""
        self.db.DB_CURSOR.execute(f"SELECT COUNT(*) FROM {table_name}")
        return self.db.DB_CURSOR.fetchone()[0]

    def _seed_teachers_if_needed(self, demo_teachers):
        """Добавляет демо-учителей, если таблица пуста"""
        if self._get_table_count("teachers") > 0:
            return

        for teacher in demo_teachers:
            self.db.add_teacher(
                teacher["last_name"],
                teacher["first_name"],
                teacher["subject"],
                teacher["classes"],
                teacher["middle_name"]
            )

    def _seed_students_if_needed(self, demo_students):
        """Добавляет демо-учеников, если таблица пуста"""
        if self._get_table_count("students") > 0:
            return

        for student in demo_students:
            self.db.add_student(
                student["last_name"],
                student["first_name"],
                student["class_name"],
                student["middle_name"]
            )

    def _build_student_index(self):
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

    def _seed_grades_if_needed(self, demo_grades):
        """Добавляет демо-оценки, если таблица пуста"""
        if self._get_table_count("grades") > 0:
            return

        student_index = self._build_student_index()

        for fio, subject, grade in demo_grades:
            student_id = student_index.get(fio)
            if student_id:
                self.db.add_grade(student_id, subject, grade)

    def _parse_fio(self, fio):
        """Разбивает ФИО на составные части"""
        parts = fio.split()
        last_name = parts[0] if len(parts) > 0 else ""
        first_name = parts[1] if len(parts) > 1 else ""
        middle_name = parts[2] if len(parts) > 2 else ""
        return last_name, first_name, middle_name

    def _split_classes(self, text):
        return [cls.strip() for cls in text.split(",") if cls.strip()]

    def _format_fio(self, last_name, first_name, middle_name):
        return " ".join(part for part in [last_name, first_name, middle_name] if part)

    def get_subject_list(self):
        try:
            return self.db.get_subject_list()
        except Exception as e:
            print(f"Ошибка получения списка предметов: {e}")
            return []

    def get_teacher_list(self):
        try:
            teachers = self.db.get_teacher_fios()
            return [self._format_fio(*teacher).strip() for teacher in teachers]
        except Exception as e:
            print(f"Ошибка получения списка учителей: {e}")
            return []

    def get_class_list(self):
        try:
            return self.db.get_class_list()
        except Exception as e:
            print(f"Ошибка получения списка классов: {e}")
            return []

    def get_teachers_by_subject(self, subject):
        try:
            teachers = self.db.get_teachers_by_subject(subject)
            return [self._format_fio(*teacher).strip() for teacher in teachers]
        except Exception as e:
            print(f"Ошибка запроса учителей по предмету: {e}")
            return []

    def get_teacher_classes(self, fio):
        try:
            last_name, first_name, middle_name = self._parse_fio(fio)
            classes = self.db.get_teacher_classes_by_name(last_name, first_name, middle_name)
            return classes if classes else []
        except Exception as e:
            print(f"Ошибка получения классов учителя: {e}")
            return []

    def get_student_count(self, class_name=None):
        try:
            if class_name:
                class_name = class_name.strip()
            return self.db.get_students_count(class_name if class_name else None)
        except Exception as e:
            print(f"Ошибка получения количества учеников: {e}")
            return 0

    def get_all_teachers(self):
        """Получение всех учителей в формате для GUI"""
        try:
            rows = self.db.fetch_all_teachers()
            teachers = []
            for teacher_id, last_name, first_name, middle_name, subject, classes in rows:
                teacher = Teacher(last_name, first_name, middle_name, subject, classes or [])
                teachers.append({"id": teacher_id, "values": teacher.to_display_tuple()})
            return teachers
        except Exception as e:
            print(f"Ошибка получения учителей: {e}")
            return []

    def get_all_students(self):
        """Получение всех учеников в формате для GUI"""
        try:
            rows = self.db.fetch_all_students()
            result = []
            for student_id, last_name, first_name, middle_name, classes in rows:
                student = Student(last_name, first_name, middle_name, classes or [])
                result.append({"id": student_id, "values": student.to_display_tuple()})
            return result
        except Exception as e:
            print(f"Ошибка получения учеников: {e}")
            return []

    def get_all_grades(self):
        """Получение всех оценок для отображения"""
        try:
            rows = self.db.get_all_grades_rows()
            result = []
            for grade_id, student_id, last_name, first_name, middle_name, subject_name, grade in rows:
                fio = f"{last_name} {first_name} {middle_name}".strip()
                grade_obj = GradeRecord(student_id, subject_name, grade)
                result.append({
                    "id": grade_id,
                    "student_id": student_id,
                    "values": grade_obj.to_display_tuple(fio)
                })
            return result
        except Exception as e:
            print(f"Ошибка получения оценок: {e}")
            return []

    def add_teacher_gui(self, fio, subject, classes_str):
        """Добавление учителя из GUI"""
        try:
            last_name, first_name, middle_name = self._parse_fio(fio)
            classes = self._split_classes(classes_str)
            teacher = Teacher(last_name, first_name, middle_name, subject, classes)
            last, first, middle, subj, class_list = teacher.to_db_payload()
            self.db.add_teacher(last, first, subj, class_list, middle)
            return True
        except Exception as e:
            print(f"Ошибка добавления учителя: {e}")
            return False

    def add_student_gui(self, fio, class_name):
        """Добавление ученика из GUI"""
        try:
            last_name, first_name, middle_name = self._parse_fio(fio)
            classes = self._split_classes(class_name)
            student = Student(last_name, first_name, middle_name, classes)
            payload = student.to_db_payload()
            self.db.add_student(payload[0], payload[1], payload[3], payload[2])
            return True
        except Exception as e:
            print(f"Ошибка добавления ученика: {e}")
            return False

    def import_teachers(self, teachers_rows):
        imported = 0
        for row in teachers_rows:
            try:
                fio, subject, classes_str = row
            except ValueError:
                continue
            last_name, first_name, middle_name = self._parse_fio(fio)
            classes = self._split_classes(classes_str)

            if self.db.teacher_exists(last_name, first_name, middle_name, subject):
                continue

            self.db.add_teacher(last_name, first_name, subject, classes, middle_name)
            imported += 1
        return imported

    def import_students(self, student_rows):
        imported = 0
        for row in student_rows:
            try:
                fio, class_str = row
            except ValueError:
                continue
            last_name, first_name, middle_name = self._parse_fio(fio)
            classes = self._split_classes(class_str)
            self.db.add_student(last_name, first_name, classes, middle_name)
            imported += 1
        return imported

    def import_grades(self, grade_rows):
        imported = 0
        for row in grade_rows:
            if len(row) < 3:
                continue
            fio, subject, grade_value = row
            last_name, first_name, middle_name = self._parse_fio(fio)
            student_id = self.db.find_student_id(last_name, first_name, middle_name)
            if not student_id:
                student_id = self.db.add_student(last_name, first_name, [], middle_name)
            try:
                grade_int = int(grade_value)
            except ValueError:
                continue
            self.db.add_grade(student_id, subject, grade_int)
            imported += 1
        return imported

    def update_teacher_gui(self, teacher_id, new_fio, new_subject, new_classes_str):
        """Обновление учителя из GUI"""
        try:
            last_name, first_name, middle_name = self._parse_fio(new_fio)
            classes = [cls.strip() for cls in new_classes_str.split(",") if cls.strip()]
            self.db.update_teachers(teacher_id, last_name, first_name, new_subject, classes, middle_name)
            return True
        except Exception as e:
            print(f"Ошибка обновления учителя: {e}")
            return False

    def delete_teacher_gui(self, teacher_id):
        """Удаление учителя из GUI"""
        try:
            self.db.delete_teacher(teacher_id)
            return True
        except Exception as e:
            print(f"Ошибка удаления учителя: {e}")
            return False

    def update_student_gui(self, student_id, new_fio, new_class_str):
        """Обновление ученика из GUI"""
        try:
            last_name, first_name, middle_name = self._parse_fio(new_fio)
            classes = [cls.strip() for cls in new_class_str.split(",") if cls.strip()]
            self.db.update_students(student_id, last_name, first_name, classes, middle_name)
            return True
        except Exception as e:
            print(f"Ошибка обновления ученика: {e}")
            return False

    def delete_student_gui(self, student_id):
        """Удаление ученика из GUI"""
        try:
            self.db.delete_student(student_id)
            return True
        except Exception as e:
            print(f"Ошибка удаления ученика: {e}")
            return False

    def update_grade_gui(self, grade_id, fio, subject_name, grade_value):
        """Обновление оценки из GUI"""
        try:
            grade_int = int(grade_value)
            if grade_int < 1 or grade_int > 5:
                raise ValueError("Оценка должна быть от 1 до 5")

            last_name, first_name, middle_name = self._parse_fio(fio)
            student_id = self.db.find_student_id(last_name, first_name, middle_name)
            if not student_id:
                raise ValueError("Указанный ученик не найден в базе")

            self.db.update_grade(grade_id, student_id, subject_name, grade_int)
            return True
        except Exception as e:
            print(f"Ошибка обновления оценки: {e}")
            return False

    def delete_grade_gui(self, grade_id):
        """Удаление оценки из GUI"""
        try:
            self.db.delete_grade(grade_id)
            return True
        except Exception as e:
            print(f"Ошибка удаления оценки: {e}")
            return False

    def get_academic_report(self):
        """Получение отчета об успеваемости - соответствует заданию"""
        try:
            return self.db.get_grades()
        except Exception as e:
            print(f"Ошибка получения отчета: {e}")
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
    """Класс для генерации отчетов в PDF формате"""

    def __init__(self):
        if not os.path.exists('templates'):
            os.makedirs('templates')
        self.env = Environment(loader=FileSystemLoader('templates'))

    def generate_pdf_report(self, data, report_type, output_file):
        """Генерация PDF отчета с использованием HTML шаблона"""
        try:
            template = self.env.get_template('report_template_pdf.html')

            if report_type == "Учителя":
                headers = ["ФИО", "Предмет", "Классы"]
            elif report_type == "Ученики":
                headers = ["ФИО", "Класс"]
            else:
                headers = ["ФИО", "Предмет", "Оценка"]

            font_path = os.path.abspath("fonts").replace("\\", "/")

            html_content = template.render(
                report_type=report_type,
                generation_date=datetime.datetime.now().strftime('%d.%m.%Y %H:%M'),
                headers=headers,
                data=data,
                total_count=len(data),
                font_path=font_path
            )

            return self._generate_pdf_from_html_template(html_content, output_file)

        except Exception as e:
            raise FileOperationError(f"Ошибка при генерации PDF отчета: {str(e)}")

    def _generate_pdf_from_html_template(self, html_content, output_file):
        """Создание PDF из HTML контента"""
        try:
            font_folder = os.path.abspath("fonts")
            pdfmetrics.registerFont(TTFont("DejaVuSans", os.path.join(font_folder, "DejaVuSans.ttf")))
            pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", os.path.join(font_folder, "DejaVuSans-Bold.ttf")))

            DEFAULT_FONT["helvetica"] = "DejaVuSans"
            DEFAULT_FONT["Helvetica"] = "DejaVuSans"
            DEFAULT_FONT["helvetica-bold"] = "DejaVuSans-Bold"
            DEFAULT_FONT["Helvetica-Bold"] = "DejaVuSans-Bold"

            with open(output_file, "wb") as output_file_obj:
                pisa_status = pisa.CreatePDF(
                    html_content,
                    dest=output_file_obj,
                    encoding='utf-8'
                )

            if pisa_status.err:
                raise Exception(f"Ошибка создания PDF: {pisa_status.err}")

            return True

        except Exception as e:
            raise FileOperationError(f"Ошибка при создании PDF: {str(e)}")


class SchoolApp:
    """
    Основной класс приложения.
    Здесь описаны все окна, кнопки и обработчики.
    """

    def __init__(self, root):
        """Создаёт окно, настраивает виджеты и загружает данные."""
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

        self.data_manager = SchoolDataManager()

        self.setup_styles()
        self.setup_report_generator()

        self.top_frame = self.create_top_panel()
        self.control_frame = self.create_control_panel()

        self.table_frame = tk.Frame(root, bg='#f0f0f0')
        self.table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.create_teachers_table()
        self.create_students_table()
        self.create_grades_table()

        self.show_table("teachers")

    def create_teachers_table(self):
        """Создаёт таблицу учителей и заполняет её."""
        self.teachers_frame = tk.Frame(self.table_frame, bg='#f0f0f0')

        columns = ("ФИО", "Предмет", "Классы")
        self.teachers_tree = ttk.Treeview(self.teachers_frame, columns=columns, show="headings")

        for col in columns:
            self.teachers_tree.heading(col, text=col,
                                       command=lambda c=col: self.sort_treeview(self.teachers_tree, c))
            self.teachers_tree.column(col, width=200)

        # ЗАГРУЖАЕМ ДАННЫЕ ИЗ БД ВМЕСТО ФИКСИРОВАННЫХ ДАННЫХ
        self.teachers_data = self.data_manager.get_all_teachers()

        for teacher in self.teachers_data:
            self.teachers_tree.insert("", "end", iid=str(teacher["id"]), values=teacher["values"])

        scrollbar = ttk.Scrollbar(self.teachers_frame, orient="vertical", command=self.teachers_tree.yview)
        self.teachers_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.teachers_tree.pack(side="left", fill="both", expand=True)

        self.original_teachers_data = [row.copy() for row in self.teachers_data]
        self.teachers_sort_options = ["ФИО", "Предмет", "Классы"]
        self.data_source["teachers"] = "database"

    def create_students_table(self):
        """Создаёт таблицу учеников и заполняет её."""
        self.students_frame = tk.Frame(self.table_frame, bg='#f0f0f0')

        columns = ("ФИО", "Класс")
        self.students_tree = ttk.Treeview(self.students_frame, columns=columns, show="headings")

        for col in columns:
            self.students_tree.heading(col, text=col,
                                       command=lambda c=col: self.sort_treeview(self.students_tree, c))
            self.students_tree.column(col, width=300)

        # ЗАГРУЖАЕМ ДАННЫЕ ИЗ БД ВМЕСТО ФИКСИРОВАННЫХ ДАННЫХ
        self.students_data = self.data_manager.get_all_students()

        for student in self.students_data:
            self.students_tree.insert("", "end", iid=str(student["id"]), values=student["values"])

        scrollbar = ttk.Scrollbar(self.students_frame, orient="vertical", command=self.students_tree.yview)
        self.students_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.students_tree.pack(side="left", fill="both", expand=True)

        self.original_students_data = [row.copy() for row in self.students_data]
        self.students_sort_options = ["ФИО", "Класс"]
        self.data_source["students"] = "database"

    def create_grades_table(self):
        """Создаёт таблицу оценок и заполняет её."""
        self.grades_frame = tk.Frame(self.table_frame, bg='#f0f0f0')

        columns = ("ФИО", "Предмет", "Оценка")
        self.grades_tree = ttk.Treeview(self.grades_frame, columns=columns, show="headings")

        for col in columns:
            self.grades_tree.heading(col, text=col,
                                     command=lambda c=col: self.sort_treeview(self.grades_tree, c))
            self.grades_tree.column(col, width=200)

        self.grades_data = self.data_manager.get_all_grades()

        for grade in self.grades_data:
            self.grades_tree.insert("", "end", iid=str(grade["id"]), values=grade["values"])

        scrollbar = ttk.Scrollbar(self.grades_frame, orient="vertical", command=self.grades_tree.yview)
        self.grades_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.grades_tree.pack(side="left", fill="both", expand=True)

        self.original_grades_data = [row.copy() for row in self.grades_data]
        self.grades_sort_options = ["ФИО", "Предмет", "Оценка"]
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

        # Кнопка PDF отчета
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
            "Импорт в БД",
            "Редактировать",
            "Удалить"
        ]

        self.tool_buttons = {}

        icon_files = {
            "Сохранить": "save_button.png",
            "Открыть файл": "open_file.png",
            "Создать файл": "new_file.png",
            "Импорт в БД": "open_file.png",
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
        try:
            file_format = self.detect_file_format(filename)

            if file_format == 'xml':
                self.save_to_xml(filename)
            else:
                self.save_to_csv(filename)

            return True
        except Exception as e:
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
                    teacher_element.set("subject", values[1])
                    teacher_element.set("classes", values[2])
            elif self.current_table == "students":
                students_element = ET.SubElement(root, "students")

                for item in self.students_tree.get_children():
                    student_element = ET.SubElement(students_element, "student")
                    values = [self.students_tree.set(item, col) for col in self.students_tree["columns"]]
                    student_element.set("fio", values[0])
                    student_element.set("class", values[1])
            else:
                grades_element = ET.SubElement(root, "grades")

                for item in self.grades_tree.get_children():
                    grade_element = ET.SubElement(grades_element, "grade")
                    values = [self.grades_tree.set(item, col) for col in self.grades_tree["columns"]]
                    grade_element.set("fio", values[0])
                    grade_element.set("subject", values[1])
                    grade_element.set("value", values[2])

            tree = ET.ElementTree(root)
            tree.write(filename, encoding='utf-8', xml_declaration=True)

            return True
        except Exception as e:
            raise XMLProcessingError(f"Ошибка при сохранении XML файла: {str(e)}")

    def load_from_file(self, filename):
        """Загружает данные из XML/CSV в таблицу."""
        try:
            file_format = self.detect_file_format(filename)

            if file_format == 'xml':
                self.load_from_xml(filename)
            else:
                self.load_from_csv(filename)

            return True
        except Exception as e:
            raise FileOperationError(f"Ошибка при загрузке файла: {str(e)}")

    def load_from_csv(self, filename):
        """Загружает CSV в текущую таблицу."""
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                header = next(reader, None)
                rows = [row for row in reader]

                self._apply_loaded_rows(rows)
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
                    (teacher_element.get("fio", ""), teacher_element.get("subject", ""), teacher_element.get("classes", ""))
                    for teacher_element in teachers_element.findall("teacher")
                ] if teachers_element is not None else []
                self._apply_loaded_rows(rows)
            elif self.current_table == "students":
                students_element = root.find("students")
                rows = [
                    (student_element.get("fio", ""), student_element.get("class", ""))
                    for student_element in students_element.findall("student")
                ] if students_element is not None else []
                self._apply_loaded_rows(rows)
            else:
                grades_element = root.find("grades")
                rows = [
                    (grade_element.get("fio", ""), grade_element.get("subject", ""), grade_element.get("value", ""))
                    for grade_element in grades_element.findall("grade")
                ] if grades_element is not None else []
                self._apply_loaded_rows(rows)

            return True
        except Exception as e:
            raise XMLProcessingError(f"Ошибка при загрузке XML файла: {str(e)}")

    def _apply_loaded_rows(self, rows):
        """Применяет загруженные строки к текущей таблице"""
        normalized = []

        if self.current_table == "teachers":
            for row in rows:
                if len(row) >= 3:
                    normalized.append((row[0], row[1], row[2]))
            self._set_table_data_from_rows("teachers", normalized)

        elif self.current_table == "students":
            for row in rows:
                if len(row) >= 2:
                    normalized.append((row[0], row[1]))
            self._set_table_data_from_rows("students", normalized)

        else:
            for row in rows:
                if len(row) >= 3:
                    normalized.append((row[0], row[1], row[2]))
            self._set_table_data_from_rows("grades", normalized)

    def _set_table_data_from_rows(self, table, rows):
        """Обновляет представление таблицы данными из списка кортежей"""
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
            self._populate_tree(self.teachers_tree, self.teachers_data)
        elif table == "students":
            self.students_data = data_entries
            self.original_students_data = [row.copy() for row in data_entries]
            self.data_source["students"] = "file"
            self.loaded_import_data["students"] = rows
            self._populate_tree(self.students_tree, self.students_data)
        else:
            self.grades_data = data_entries
            self.original_grades_data = [row.copy() for row in data_entries]
            self.data_source["grades"] = "file"
            self.loaded_import_data["grades"] = rows
            self._populate_tree(self.grades_tree, self.grades_data)

    def on_import_to_db_click(self, _):
        """Импортирует загруженные данные в БД"""
        try:
            imported = self._import_loaded_data_to_db()
            messagebox.showinfo("Импорт в БД", f"Импортировано записей: {imported}")
        except NoImportFileError as e:
            messagebox.showwarning("Импорт в БД", str(e))
        except Exception as e:
            messagebox.showerror("Импорт в БД", f"Ошибка импорта: {str(e)}")

    def _import_loaded_data_to_db(self):
        table = self.current_table
        if not self.current_file:
            raise NoImportFileError("Сначала выберите файл для загрузки.")
        rows = self.loaded_import_data.get(table) or []
        if not rows:
            raise NoImportFileError("Сначала загрузите файл для текущей таблицы.")

        if table == "teachers":
            imported = self.data_manager.import_teachers(rows)
        elif table == "students":
            imported = self.data_manager.import_students(rows)
        else:
            imported = self.data_manager.import_grades(rows)

        self.refresh_data(table)
        self.data_source[table] = "database"
        return imported

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

        except NoFileChoosen as e:
            messagebox.showerror("Ошибка сохранения", str(e))
        except FileOperationError as e:
            messagebox.showerror("Ошибка операции с файлом", str(e))
        except XMLProcessingError as e:
            messagebox.showerror("Ошибка обработки XML", str(e))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка при сохранении файла: {str(e)}")

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
            messagebox.showerror("Ошибка выбора файла", str(e))
        except FileOperationError as e:
            messagebox.showerror("Ошибка операции с файлом", str(e))
        except XMLProcessingError as e:
            messagebox.showerror("Ошибка обработки XML", str(e))
        except Exception as e:
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

                tk.Label(form_frame, text="Предмет:").grid(row=1, column=0, sticky="w", pady=5)
                subject_entry = tk.Entry(form_frame, width=30)
                subject_entry.grid(row=1, column=1, pady=5, padx=(10, 0))
                subject_entry.insert(0, current_values[1])
                entry_widgets['subject'] = subject_entry

                tk.Label(form_frame, text="Классы:").grid(row=2, column=0, sticky="w", pady=5)
                classes_entry = tk.Entry(form_frame, width=30)
                classes_entry.grid(row=2, column=1, pady=5, padx=(10, 0))
                classes_entry.insert(0, current_values[2])
                entry_widgets['classes'] = classes_entry

            elif self.current_table == "students":
                tk.Label(form_frame, text="ФИО:").grid(row=0, column=0, sticky="w", pady=5)
                fio_entry = tk.Entry(form_frame, width=30)
                fio_entry.grid(row=0, column=1, pady=5, padx=(10, 0))
                fio_entry.insert(0, current_values[0])
                entry_widgets['fio'] = fio_entry

                tk.Label(form_frame, text="Класс:").grid(row=1, column=0, sticky="w", pady=5)
                class_entry = tk.Entry(form_frame, width=30)
                class_entry.grid(row=1, column=1, pady=5, padx=(10, 0))
                class_entry.insert(0, current_values[1])
                entry_widgets['class'] = class_entry
            else:
                tk.Label(form_frame, text="ФИО:").grid(row=0, column=0, sticky="w", pady=5)
                fio_entry = tk.Entry(form_frame, width=30)
                fio_entry.grid(row=0, column=1, pady=5, padx=(10, 0))
                fio_entry.insert(0, current_values[0])
                entry_widgets['fio'] = fio_entry

                tk.Label(form_frame, text="Предмет:").grid(row=1, column=0, sticky="w", pady=5)
                subject_entry = tk.Entry(form_frame, width=30)
                subject_entry.grid(row=1, column=1, pady=5, padx=(10, 0))
                subject_entry.insert(0, current_values[1])
                entry_widgets['subject'] = subject_entry

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

    # ДОБАВЛЯЕМ В КЛАСС SchoolApp:

    def refresh_data(self, table_type=None):
        """Обновляет данные из базы для указанной таблицы."""
        table = table_type or self.current_table

        if table == "teachers":
            self.teachers_data = self.data_manager.get_all_teachers()
            self.original_teachers_data = [row.copy() for row in self.teachers_data]
            self.data_source["teachers"] = "database"
            self._populate_tree(self.teachers_tree, self.teachers_data)
        elif table == "students":
            self.students_data = self.data_manager.get_all_students()
            self.original_students_data = [row.copy() for row in self.students_data]
            self.data_source["students"] = "database"
            self._populate_tree(self.students_tree, self.students_data)
        else:
            self.grades_data = self.data_manager.get_all_grades()
            self.original_grades_data = [row.copy() for row in self.grades_data]
            self.data_source["grades"] = "database"
            self._populate_tree(self.grades_tree, self.grades_data)

    def save_edited_row(self, edit_window, selected_item, entry_widgets, tree):
        """Сохранение отредактированных данных В БД"""
        try:
            if self.current_table == "teachers":
                new_fio = entry_widgets['fio'].get().strip()
                new_subject = entry_widgets['subject'].get().strip()
                new_classes = entry_widgets['classes'].get().strip()

                if not new_fio:
                    raise EmptySearchError("Поле 'ФИО' не может быть пустым")

                if self.data_source["teachers"] == "database":
                    teacher_id = int(selected_item)
                    success = self.data_manager.update_teacher_gui(teacher_id, new_fio, new_subject, new_classes)
                    if not success:
                        raise FileOperationError("Не удалось обновить запись учителя")
                    self.refresh_data("teachers")
                else:
                    new_values = (new_fio, new_subject, new_classes)
                    tree.item(selected_item, values=new_values)
                    self._sync_table_from_tree("teachers")

            elif self.current_table == "students":
                new_fio = entry_widgets['fio'].get().strip()
                new_class = entry_widgets['class'].get().strip()

                if not new_fio:
                    raise EmptySearchError("Поле 'ФИО' не может быть пустым")

                if self.data_source["students"] == "database":
                    student_id = int(selected_item)
                    success = self.data_manager.update_student_gui(student_id, new_fio, new_class)
                    if not success:
                        raise FileOperationError("Не удалось обновить запись ученика")
                    self.refresh_data("students")
                else:
                    new_values = (new_fio, new_class)
                    tree.item(selected_item, values=new_values)
                    self._sync_table_from_tree("students")

            else:
                new_fio = entry_widgets['fio'].get().strip()
                new_subject = entry_widgets['subject'].get().strip()
                new_grade = entry_widgets['grade'].get().strip()

                if not new_fio or not new_subject or not new_grade:
                    raise EmptySearchError("Все поля должны быть заполнены")

                if self.data_source["grades"] == "database":
                    grade_id = int(selected_item)
                    success = self.data_manager.update_grade_gui(grade_id, new_fio, new_subject, new_grade)
                    if not success:
                        raise FileOperationError("Не удалось обновить запись об оценке")
                    self.refresh_data("grades")
                else:
                    new_values = (new_fio, new_subject, new_grade)
                    tree.item(selected_item, values=new_values)
                    self._sync_table_from_tree("grades")

            edit_window.destroy()
            messagebox.showinfo("Успех", "Данные успешно обновлены")

        except EmptySearchError as e:
            messagebox.showwarning("Ошибка заполнения", str(e))
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
                self._handle_delete(selected_item)
            elif self.current_table == "students":
                selected_item = self.students_tree.selection()
                if not selected_item:
                    messagebox.showwarning("Удаление", "Выберите запись для удаления")
                    return
                self._handle_delete(selected_item)
            else:
                selected_item = self.grades_tree.selection()
                if not selected_item:
                    messagebox.showwarning("Удаление", "Выберите запись для удаления")
                    return
                self._handle_delete(selected_item)

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
        self.info_window.protocol("WM_DELETE_WINDOW", self._close_info_center)

        notebook = ttk.Notebook(self.info_window)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self._build_subject_tab(notebook)
        self._build_teacher_tab(notebook)
        self._build_students_tab(notebook)
        self._build_performance_tab(notebook)

        refresh_btn = ttk.Button(self.info_window, text="Обновить данные", command=self._refresh_info_center_data)
        refresh_btn.pack(pady=(0, 10))

        self._refresh_info_center_data()

    def _close_info_center(self):
        if self.info_window and tk.Toplevel.winfo_exists(self.info_window):
            self.info_window.destroy()
        self.info_window = None

    def _build_subject_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=10)
        notebook.add(frame, text="Предметы")

        ttk.Label(frame, text="Предмет:").grid(row=0, column=0, sticky="w")
        self.subject_query_var = tk.StringVar()
        self.subject_combo = ttk.Combobox(frame, textvariable=self.subject_query_var, width=35)
        self.subject_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        subject_btn = ttk.Button(frame, text="Показать", command=self._handle_subject_lookup)
        subject_btn.grid(row=0, column=2, padx=5, pady=5)

        self.subject_result_box = tk.Listbox(frame, height=8)
        self.subject_result_box.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=(10, 0))

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)

    def _build_teacher_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=10)
        notebook.add(frame, text="Учителя")

        ttk.Label(frame, text="Учитель:").grid(row=0, column=0, sticky="w")
        self.teacher_query_var = tk.StringVar()
        self.teacher_combo = ttk.Combobox(frame, textvariable=self.teacher_query_var, width=35)
        self.teacher_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        teacher_btn = ttk.Button(frame, text="Показать классы", command=self._handle_teacher_classes_lookup)
        teacher_btn.grid(row=0, column=2, padx=5, pady=5)

        self.teacher_classes_var = tk.StringVar(value="Классы: —")
        ttk.Label(frame, textvariable=self.teacher_classes_var, wraplength=400, justify="left").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(10, 0))

        frame.columnconfigure(1, weight=1)

    def _build_students_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=10)
        notebook.add(frame, text="Ученики")

        self.total_students_var = tk.StringVar(value="Всего учеников: —")
        ttk.Label(frame, textvariable=self.total_students_var, font=('Arial', 10, 'bold')).grid(
            row=0, column=0, columnspan=3, sticky="w")

        ttk.Label(frame, text="Класс:").grid(row=1, column=0, sticky="w", pady=(15, 0))
        self.class_query_var = tk.StringVar()
        self.student_class_combo = ttk.Combobox(frame, textvariable=self.class_query_var, width=15)
        self.student_class_combo.grid(row=1, column=1, padx=5, pady=(15, 0), sticky="w")

        class_btn = ttk.Button(frame, text="Посчитать", command=self._handle_class_count_lookup)
        class_btn.grid(row=1, column=2, padx=5, pady=(15, 0))

        self.class_count_var = tk.StringVar(value="Ученики в выбранном классе: —")
        ttk.Label(frame, textvariable=self.class_count_var).grid(row=2, column=0, columnspan=3, sticky="w", pady=(10, 0))

    def _build_performance_tab(self, notebook):
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

    def _handle_subject_lookup(self):
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

    def _handle_teacher_classes_lookup(self):
        teacher = self.teacher_query_var.get().strip() if hasattr(self, 'teacher_query_var') else ""
        if not teacher:
            messagebox.showwarning("Поиск учителя", "Введите или выберите учителя.")
            return

        classes = self.data_manager.get_teacher_classes(teacher)
        if classes:
            self.teacher_classes_var.set(f"Классы: {', '.join(classes)}")
        else:
            self.teacher_classes_var.set("Классы: нет данных")

    def _handle_class_count_lookup(self):
        class_name = self.class_query_var.get().strip() if hasattr(self, 'class_query_var') else ""
        if not class_name:
            messagebox.showwarning("Поиск класса", "Введите или выберите класс.")
            return

        count = self.data_manager.get_student_count(class_name)
        self.class_count_var.set(f"Ученики в классе {class_name}: {count}")

    def _refresh_info_center_data(self):
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
            self._populate_student_listbox(self.good_students_list, report.get('good_students', []))
        if hasattr(self, 'bad_students_list'):
            self._populate_student_listbox(self.bad_students_list, report.get('bad_students', []))

    def _populate_student_listbox(self, listbox, students):
        listbox.delete(0, tk.END)
        if not students:
            listbox.insert(tk.END, "Нет данных")
            return
        for student in students:
            listbox.insert(tk.END, self._format_student_record(student))

    def _format_student_record(self, student_row):
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

    def _get_tree_and_data(self):
        """Возвращает дерево и набор исходных данных для текущей таблицы"""
        if self.current_table == "teachers":
            return self.teachers_tree, self.original_teachers_data
        elif self.current_table == "students":
            return self.students_tree, self.original_students_data
        else:
            return self.grades_tree, self.original_grades_data

    def _populate_tree(self, tree, data_rows):
        """Заполняет дерево указанными строками"""
        for item in tree.get_children():
            tree.delete(item)

        for row in data_rows:
            row_id = row.get("id")
            if row_id is not None:
                tree.insert("", "end", iid=str(row_id), values=row["values"])
            else:
                tree.insert("", "end", values=row["values"])

    def _sync_table_from_tree(self, table):
        """Обновляет кэшированные данные таблицы из Treeview"""
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

    def _handle_delete(self, selected_items):
        """Удаляет записи в текущей таблице с учетом источника данных"""
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
                self._sync_table_from_tree("teachers")

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
                self._sync_table_from_tree("students")

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
                self._sync_table_from_tree("grades")

    def perform_search(self, search_term):
        """Выполняет поиск по таблице"""
        tree, data = self._get_tree_and_data()
        filtered = []
        search_term_lower = search_term.lower()

        for row in data:
            if any(search_term_lower in str(field).lower() for field in row["values"]):
                filtered.append(row)

        self._populate_tree(tree, filtered)

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
            if sort_by == "ФИО":
                column_index = 0
            elif sort_by == "Предмет":
                column_index = 1
            else:
                column_index = 2
        elif self.current_table == "students":
            tree = self.students_tree
            if sort_by == "ФИО":
                column_index = 0
            else:
                column_index = 1
        else:
            tree = self.grades_tree
            if sort_by == "ФИО":
                column_index = 0
            elif sort_by == "Предмет":
                column_index = 1
            else:
                column_index = 2

        self.sort_treeview(tree, column_index)

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
        value_str = str(value).lower()

        if self.current_table == "students" and column_index == 1:
            return self.parse_single_class(value)

        elif self.current_table == "teachers" and column_index == 2:
            return self.parse_teacher_classes(value)

        elif self.current_table == "grades" and column_index == 2:
            try:
                return (int(value),)
            except (TypeError, ValueError):
                return (value_str,)

        else:
            return (value_str,)

    def sort_treeview(self, tree, column):
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
            items.sort(key=lambda x: x[0])
        except TypeError:
            items.sort(key=lambda x: str(x[0]))

        for index, (_, item) in enumerate(items):
            tree.move(item, '', index)

    def reset_filters(self):
        """Сбрасывает все фильтры и сортировку к исходному состоянию"""
        self.search_var.set("")
        tree, data = self._get_tree_and_data()
        self._populate_tree(tree, data)

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
    root = tk.Tk()
    app = SchoolApp(root)
    root.geometry("950x650")
    root.mainloop()
    root.mainloop()