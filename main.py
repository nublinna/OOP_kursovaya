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


# ДОБАВЛЯЕМ В НАЧАЛО ОСНОВНОГО ФАЙЛА, ПОСЛЕ ИМПОРТОВ

class SchoolDataManager:
    """Класс для интеграции БД с GUI - соответствует требованиям ООП"""

    def __init__(self):
        self.db = SchoolDatabase()
        self._setup_initial_data()

    def _setup_initial_data(self):
        """Инициализация начальных данных при первом запуске"""
        try:
            # Проверяем, есть ли данные в БД, если нет - заполняем демо-данными
            if self._is_database_empty():
                self._initialize_demo_data()
        except Exception as e:
            print(f"Ошибка инициализации БД: {e}")

    def _is_database_empty(self):
        """Проверяет, пустая ли БД"""
        try:
            self.db.DB_CURSOR.execute("SELECT COUNT(*) FROM students")
            student_count = self.db.DB_CURSOR.fetchone()[0]

            self.db.DB_CURSOR.execute("SELECT COUNT(*) FROM teachers")
            teacher_count = self.db.DB_CURSOR.fetchone()[0]

            return student_count == 0 and teacher_count == 0
        except:
            return True

    def _initialize_demo_data(self):
        """Заполнение демо-данными согласно требованиям методички"""
        # Демо-учителя
        demo_teachers = [
            ("Иванова", "Анна", "Петровна", "Математика", ["5А", "6Б", "9В"]),
            ("Петров", "Сергей", "Владимирович", "Физика", ["7А", "8Б", "10А"]),
            ("Сидорова", "Ольга", "Михайловна", "Литература", ["5А", "6А", "7А", "8А"]),
        ]

        for teacher in demo_teachers:
            self.db.add_teacher(*teacher)

        # Демо-ученики
        demo_students = [
            ("Алексеев", "Александр", "5А", "Сергеевич"),
            ("Борисова", "Екатерина", "6Б", "Игоревна"),
            ("Васильев", "Максим", "7А", "Дмитриевич"),
            ("Григорьева", "София", "8Б", "Андреевна"),
        ]

        for student in demo_students:
            self.db.add_student(*student)

    def get_all_teachers(self):
        """Получение всех учителей в формате для GUI"""
        try:
            self.db.DB_CURSOR.execute("SELECT last_name, first_name, middle_name, subject, classes FROM teachers")
            teachers = self.db.DB_CURSOR.fetchall()

            # Преобразуем в формат для Treeview: (ФИО, Предмет, Классы)
            result = []
            for teacher in teachers:
                last_name, first_name, middle_name, subject, classes = teacher
                fio = f"{last_name} {first_name} {middle_name}".strip()
                classes_str = ", ".join(classes) if classes else ""
                result.append((fio, subject, classes_str))

            return result
        except Exception as e:
            print(f"Ошибка получения учителей: {e}")
            return []

    def get_all_students(self):
        """Получение всех учеников в формате для GUI"""
        try:
            self.db.DB_CURSOR.execute("SELECT last_name, first_name, middle_name, class_name FROM students")
            students = self.db.DB_CURSOR.fetchall()

            # Преобразуем в формат для Treeview: (ФИО, Класс)
            result = []
            for student in students:
                last_name, first_name, middle_name, class_name = student
                fio = f"{last_name} {first_name} {middle_name}".strip()
                # class_name это массив, берем первый элемент
                class_str = class_name[0] if class_name and len(class_name) > 0 else ""
                result.append((fio, class_str))

            return result
        except Exception as e:
            print(f"Ошибка получения учеников: {e}")
            return []

    def add_teacher_gui(self, fio, subject, classes_str):
        """Добавление учителя из GUI"""
        try:
            # Парсим ФИО
            parts = fio.split()
            if len(parts) >= 2:
                last_name = parts[0]
                first_name = parts[1]
                middle_name = parts[2] if len(parts) > 2 else ""
            else:
                last_name = fio
                first_name = ""
                middle_name = ""

            # Парсим классы
            classes = [cls.strip() for cls in classes_str.split(",") if cls.strip()]

            self.db.add_teacher(last_name, first_name, subject, classes, middle_name)
            return True
        except Exception as e:
            print(f"Ошибка добавления учителя: {e}")
            return False

    def add_student_gui(self, fio, class_name):
        """Добавление ученика из GUI"""
        try:
            # Парсим ФИО
            parts = fio.split()
            if len(parts) >= 2:
                last_name = parts[0]
                first_name = parts[1]
                middle_name = parts[2] if len(parts) > 2 else ""
            else:
                last_name = fio
                first_name = ""
                middle_name = ""

            self.db.add_student(last_name, first_name, [class_name], middle_name)
            return True
        except Exception as e:
            print(f"Ошибка добавления ученика: {e}")
            return False

    def update_teacher_gui(self, old_fio, new_fio, new_subject, new_classes_str):
        """Обновление учителя из GUI"""
        try:
            # Для простоты удаляем и добавляем заново
            # В реальном приложении нужно использовать ID
            self.delete_teacher_gui(old_fio)
            return self.add_teacher_gui(new_fio, new_subject, new_classes_str)
        except Exception as e:
            print(f"Ошибка обновления учителя: {e}")
            return False

    def delete_teacher_gui(self, fio):
        """Удаление учителя из GUI"""
        try:
            parts = fio.split()
            if len(parts) >= 2:
                last_name = parts[0]
                first_name = parts[1]

                self.db.DB_CURSOR.execute(
                    "DELETE FROM teachers WHERE last_name = %s AND first_name = %s",
                    (last_name, first_name)
                )
                self.db.DB_CONNECTION.commit()
                return True
            return False
        except Exception as e:
            print(f"Ошибка удаления учителя: {e}")
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
            else:
                headers = ["ФИО", "Класс"]

            font_path = os.path.abspath("fonts").replace("\\", "/")
            print(f"{font_path}")

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

            DEFAULT_FONT["helvetica"] = "DejavuSans"
            DEFAULT_FONT["Helvetica"] = "DejavuSans"
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
    Класс SchoolApp используется для создания основных компонентов программы
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Школьная база данных")
        self.root.configure(bg='#f0f0f0')

        self.current_file = None
        self.current_table = "teachers"

        self.data_manager = SchoolDataManager()

        self.setup_styles()
        self.setup_report_generator()

        self.top_frame = self.create_top_panel()
        self.control_frame = self.create_control_panel()

        self.table_frame = tk.Frame(root, bg='#f0f0f0')
        self.table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.create_teachers_table()
        self.create_students_table()

        self.show_table("teachers")

    def create_teachers_table(self):
        """Создание таблицы учителей с данными из БД"""
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
            self.teachers_tree.insert("", "end", values=teacher)

        scrollbar = ttk.Scrollbar(self.teachers_frame, orient="vertical", command=self.teachers_tree.yview)
        self.teachers_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.teachers_tree.pack(side="left", fill="both", expand=True)

        self.original_teachers_data = self.teachers_data.copy()
        self.teachers_sort_options = ["ФИО", "Предмет", "Классы"]

    def create_students_table(self):
        """Создание таблицы учеников с данными из БД"""
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
            self.students_tree.insert("", "end", values=student)

        scrollbar = ttk.Scrollbar(self.students_frame, orient="vertical", command=self.students_tree.yview)
        self.students_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.students_tree.pack(side="left", fill="both", expand=True)

        self.original_students_data = self.students_data.copy()
        self.students_sort_options = ["ФИО", "Класс"]

    def setup_styles(self):
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
        """
        Создание верхней панели с кнопками
        """
        top_frame = tk.Frame(self.root, bg='#d0d0d0', height=80)
        top_frame.pack(fill="x", padx=5, pady=5)
        top_frame.pack_propagate(False)

        main_logo = tk.Label(top_frame, text="[ЛОГОТИП\nШКОЛЫ]",
                             bg='#b0b0b0', fg='#555555',
                             width=12, height=4,
                             relief='sunken', font=('Arial', 9, 'bold'))
        main_logo.pack(side="left", padx=5, pady=5)

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
            "Редактировать",
            "Удалить"
        ]

        self.tool_buttons = {}

        icon_files = {
            "Сохранить": "save_button.png",
            "Открыть файл": "open_file.png",
            "Создать файл": "new_file.png",
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
        """Определяет формат файла по расширению"""
        _, ext = os.path.splitext(filename)
        ext = ext.lower()

        if ext == '.xml':
            return 'xml'
        elif ext == '.csv' or ext == '.txt':
            return 'csv'
        else:
            return None

    def save_to_file(self, filename):
        """Сохранение данных текущей таблицы в файл"""
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
        """Сохранение данных текущей таблицы в файл CSV"""
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)

                if self.current_table == "teachers":
                    tree = self.teachers_tree
                    headers = [self.teachers_tree.heading(col)["text"] for col in self.teachers_tree["columns"]]
                    writer.writerow(headers)
                    for item in tree.get_children():
                        row = [tree.set(item, col) for col in tree["columns"]]
                        writer.writerow(row)
                else:
                    tree = self.students_tree
                    headers = [self.students_tree.heading(col)["text"] for col in self.students_tree["columns"]]
                    writer.writerow(headers)
                    for item in tree.get_children():
                        row = [tree.set(item, col) for col in tree["columns"]]
                        writer.writerow(row)

            return True
        except Exception as e:
            raise FileOperationError(f"Ошибка при сохранении CSV файла: {str(e)}")

    def save_to_xml(self, filename):
        """Сохранение данных текущей таблицы в файл XML"""
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
            else:
                students_element = ET.SubElement(root, "students")

                for item in self.students_tree.get_children():
                    student_element = ET.SubElement(students_element, "student")
                    values = [self.students_tree.set(item, col) for col in self.students_tree["columns"]]
                    student_element.set("fio", values[0])
                    student_element.set("class", values[1])

            tree = ET.ElementTree(root)
            tree.write(filename, encoding='utf-8', xml_declaration=True)

            return True
        except Exception as e:
            raise XMLProcessingError(f"Ошибка при сохранении XML файла: {str(e)}")

    def load_from_file(self, filename):
        """Загрузка данных из файла в текущую таблицу"""
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
        """Загрузка данных из файла CSV в текущую таблицу"""
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)

                if self.current_table == "teachers":
                    tree = self.teachers_tree
                    for item in tree.get_children():
                        tree.delete(item)
                    next(reader, None)
                    for row in reader:
                        if len(row) == 3:
                            tree.insert("", "end", values=row)
                    self.original_teachers_data = []
                    for item in tree.get_children():
                        self.original_teachers_data.append([tree.set(item, col) for col in tree["columns"]])
                else:
                    tree = self.students_tree
                    for item in tree.get_children():
                        tree.delete(item)
                    next(reader, None)
                    for row in reader:
                        if len(row) == 2:
                            tree.insert("", "end", values=row)
                    self.original_students_data = []
                    for item in tree.get_children():
                        self.original_students_data.append([tree.set(item, col) for col in tree["columns"]])
            return True
        except Exception as e:
            raise FileOperationError(f"Ошибка при загрузке CSV файла: {str(e)}")

    def load_from_xml(self, filename):
        """Загрузка данных из файла XML в текущую таблицу"""
        try:
            tree_xml = ET.parse(filename)
            root = tree_xml.getroot()

            if self.current_table == "teachers":
                tree = self.teachers_tree
                for item in tree.get_children():
                    tree.delete(item)

                teachers_element = root.find("teachers")
                if teachers_element is not None:
                    for teacher_element in teachers_element.findall("teacher"):
                        fio = teacher_element.get("fio", "")
                        subject = teacher_element.get("subject", "")
                        classes = teacher_element.get("classes", "")
                        tree.insert("", "end", values=(fio, subject, classes))

                self.original_teachers_data = []
                for item in tree.get_children():
                    self.original_teachers_data.append([tree.set(item, col) for col in tree["columns"]])
            else:
                tree = self.students_tree
                for item in tree.get_children():
                    tree.delete(item)

                students_element = root.find("students")
                if students_element is not None:
                    for student_element in students_element.findall("student"):
                        fio = student_element.get("fio", "")
                        student_class = student_element.get("class", "")
                        tree.insert("", "end", values=(fio, student_class))

                self.original_students_data = []
                for item in tree.get_children():
                    self.original_students_data.append([tree.set(item, col) for col in tree["columns"]])

            return True
        except Exception as e:
            raise XMLProcessingError(f"Ошибка при загрузке XML файла: {str(e)}")

    def validate_search_input(self, search_term):
        """Проверяет введенный текст для поиска"""
        if not search_term or not search_term.strip():
            raise EmptySearchError("Поле поиска не может быть пустым")
        return True

    def on_save_click(self, _):
        """Обработчик событий для кнопки "Сохранить"""
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
        """Обработчик событий для кнопки "Открыть файл"""
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
        """Обработчик событий для кнопки "Создать файл"""
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
                self.original_teachers_data = []
            else:
                tree = self.students_tree
                for item in tree.get_children():
                    tree.delete(item)
                self.original_students_data = []

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
        """Редактирование выбранной строки в таблице"""
        try:
            if self.current_table == "teachers":
                tree = self.teachers_tree
                original_data = self.original_teachers_data
            else:
                tree = self.students_tree
                original_data = self.original_students_data

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

            else:
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

            button_frame = tk.Frame(edit_window, pady=10)
            button_frame.pack(fill="x")

            save_button = tk.Button(button_frame, text="Сохранить",
                                    command=lambda: self.save_edited_row(edit_window, selected_item, entry_widgets,
                                                                         tree, original_data))
            save_button.pack(side="left", padx=10)

            cancel_button = tk.Button(button_frame, text="Отмена",
                                      command=edit_window.destroy)
            cancel_button.pack(side="left", padx=10)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка при редактировании: {str(e)}")

    # ДОБАВЛЯЕМ В КЛАСС SchoolApp:

    def refresh_data(self):
        """Обновление данных из БД"""
        if self.current_table == "teachers":
            self.teachers_data = self.data_manager.get_all_teachers()
            for item in self.teachers_tree.get_children():
                self.teachers_tree.delete(item)
            for teacher in self.teachers_data:
                self.teachers_tree.insert("", "end", values=teacher)
            self.original_teachers_data = self.teachers_data.copy()
        else:
            self.students_data = self.data_manager.get_all_students()
            for item in self.students_tree.get_children():
                self.students_tree.delete(item)
            for student in self.students_data:
                self.students_tree.insert("", "end", values=student)
            self.original_students_data = self.students_data.copy()

    def save_edited_row(self, edit_window, selected_item, entry_widgets, tree, original_data):
        """Сохранение отредактированных данных В БД"""
        try:
            if self.current_table == "teachers":
                new_fio = entry_widgets['fio'].get().strip()
                new_subject = entry_widgets['subject'].get().strip()
                new_classes = entry_widgets['classes'].get().strip()

                if not new_fio:
                    raise EmptySearchError("Поле 'ФИО' не может быть пустым")

                # Получаем старые данные для удаления
                old_values = tree.item(selected_item, 'values')
                old_fio = old_values[0]

                # Обновляем в БД
                success = self.data_manager.update_teacher_gui(old_fio, new_fio, new_subject, new_classes)
                if success:
                    new_values = (new_fio, new_subject, new_classes)
                    tree.item(selected_item, values=new_values)
                    self.refresh_data()  # Обновляем данные из БД

            else:
                new_fio = entry_widgets['fio'].get().strip()
                new_class = entry_widgets['class'].get().strip()

                if not new_fio:
                    raise EmptySearchError("Поле 'ФИО' не может быть пустым")

                # Для студентов просто обновляем в дереве
                new_values = (new_fio, new_class)
                tree.item(selected_item, values=new_values)

            edit_window.destroy()
            messagebox.showinfo("Успех", "Данные успешно обновлены")

        except EmptySearchError as e:
            messagebox.showwarning("Ошибка заполнения", str(e))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при сохранении: {str(e)}")

    def on_edit_click(self, _):
        """Обработчик событий для кнопки "Редактировать"""
        try:
            if not self.current_file:
                raise NoFileOpen("Файл не открыт. Нечего редактировать.")

            if self.current_table == "teachers":
                selected_item = self.teachers_tree.selection()
                if not selected_item:
                    raise NoDataForEdit("Выберите запись для редактирования")
            else:
                selected_item = self.students_tree.selection()
                if not selected_item:
                    raise NoDataForEdit("Выберите запись для редактирования")

            self.edit_selected_row()

        except NoFileOpen as e:
            messagebox.showerror("Ошибка редактирования", str(e))
        except NoDataForEdit as e:
            messagebox.showwarning("Редактирование", str(e))
        except FileOperationError as e:
            messagebox.showerror("Ошибка операции с файлом", str(e))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка при редактировании файла: {str(e)}")

    def on_delete_click(self, _):
        """Обработчик событий для кнопки "Удалить"""
        try:
            if not self.current_file:
                raise NoFileOpen("Файл не открыт. Нечего удалять.")

            if self.current_table == "teachers":
                selected_item = self.teachers_tree.selection()
                if not selected_item:
                    messagebox.showwarning("Удаление", "Выберите запись для удаления")
                    return
                for item in selected_item:
                    self.teachers_tree.delete(item)
                self.original_teachers_data = []
                for item in self.teachers_tree.get_children():
                    self.original_teachers_data.append(
                        [self.teachers_tree.set(item, col) for col in self.teachers_tree["columns"]])
            else:
                selected_item = self.students_tree.selection()
                if not selected_item:
                    messagebox.showwarning("Удаление", "Выберите запись для удаления")
                    return
                for item in selected_item:
                    self.students_tree.delete(item)
                self.original_students_data = []
                for item in self.students_tree.get_children():
                    self.original_students_data.append(
                        [self.students_tree.set(item, col) for col in self.students_tree["columns"]])

            messagebox.showinfo("Удаление", "Запись успешно удалена")

        except NoFileOpen as e:
            messagebox.showerror("Ошибка удаления", str(e))
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

        tk.Label(control_frame, text="Просмотр:", bg='#f0f0f0', font=('Arial', 9)).pack(side="left", padx=(0, 5))

        self.table_var = tk.StringVar(value="Учителя")
        self.table_combo = ttk.Combobox(control_frame,
                                        textvariable=self.table_var,
                                        values=["Учителя", "Ученики"],
                                        state="readonly",
                                        width=12)
        self.table_combo.pack(side="left", padx=(0, 20))
        self.table_combo.bind('<<ComboboxSelected>>', self.on_table_change)

        tk.Label(control_frame, text="Поиск:", bg='#f0f0f0', font=('Arial', 9)).pack(side="left", padx=(0, 5))

        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(control_frame, textvariable=self.search_var, width=20)
        self.search_entry.pack(side="left", padx=(0, 5))
        self.search_entry.bind('<KeyRelease>', self.on_search)

        self.search_btn = ttk.Button(control_frame, text="Найти", command=self.on_search_button)
        self.search_btn.pack(side="left", padx=(5, 0))

        tk.Label(control_frame, text="Сортировка:", bg='#f0f0f0', font=('Arial', 9)).pack(side="left", padx=(20, 5))

        self.sort_var = tk.StringVar()
        self.sort_combo = ttk.Combobox(control_frame,
                                       textvariable=self.sort_var,
                                       state="readonly",
                                       width=15)
        self.sort_combo.pack(side="left", padx=(0, 5))
        self.sort_combo.bind('<<ComboboxSelected>>', self.on_sort_change)

        self.reset_btn = ttk.Button(control_frame, text="Сбросить", command=self.reset_filters)
        self.reset_btn.pack(side="left", padx=(10, 0))

        return control_frame

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

    def perform_search(self, search_term):
        """Выполняет поиск по таблице"""
        if self.current_table == "teachers":
            tree = self.teachers_tree
            data = self.original_teachers_data
        else:
            tree = self.students_tree
            data = self.original_students_data

        for item in tree.get_children():
            tree.delete(item)

        for item in data:
            if any(search_term.lower() in str(field).lower() for field in item):
                tree.insert("", "end", values=item)

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
        if table_type == "teachers":
            self.students_frame.pack_forget()
            self.teachers_frame.pack(fill="both", expand=True)
            self.current_table = "teachers"
            self.update_sort_options(self.teachers_sort_options)
        else:
            self.teachers_frame.pack_forget()
            self.students_frame.pack(fill="both", expand=True)
            self.current_table = "students"
            self.update_sort_options(self.students_sort_options)

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
        else:
            self.show_table("students")
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
        else:
            tree = self.students_tree
            if sort_by == "ФИО":
                column_index = 0
            else:
                column_index = 1

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

        items = []
        for item in tree.get_children(''):
            value = tree.set(item, column_index)
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

        if self.current_table == "teachers":
            tree = self.teachers_tree
            data = self.original_teachers_data
        else:
            tree = self.students_tree
            data = self.original_students_data

        for item in tree.get_children():
            tree.delete(item)

        for item in data:
            tree.insert("", "end", values=item)

        if self.current_table == "teachers" and self.teachers_sort_options:
            self.sort_var.set(self.teachers_sort_options[0])
            self.apply_sorting()
        elif self.current_table == "students" and self.students_sort_options:
            self.sort_var.set(self.students_sort_options[0])
            self.apply_sorting()

    def setup_report_generator(self):
        """Инициализация генератора отчетов"""
        self.report_generator = ReportGenerator()

    def generate_pdf_report(self):
        """Генерация PDF отчета"""
        try:
            if self.current_table == "teachers":
                data = self.original_teachers_data
                report_type = "Учителя"
            else:
                data = self.original_students_data
                report_type = "Ученики"

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
    root.geometry("700x600")
    root.mainloop()