"""Абстрактные репозитории и реализации в памяти (используются в тестах)."""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from .domain import Assignment, Group, Role, Subject, Submission, User


class UserRepository(ABC):
    """Хранилище пользователей."""

    @abstractmethod
    def add(self, user: User) -> User: ...
    @abstractmethod
    def get(self, user_id: int) -> Optional[User]: ...
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]: ...
    @abstractmethod
    def list_students(self, group_id: int) -> List[User]: ...


class GroupRepository(ABC):
    """Хранилище групп."""

    @abstractmethod
    def get_or_create(self, name: str) -> Group: ...
    @abstractmethod
    def get(self, group_id: int) -> Optional[Group]: ...


class SubjectRepository(ABC):
    """Хранилище дисциплин."""

    @abstractmethod
    def add(self, subject: Subject) -> Subject: ...
    @abstractmethod
    def get(self, subject_id: int) -> Optional[Subject]: ...
    @abstractmethod
    def list_by_group(self, group_id: int) -> List[Subject]: ...
    @abstractmethod
    def list_by_teacher(self, teacher_id: int) -> List[Subject]: ...


class AssignmentRepository(ABC):
    """Хранилище практических работ."""

    @abstractmethod
    def add(self, assignment: Assignment) -> Assignment: ...
    @abstractmethod
    def get(self, assignment_id: int) -> Optional[Assignment]: ...
    @abstractmethod
    def save(self, assignment: Assignment) -> None: ...
    @abstractmethod
    def delete(self, assignment_id: int) -> None: ...
    @abstractmethod
    def list_by_subject(self, subject_id: int) -> List[Assignment]: ...


class SubmissionRepository(ABC):
    """Хранилище сдач."""

    @abstractmethod
    def add(self, submission: Submission) -> Submission: ...
    @abstractmethod
    def get(self, submission_id: int) -> Optional[Submission]: ...
    @abstractmethod
    def save(self, submission: Submission) -> None: ...
    @abstractmethod
    def delete_by_assignment(self, assignment_id: int) -> None: ...
    @abstractmethod
    def list_by_student(self, student_id: int) -> List[Submission]: ...
    @abstractmethod
    def list_by_assignment(self, assignment_id: int) -> List[Submission]: ...


class _MemoryBase:
    def __init__(self):
        self._items: Dict[int, object] = {}
        self._next = 1

    def _insert(self, obj):
        obj.id = self._next
        self._items[obj.id] = obj
        self._next += 1
        return obj


class InMemoryUserRepository(_MemoryBase, UserRepository):
    """Пользователи в памяти (для тестов)."""

    def add(self, user): return self._insert(user)
    def get(self, user_id): return self._items.get(user_id)

    def get_by_email(self, email):
        return next((u for u in self._items.values() if u.email == email), None)

    def list_students(self, group_id):
        return [u for u in self._items.values()
                if u.group_id == group_id and u.role == Role.STUDENT]


class InMemoryGroupRepository(_MemoryBase, GroupRepository):
    """Группы в памяти (для тестов)."""

    def get_or_create(self, name):
        found = next((g for g in self._items.values() if g.name == name), None)
        return found or self._insert(Group(name=name))

    def get(self, group_id): return self._items.get(group_id)


class InMemorySubjectRepository(_MemoryBase, SubjectRepository):
    """Дисциплины в памяти (для тестов)."""

    def add(self, subject): return self._insert(subject)
    def get(self, subject_id): return self._items.get(subject_id)

    def list_by_group(self, group_id):
        return [s for s in self._items.values() if s.group_id == group_id]

    def list_by_teacher(self, teacher_id):
        return [s for s in self._items.values() if s.teacher_id == teacher_id]


class InMemoryAssignmentRepository(_MemoryBase, AssignmentRepository):
    """Работы в памяти (для тестов)."""

    def add(self, assignment): return self._insert(assignment)
    def get(self, assignment_id): return self._items.get(assignment_id)
    def save(self, assignment): self._items[assignment.id] = assignment
    def delete(self, assignment_id): self._items.pop(assignment_id, None)

    def list_by_subject(self, subject_id):
        return [a for a in self._items.values() if a.subject_id == subject_id]


class InMemorySubmissionRepository(_MemoryBase, SubmissionRepository):
    """Сдачи в памяти (для тестов)."""

    def add(self, submission): return self._insert(submission)
    def get(self, submission_id): return self._items.get(submission_id)
    def save(self, submission): self._items[submission.id] = submission

    def delete_by_assignment(self, assignment_id):
        for sid in [s.id for s in self._items.values() if s.assignment_id == assignment_id]:
            del self._items[sid]

    def list_by_student(self, student_id):
        return [s for s in self._items.values() if s.student_id == student_id]

    def list_by_assignment(self, assignment_id):
        return [s for s in self._items.values() if s.assignment_id == assignment_id]
