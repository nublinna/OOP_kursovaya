import random
xml_declaration = True
from xml.etree.ElementTree import Element, SubElement, ElementTree


random.seed(7)


first_names = [
    "Алексей", "Иван", "Сергей", "Дмитрий", "Никита", "Павел",
    "Мария", "Анна", "Екатерина", "Ольга", "София", "Виктория",
    "Максим", "Антон", "Кирилл", "Карина", "Ангелина", "Виктор",
    "Елена", "Даниил", "Денис", "Людмила", "Евгений", "Евгения",
    "Михаил", "Артём", "Александр", "Роман", "Юлия", "Вероника",
    "Илья", "Андрей", "Владимир", "Вера", "Василина"
]

middle_names = [
    "Алексеевич", "Иванович", "Сергеевич", "Павлович",
    "Алексеевна", "Ивановна", "Сергеевна", "Павловна",
    "Денисович", "Денисовна", "Викторович", "Викторовна",
    "Михайлович", "Михайловна", "Александрович", "Александровна",
    "Романович", "Романовна", "Дмитриевич", "Дмитриевна",
    "Кириллович", "Кирилловна", "Антонович", "Антонова",
    "Андреевич", "Андреевна", "Аркадьевич", "Аркадьевна",
    "Ильич", "Владимирович", "Владимировна", "Максимович",
    "Максимовна"
]

last_names = [
    "Иванов", "Петров", "Сидоров", "Кузнецов", "Смирнов",
    "Попов", "Орлова", "Морозова", "Васильева", "Федорова",
    "Жуков", "Соколова", "Титова", "Назаров", "Ефимова",
    "Кириллова", "Борисов", "Громов", "Николаева", "Романова",
    "Алексеев", "Мирошниченко", "Кузьмин", "Машеров", "Берг",
    "Абрамович", "Козлов", "Козлова", "Беляев", "Астапенко",
    "Петрашко", "Зубаревич", "Калиновский", "Адамович", "Мицкевич",
    "Мурашко", "Новицкий", "Полищук", "Протасевич", "Юденич"
]


class_structure = {}
for grade in range(1, 5):
    class_structure[grade] = ["А", "Б", "В"]
for grade in range(5, 10):
    class_structure[grade] = ["А", "Б"]
for grade in (10, 11):
    class_structure[grade] = ["А", "Б"]


primary_subjects = [
    "Русский язык", "Русская литература", "Иностранный язык",
    "Музыка", "ИЗО", "Физкультура", "Математика", "Человек и мир"
]

middle_subjects = [
    "Русский язык", "Русская литература", "Английский язык",
    "Немецкий язык", "История России", "Всемирная история",
    "Математика", "Физика", "Химия", "Биология", "География",
    "Информатика", "ОБЖ", "Физкультура"
]

upper_subjects = middle_subjects + ["Обществознание", "Экономика"]


subject_ranges = {
    "Начальные классы": (1, 4),
    "Русский язык": (1, 11),
    "Русская литература": (1, 11),
    "Иностранный язык": (1, 4),
    "Музыка": (1, 4),
    "ИЗО": (1, 4),
    "Физкультура": (1, 11),
    "Математика": (1, 11),
    "Человек и мир": (1, 4),
    "Английский язык": (5, 11),
    "Немецкий язык": (5, 11),
    "История России": (5, 11),
    "Всемирная история": (5, 11),
    "Физика": (7, 11),
    "Химия": (7, 11),
    "Биология": (5, 11),
    "География": (5, 11),
    "Информатика": (7, 11),
    "ОБЖ": (5, 11),
    "Обществознание": (8, 11),
    "Экономика": (10, 11),
}


def next_name(index):
    last = last_names[index % len(last_names)]
    first = first_names[(index // len(last_names)) % len(first_names)]
    middle = middle_names[(index // (len(last_names) * len(first_names))) % len(middle_names)]
    return f"{last} {first} {middle}"


def classes_in_range(start_grade, end_grade):
    result = []
    for grade, letters in class_structure.items():
        if start_grade <= grade <= end_grade:
            for letter in letters:
                result.append(f"{grade}{letter}")
    return result


def subjects_for_grade(grade):
    if grade <= 2:
        return primary_subjects
    if grade <= 4:
        return primary_subjects
    if grade <= 9:
        return middle_subjects
    return upper_subjects


teacher_records = []
teacher_index = 0


for grade in range(1, 5):
    for letter in class_structure[grade]:
        teacher_records.append({
            "fio": next_name(teacher_index),
            "subject": "Начальные классы",
            "classes": f"{grade}{letter}"
        })
        teacher_index += 1


subjects_for_teachers = sorted(subject_ranges.keys())

for subject in subjects_for_teachers:
    if subject == "Начальные классы":
        continue
    start, end = subject_ranges[subject]
    relevant_classes = classes_in_range(start, end)
    if not relevant_classes:
        continue
    split_point = len(relevant_classes) // 2 or 1
    class_groups = [relevant_classes[:split_point], relevant_classes[split_point:]]
    for classes in class_groups:
        teacher_records.append({
            "fio": next_name(teacher_index),
            "subject": subject,
            "classes": ", ".join(classes)
        })
        teacher_index += 1


students = []
student_index = 0

for grade, letters in class_structure.items():
    for letter in letters:
        class_name = f"{grade}{letter}"
        for _ in range(12):
            fio = next_name(student_index)
            students.append({
                "fio": fio,
                "class": class_name,
                "grade": grade,
                "subjects": subjects_for_grade(grade)
            })
            student_index += 1


grades = []

for student in students:
    if student["grade"] <= 2:
        continue
    for subject in student["subjects"]:
        value = random.choice(["3", "4", "5"])
        grades.append({
            "fio": student["fio"],
            "subject": subject,
            "value": value
        })


def write_teachers(filename):
    root = Element("school_data")
    teachers_el = SubElement(root, "teachers")
    for teacher in teacher_records:
        el = SubElement(teachers_el, "teacher")
        el.set("fio", teacher["fio"])
        el.set("subject", teacher["subject"])
        el.set("classes", teacher["classes"])
    ElementTree(root).write(filename, encoding="utf-8", xml_declaration=True)


def write_students(filename):
    root = Element("school_data")
    students_el = SubElement(root, "students")
    for student in students:
        el = SubElement(students_el, "student")
        el.set("fio", student["fio"])
        el.set("class", student["class"])
    ElementTree(root).write(filename, encoding="utf-8", xml_declaration=True)


def write_grades(filename):
    root = Element("school_data")
    grades_el = SubElement(root, "grades")
    for grade in grades:
        el = SubElement(grades_el, "grade")
        el.set("fio", grade["fio"])
        el.set("subject", grade["subject"])
        el.set("value", grade["value"])
    ElementTree(root).write(filename, encoding="utf-8", xml_declaration=True)


write_teachers("teachers_data.xml")
write_students("students_data.xml")
write_grades("grades_data.xml")

