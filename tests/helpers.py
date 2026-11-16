"""Общая подготовка окружения для тестов."""
from datetime import date

from app.domain import Role
from app.observers import RecordingObserver
from app.repositories import (InMemoryAssignmentRepository, InMemoryGroupRepository,
                              InMemorySubjectRepository, InMemorySubmissionRepository,
                              InMemoryUserRepository)
from app.services import (AssignmentService, AuthService, SubjectService,
                          SubmissionService)

TODAY = date(2026, 11, 9)
PASSWORD = "secret123"


class Env:
    def __init__(self):
        self.users = InMemoryUserRepository()
        self.groups = InMemoryGroupRepository()
        self.subjects = InMemorySubjectRepository()
        self.assignments = InMemoryAssignmentRepository()
        self.submissions = InMemorySubmissionRepository()
        self.observer = RecordingObserver()
        self.auth = AuthService(self.users, self.groups, secret="test-secret")
        self.subject_service = SubjectService(self.subjects, self.groups)
        self.assignment_service = AssignmentService(
            self.assignments, self.subjects, self.submissions, self.users)
        self.submission_service = SubmissionService(
            self.submissions, self.assignments, self.subjects, self.users,
            observers=[self.observer], clock=lambda: TODAY)

    def teacher(self, email="teacher@example.kz", name="Преподаватель П."):
        return self.auth.register(email, PASSWORD, name, Role.TEACHER)

    def student(self, email="student@example.kz", name="Студент С.", group="БИС 31с"):
        return self.auth.register(email, PASSWORD, name, Role.STUDENT, group)

    def setup_course(self, deadline=date(2026, 11, 20)):
        """Преподаватель, дисциплина, один студент и одна работа."""
        t = self.teacher()
        s = self.student()
        subject = self.subject_service.create(t, "Технологии разработки ПО", "БИС 31с")
        a = self.assignment_service.create(t, subject.id, "ПР1", "Анализ", deadline)
        sub = self.submissions.list_by_student(s.id)[0]
        return t, s, subject, a, sub
