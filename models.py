"""Простые модели Teacher, Student и GradeRecord для GUI."""

from abc import ABC, abstractmethod
from typing import Iterable, List


class BasePerson(ABC):
    """Простой базовый класс. В нём приватные поля и общая логика."""

    def __init__(self, last_name: str, first_name: str, middle_name: str = ""):
        self._last_name = last_name.strip()
        self._first_name = first_name.strip()
        self._middle_name = middle_name.strip()

    @property
    def last_name(self):
        return self._last_name

    @property
    def first_name(self):
        return self._first_name

    @property
    def middle_name(self):
        return self._middle_name

    @property
    def full_name(self):
        parts = [self._last_name, self._first_name, self._middle_name]
        return " ".join(part for part in parts if part)

    def copy(self):
        return type(self)(self._last_name, self._first_name, self._middle_name)

    @abstractmethod
    def to_display_tuple(self):
        pass

    @abstractmethod
    def to_db_payload(self):
        pass


class Teacher(BasePerson):
    """Наследник BasePerson для учителей."""

    def __init__(self, last_name: str, first_name: str, middle_name: str,
                 subject: str, classes: Iterable[str]):
        super().__init__(last_name, first_name, middle_name)
        self._subject = subject.strip()
        self._classes = [cls.strip() for cls in classes if cls and cls.strip()]

    @property
    def subject(self):
        return self._subject

    @property
    def classes(self):
        return list(self._classes)

    def to_display_tuple(self):
        return self.full_name, self._subject, ", ".join(self._classes)

    def to_db_payload(self):
        return (self.last_name, self.first_name,
                self.middle_name, self._subject, self.classes)


class Student(BasePerson):
    """Наследник BasePerson для учеников."""

    def __init__(self, last_name: str, first_name: str, middle_name: str,
                 classes: Iterable[str]):
        super().__init__(last_name, first_name, middle_name)
        self._classes = [cls.strip() for cls in classes if cls and cls.strip()]

    @property
    def classes(self):
        return list(self._classes)

    def to_display_tuple(self):
        return self.full_name, ", ".join(self._classes)

    def to_db_payload(self):
        return self.last_name, self.first_name, self.middle_name, self.classes


class GradeRecord:
    """Простой класс оценки. Здесь хранится id ученика и его оценка."""

    def __init__(self, student_id: int, subject: str, grade: int):
        self._student_id = student_id
        self._subject = subject.strip()
        self._grade = int(grade)

    @property
    def student_id(self):
        return self._student_id

    @property
    def subject(self):
        return self._subject

    @property
    def grade(self):
        return self._grade

    def to_display_tuple(self, student_name: str):
        return student_name, self._subject, str(self._grade)

