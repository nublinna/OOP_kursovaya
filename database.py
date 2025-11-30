import psycopg2

class SchoolDatabase:
    def __init__(self):
        self.DB_CONNECTION = psycopg2.connect(
            dbname="school_db",
            user="postgres",
            password="18072007",
            host="localhost",
            port=5432
        )
        self.DB_CURSOR = self.DB_CONNECTION.cursor()
        self.__create_tables()

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
        get_student_query = """
                        INSERT INTO students (last_name, first_name, 
                        middle_name, class_name)
                        VALUES (%s, %s, %s, %s)
                        """
        self.DB_CURSOR.execute(get_student_query,
                               (
                                   last_name,
                                    first_name,
                                    class_name,
                                    middle_name
                               ))
        self.DB_CONNECTION.commit()

    def update_students(self, student_id, last_name, first_name,
                        class_name, middle_name=""):
        update_student_query = """
            UPDATE students SET last_name = %s, first_name = %s, class_name = %s,
            middle_name = %s
            WHERE id = %s
        """
        self.DB_CURSOR.execute(update_student_query,(last_name, first_name, class_name,
                                                     middle_name, student_id))
        self.DB_CONNECTION.commit()

    def get_students_count(self, class_name=None):
        if class_name:
            self.DB_CURSOR.execute("SELECT COUNT(*) FROM students WHERE class_name=%s", (class_name,))
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
        query = "INSERT INTO grades (student_id, subject_name, grade) VALUES (%s, %s, %s)"
        self.DB_CURSOR.execute(query, (student_id, subject_name, grade))
        self.DB_CONNECTION.commit()

    def delete_student(self, student_id):
        self.DB_CURSOR.execute("DELETE FROM students WHERE id = %s", (student_id,))
        self.DB_CONNECTION.commit()

    def add_teacher(self, last_name, first_name, classes, subject, middle_name=""):
        add_teacher_query = """
                                INSERT INTO teachers (last_name, first_name, 
                                middle_name, subject, classes)
                                VALUES (%s, %s, %s, %s, %s)
                                """
        self.DB_CURSOR.execute(add_teacher_query,
                               (
                                   last_name,
                                   first_name,
                                   classes,
                                   subject,
                                   middle_name
                               ))
        self.DB_CONNECTION.commit()

    def update_teachers(self, teacher_id, last_name, first_name,
                        classes, subject, middle_name=""):
        update_teachers_query = """
                    UPDATE teachers SET last_name = %s, first_name = %s, classes = %s,
                    subject = %s, middle_name = %s
                    WHERE id = %s
                """
        self.DB_CURSOR.execute(update_teachers_query, (last_name, first_name, classes,
                                                      subject, middle_name, teacher_id))
        self.DB_CONNECTION.commit()

    def get_teachers_by_subject(self, subject):
        self.DB_CURSOR.execute("""SELECT last_name, first_name, middle_name
         FROM teachers WHERE subject = %s""", (subject,))
        self.DB_CONNECTION.commit()
        return self.DB_CURSOR.fetchall()

    def get_teachers_by_classes(self, classes):
        self.DB_CURSOR.execute("""SELECT last_name, first_name, middle_name
        FROM teachers WHERE classes = %s""", (classes,))
        self.DB_CONNECTION.commit()
        return self.DB_CURSOR.fetchall()

    def get_teacher_classes(self, teacher_id):
        self.DB_CURSOR.execute("SELECT classes FROM teachers WHERE id = %s", (teacher_id,))
        return self.DB_CURSOR.fetchone()[0]

    def delete_teacher(self, teacher_id):
        self.DB_CURSOR.execute("DELETE FROM teachers WHERE id = %s", (teacher_id,))
        self.DB_CONNECTION.commit()
