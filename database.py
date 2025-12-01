import os
import psycopg2

class SchoolDatabase:
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

    def _prepare_array(self, values):
        """Преобразует разные входные форматы в список строк для TEXT[]"""
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
        students_table = """
                            CREATE TABLE IF NOT EXISTS students (
                                id SERIAL PRIMARY KEY,
                                last_name VARCHAR(50),
                                first_name VARCHAR(50),
                                middle_name VARCHAR(50),
                                class_name TEXT[]
                            );
                        """
        teachers_table = """
                            CREATE TABLE IF NOT EXISTS teachers (
                                id SERIAL PRIMARY KEY,
                                last_name VARCHAR(50),
                                first_name VARCHAR(50),
                                middle_name VARCHAR(50),
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
        self.DB_CONNECTION.commit()

    def add_student(self, last_name, first_name, class_name,  middle_name=""):
        insert_student_query = """
                        INSERT INTO students (last_name, first_name,
                        middle_name, class_name)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                        """
        class_array = self._prepare_array(class_name)

        self.DB_CURSOR.execute(
            insert_student_query,
            (last_name, first_name, middle_name, class_array)
        )
        student_id = self.DB_CURSOR.fetchone()[0]
        self.DB_CONNECTION.commit()
        return student_id

    def update_students(self, student_id, last_name, first_name,
                        class_name, middle_name=""):
        update_student_query = """
            UPDATE students SET last_name = %s, first_name = %s, class_name = %s,
            middle_name = %s
            WHERE id = %s
        """
        class_array = self._prepare_array(class_name)
        self.DB_CURSOR.execute(update_student_query,(last_name, first_name, class_array,
                                                     middle_name, student_id))
        self.DB_CONNECTION.commit()

    def get_students_count(self, class_name=None):
        if class_name:
            query = "SELECT COUNT(*) FROM students WHERE %s = ANY(class_name)"
            self.DB_CURSOR.execute(query, (class_name,))
        else:
            self.DB_CURSOR.execute("SELECT COUNT(*) FROM students")
        return self.DB_CURSOR.fetchone()[0]

    def get_grades(self):
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
                HAVING AVG(grade) < 3
                
                )
            """)
        bad_students = self.DB_CURSOR.fetchall()

        return {
            'good_students': good_students,
            'bad_students': bad_students,
            'total_students': self.get_students_count()
        }

    def add_grade(self, student_id, subject_name, grade):
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
        self.DB_CURSOR.execute("DELETE FROM grades WHERE student_id = %s", (student_id,))
        self.DB_CURSOR.execute("DELETE FROM students WHERE id = %s", (student_id,))
        self.DB_CONNECTION.commit()

    def add_teacher(self, last_name, first_name, subject, classes, middle_name=""):
        add_teacher_query = """
                                INSERT INTO teachers (last_name, first_name, 
                                middle_name, subject, classes)
                                VALUES (%s, %s, %s, %s, %s)
                                RETURNING id
                                """
        classes_array = self._prepare_array(classes)

        self.DB_CURSOR.execute(
            add_teacher_query,
            (last_name, first_name, middle_name, subject, classes_array)
        )
        teacher_id = self.DB_CURSOR.fetchone()[0]
        self.DB_CONNECTION.commit()
        return teacher_id

    def update_teachers(self, teacher_id, last_name, first_name,
                        subject, classes, middle_name=""):
        update_teachers_query = """
                    UPDATE teachers SET last_name = %s, first_name = %s, subject = %s,
                    classes = %s, middle_name = %s
                    WHERE id = %s
                """
        classes_array = self._prepare_array(classes)
        self.DB_CURSOR.execute(
            update_teachers_query,
            (last_name, first_name, subject, classes_array, middle_name, teacher_id)
        )
        self.DB_CONNECTION.commit()

    def get_teachers_by_subject(self, subject):
        self.DB_CURSOR.execute("""SELECT last_name, first_name, middle_name
         FROM teachers WHERE subject = %s""", (subject,))
        return self.DB_CURSOR.fetchall()

    def get_teachers_by_classes(self, classes):
        self.DB_CURSOR.execute("""SELECT last_name, first_name, middle_name
        FROM teachers WHERE classes = %s""", (classes,))
        return self.DB_CURSOR.fetchall()

    def get_teacher_classes(self, teacher_id):
        self.DB_CURSOR.execute("SELECT classes FROM teachers WHERE id = %s", (teacher_id,))
        return self.DB_CURSOR.fetchone()[0]

    def delete_teacher(self, teacher_id):
        self.DB_CURSOR.execute("DELETE FROM teachers WHERE id = %s", (teacher_id,))
        self.DB_CONNECTION.commit()

    def get_all_grades_rows(self):
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
        query = """
            UPDATE grades
            SET student_id = %s, subject_name = %s, grade = %s
            WHERE id = %s
        """
        self.DB_CURSOR.execute(query, (student_id, subject_name, grade, grade_id))
        self.DB_CONNECTION.commit()

    def delete_grade(self, grade_id):
        self.DB_CURSOR.execute("DELETE FROM grades WHERE id = %s", (grade_id,))
        self.DB_CONNECTION.commit()

    def find_student_id(self, last_name, first_name, middle_name=""):
        query = """
            SELECT id FROM students
            WHERE last_name = %s AND first_name = %s AND COALESCE(middle_name, '') = %s
        """
        self.DB_CURSOR.execute(query, (last_name, first_name, middle_name))
        result = self.DB_CURSOR.fetchone()
        return result[0] if result else None

    def teacher_exists(self, last_name, first_name, middle_name, subject):
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
        self.DB_CURSOR.execute("DELETE FROM teachers")
        self.DB_CONNECTION.commit()

    def get_subject_list(self):
        self.DB_CURSOR.execute("""
            SELECT DISTINCT subject
            FROM teachers
            WHERE subject IS NOT NULL AND subject <> ''
            ORDER BY subject
        """)
        return [row[0] for row in self.DB_CURSOR.fetchall()]

    def get_teacher_fios(self):
        self.DB_CURSOR.execute("""
            SELECT last_name, first_name, COALESCE(middle_name, '')
            FROM teachers
            ORDER BY last_name, first_name, middle_name
        """)
        return self.DB_CURSOR.fetchall()

    def get_class_list(self):
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
        query = """
            SELECT classes
            FROM teachers
            WHERE last_name = %s AND first_name = %s AND COALESCE(middle_name, '') = %s
            LIMIT 1
        """
        self.DB_CURSOR.execute(query, (last_name, first_name, middle_name))
        result = self.DB_CURSOR.fetchone()
        return result[0] if result else []
