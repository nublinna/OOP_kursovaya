"""Работа с PostgreSQL: создание таблиц и простые CRUD операции."""

import os
import psycopg2

class SchoolDatabase:
    """Простой класс-обёртка над PostgreSQL. Содержит все запросы приложения."""
    def __init__(self):
        db_config = {
            "dbname": os.getenv("SCHOOL_DB_NAME", "school_db"),
            "user": os.getenv("SCHOOL_DB_USER", "postgres"),
            "password": os.getenv("SCHOOL_DB_PASSWORD", "18072007"),
            "host": os.getenv("SCHOOL_DB_HOST", "localhost"),
            "port": int(os.getenv("SCHOOL_DB_PORT", 5432)),
        }
        self.DB_CONNECTION = psycopg2.connect(**db_config)
        self.DB_CURSOR = self.DB_CONNECTION.cursor()
        self.__create_tables()
        self.reset_all_sequences()

    def __del__(self):
        """Закрывает соединение и курсор при уничтожении объекта."""
        try:
            if hasattr(self, "DB_CURSOR") and self.DB_CURSOR:
                self.DB_CURSOR.close()
            if hasattr(self, "DB_CONNECTION") and self.DB_CONNECTION:
                self.DB_CONNECTION.close()
        except Exception:
            pass

    def _prepare_array(self, values):
        """Приводит список/строку классов к виду, понятному PostgreSQL."""
        if not values:
            return []

        if isinstance(values, str):
            cleaned = values.strip()
            if not cleaned:
                return []
            items = [item.strip() for item in cleaned.split(',') if item.strip()]
            return items if items else [cleaned]

        result = []
        for item in values:
            text = str(item).strip()
            if text:
                result.append(text)
        return result

    def __create_tables(self):
        """Создаёт таблицы, если их ещё нет."""
        students_table = """
                            CREATE TABLE IF NOT EXISTS students (
                                id SERIAL PRIMARY KEY,
                                last_name VARCHAR(50),
                                first_name VARCHAR(50),
                                middle_name VARCHAR(50),
                                birth_date DATE,
                                class_name TEXT[]
                            );
                        """
        teachers_table = """
                            CREATE TABLE IF NOT EXISTS teachers (
                                id SERIAL PRIMARY KEY,
                                last_name VARCHAR(50),
                                first_name VARCHAR(50),
                                middle_name VARCHAR(50),
                                birth_date DATE,
                                subject VARCHAR(50),
                                classes TEXT[]
                            );
                        """
        grades_table =  """
                            CREATE TABLE IF NOT EXISTS grades (
                                id SERIAL PRIMARY KEY,
                                student_id INTEGER REFERENCES students(id),
                                subject_name VARCHAR(50),
                                grade INTEGER CHECK (grade >=1 AND grade <= 5),
                                grade_date DATE DEFAULT CURRENT_DATE
                            );
                       """
        self.DB_CURSOR.execute(students_table)
        self.DB_CURSOR.execute(teachers_table)
        self.DB_CURSOR.execute(grades_table)
        self.DB_CURSOR.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS birth_date DATE")
        self.DB_CURSOR.execute("ALTER TABLE teachers ADD COLUMN IF NOT EXISTS birth_date DATE")
        self.DB_CONNECTION.commit()

    def add_student(self, last_name, first_name, class_name, middle_name="", birth_date=None):
        """Добавляет ученика и возвращает его id."""
        insert_student_query = """
                        INSERT INTO students (last_name, first_name,
                        middle_name, birth_date, class_name)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                        """
        class_array = self._prepare_array(class_name)
        self.DB_CURSOR.execute(
            insert_student_query,
            (last_name, first_name, middle_name, birth_date, class_array)
        )
        student_id = self.DB_CURSOR.fetchone()[0]
        self.DB_CONNECTION.commit()
        return student_id

    def update_students(self, student_id, last_name, first_name,
                        class_name, middle_name="", birth_date=None):
        """Обновляет данные ученика."""
        update_student_query = """
            UPDATE students SET last_name = %s, first_name = %s, class_name = %s,
            middle_name = %s, birth_date = %s
            WHERE id = %s
        """
        class_array = self._prepare_array(class_name)
        self.DB_CURSOR.execute(
            update_student_query,
            (last_name, first_name, class_array, middle_name, birth_date, student_id)
        )
        self.DB_CONNECTION.commit()

    def get_students_count(self, class_name=None):
        """Считает учеников в школе или в выбранном классе."""
        if class_name:
            query = "SELECT COUNT(*) FROM students WHERE %s = ANY(class_name)"
            self.DB_CURSOR.execute(query, (class_name,))
        else:
            self.DB_CURSOR.execute("SELECT COUNT(*) FROM students")
        return self.DB_CURSOR.fetchone()[0]

    def get_grades(self):
        """Возвращает данные для отчёта об успеваемости."""
        self.DB_CURSOR.execute("""
            SELECT last_name, first_name, middle_name, class_name
            FROM students WHERE id IN (
                SELECT student_id FROM grades
                GROUP BY student_id
                HAVING AVG(grade) >= 4.5
                
                )
            """)
        good_students = self.DB_CURSOR.fetchall()

        self.DB_CURSOR.execute("""
            SELECT last_name, first_name, middle_name, class_name
            FROM students WHERE id IN (
                SELECT student_id FROM grades
                GROUP BY student_id
                HAVING AVG(grade) < 3.5
                
                )
            """)
        bad_students = self.DB_CURSOR.fetchall()

        return {
            'good_students': good_students,
            'bad_students': bad_students,
            'total_students': self.get_students_count()
        }

    def add_grade(self, student_id, subject_name, grade):
        """Добавляет новую оценку и возвращает её id."""
        query = """
            INSERT INTO grades (student_id, subject_name, grade)
            VALUES (%s, %s, %s)
            RETURNING id
        """
        self.DB_CURSOR.execute(query, (student_id, subject_name, grade))
        grade_id = self.DB_CURSOR.fetchone()[0]
        self.DB_CONNECTION.commit()
        return grade_id

    def delete_student(self, student_id):
        """Удаляет ученика и все его оценки."""
        self.DB_CURSOR.execute("DELETE FROM grades WHERE student_id = %s", (student_id,))
        self.DB_CURSOR.execute("DELETE FROM students WHERE id = %s", (student_id,))
        self.DB_CONNECTION.commit()

    def add_teacher(self, last_name, first_name, subject, classes, middle_name="", birth_date=None):
        """Добавляет учителя и возвращает его id."""
        add_teacher_query = """
                                INSERT INTO teachers (last_name, first_name, 
                                middle_name, birth_date, subject, classes)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                RETURNING id
                                """
        classes_array = self._prepare_array(classes)

        self.DB_CURSOR.execute(
            add_teacher_query,
            (last_name, first_name, middle_name, birth_date, subject, classes_array)
        )
        teacher_id = self.DB_CURSOR.fetchone()[0]
        self.DB_CONNECTION.commit()
        return teacher_id

    def update_teachers(self, teacher_id, last_name, first_name,
                        subject, classes, middle_name="", birth_date=None):
        """Обновляет данные учителя."""
        update_teachers_query = """
                    UPDATE teachers SET last_name = %s, first_name = %s, subject = %s,
                    classes = %s, middle_name = %s, birth_date = %s
                    WHERE id = %s
                """
        classes_array = self._prepare_array(classes)
        self.DB_CURSOR.execute(
            update_teachers_query,
            (last_name, first_name, subject, classes_array, middle_name, birth_date, teacher_id)
        )
        self.DB_CONNECTION.commit()

    def get_teachers_by_subject(self, subject):
        """Находит учителей по предмету."""
        self.DB_CURSOR.execute("""SELECT last_name, first_name, middle_name
         FROM teachers WHERE subject = %s""", (subject,))
        return self.DB_CURSOR.fetchall()

    def get_teachers_by_classes(self, classes):
        """Находит учителей по набору классов."""
        self.DB_CURSOR.execute("""SELECT last_name, first_name, middle_name
        FROM teachers WHERE classes = %s""", (classes,))
        return self.DB_CURSOR.fetchall()

    def get_teacher_classes(self, teacher_id):
        """Возвращает список классов, закреплённых за учителем."""
        self.DB_CURSOR.execute("SELECT classes FROM teachers WHERE id = %s", (teacher_id,))
        return self.DB_CURSOR.fetchone()[0]

    def delete_teacher(self, teacher_id):
        """Удаляет учителя."""
        self.DB_CURSOR.execute("DELETE FROM teachers WHERE id = %s", (teacher_id,))
        self.DB_CONNECTION.commit()

    def get_all_grades_rows(self):
        """Возвращает все оценки вместе с ФИО учеников."""
        grade_rows_query = """
            SELECT g.id,
                   g.student_id,
                   s.last_name,
                   s.first_name,
                   s.middle_name,
                   g.subject_name,
                   g.grade
            FROM grades g
            JOIN students s ON s.id = g.student_id
            ORDER BY g.id
        """
        self.DB_CURSOR.execute(grade_rows_query)
        return self.DB_CURSOR.fetchall()

    def update_grade(self, grade_id, student_id, subject_name, grade):
        """Правит существующую оценку."""
        query = """
            UPDATE grades
            SET student_id = %s, subject_name = %s, grade = %s
            WHERE id = %s
        """
        self.DB_CURSOR.execute(query, (student_id, subject_name, grade, grade_id))
        self.DB_CONNECTION.commit()

    def delete_grade(self, grade_id):
        """Удаляет оценку."""
        self.DB_CURSOR.execute("DELETE FROM grades WHERE id = %s", (grade_id,))
        self.DB_CONNECTION.commit()

    def find_student_id(self, last_name, first_name, middle_name=""):
        """Ищет id ученика по ФИО."""
        query = """
            SELECT id FROM students
            WHERE last_name = %s AND first_name = %s AND COALESCE(middle_name, '') = %s
        """
        self.DB_CURSOR.execute(query, (last_name, first_name, middle_name))
        result = self.DB_CURSOR.fetchone()
        return result[0] if result else None

    def teacher_exists(self, last_name, first_name, middle_name, subject):
        """Проверяет, есть ли учитель с таким ФИО и предметом."""
        query = """
            SELECT id FROM teachers
            WHERE last_name = %s
              AND first_name = %s
              AND COALESCE(middle_name, '') = %s
              AND subject = %s
            LIMIT 1
        """
        self.DB_CURSOR.execute(query, (last_name, first_name, middle_name, subject))
        return self.DB_CURSOR.fetchone() is not None

    def clear_teachers(self):
        """Полностью очищает таблицу учителей."""
        self.DB_CURSOR.execute("DELETE FROM teachers")
        self.reset_sequence("teachers")
        self.DB_CONNECTION.commit()

    def clear_students(self):
        """Полностью очищает таблицу учеников."""
        self.DB_CURSOR.execute("DELETE FROM students")
        self.reset_sequence("students")
        self.DB_CONNECTION.commit()

    def clear_grades(self):
        """Полностью очищает таблицу оценок."""
        self.DB_CURSOR.execute("DELETE FROM grades")
        self.reset_sequence("grades")
        self.DB_CONNECTION.commit()

    def reset_sequence(self, table_name):
        """Сбрасывает последовательность id для указанной таблицы."""
        query = f"""
            SELECT setval(
                pg_get_serial_sequence('{table_name}', 'id'),
                COALESCE((SELECT MAX(id) FROM {table_name}), 0) + 1,
                false
            )
        """
        self.DB_CURSOR.execute(query)
        self.DB_CONNECTION.commit()

    def reset_all_sequences(self):
        """Сбрасывает последовательности для всех таблиц."""
        for table in ("students", "teachers", "grades"):
            self.reset_sequence(table)

    def fetch_all_teachers(self):
        """Возвращает все строки из таблицы teachers."""
        self.DB_CURSOR.execute("SELECT id, last_name, first_name, middle_name, birth_date, subject, classes FROM teachers")
        return self.DB_CURSOR.fetchall()

    def fetch_all_students(self):
        """Возвращает все строки из таблицы students."""
        self.DB_CURSOR.execute("SELECT id, last_name, first_name, middle_name, birth_date, class_name FROM students")
        return self.DB_CURSOR.fetchall()

    def get_subject_list(self):
        """Возвращает список всех предметов."""
        self.DB_CURSOR.execute("""
            SELECT DISTINCT subject
            FROM teachers
            WHERE subject IS NOT NULL AND subject <> ''
            ORDER BY subject
        """)
        return [row[0] for row in self.DB_CURSOR.fetchall()]

    def get_teacher_fios(self):
        """Возвращает список ФИО учителей."""
        self.DB_CURSOR.execute("""
            SELECT last_name, first_name, COALESCE(middle_name, '')
            FROM teachers
            ORDER BY last_name, first_name, middle_name
        """)
        return self.DB_CURSOR.fetchall()

    def get_class_list(self):
        """Возвращает список классов в школе."""
        self.DB_CURSOR.execute("""
            SELECT DISTINCT class_name
            FROM (
                SELECT UNNEST(class_name) AS class_name
                FROM students
            ) AS t
            WHERE class_name IS NOT NULL AND class_name <> ''
            ORDER BY class_name
        """)
        return [row[0] for row in self.DB_CURSOR.fetchall()]

    def get_teacher_classes_by_name(self, last_name, first_name, middle_name=""):
        """Возвращает массив классов по ФИО учителя."""
        query = """
            SELECT classes
            FROM teachers
            WHERE last_name = %s AND first_name = %s AND COALESCE(middle_name, '') = %s
            LIMIT 1
        """
        self.DB_CURSOR.execute(query, (last_name, first_name, middle_name))
        result = self.DB_CURSOR.fetchone()
        return result[0] if result else []
