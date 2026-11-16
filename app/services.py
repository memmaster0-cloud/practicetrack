"""Бизнес-логика: регистрация, дисциплины, работы, сдачи, отчёты."""
import logging
import re
from datetime import date
from typing import Callable, Dict, List, Optional

from .domain import (Assignment, Role, Status, Subject, Submission, User,
                     days_left, deadline_flag)
from .errors import (AuthError, ConflictError, NotFoundError, PermissionDenied,
                     ValidationError)
from .observers import StatusObserver
from .progress import calculate_progress
from .repositories import (AssignmentRepository, GroupRepository,
                           SubjectRepository, SubmissionRepository,
                           UserRepository)
from .security import (DEFAULT_TOKEN_TTL_SECONDS, create_token, decode_token,
                       hash_password, verify_password)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LEN = 8
log = logging.getLogger("practicetrack.auth")


def _require_role(user: User, role: Role) -> None:
    if user.role != role:
        raise PermissionDenied("Недостаточно прав для этого действия")


def owned_subject(subjects: SubjectRepository, teacher: User, subject_id: int) -> Subject:
    """Возвращает дисциплину, если она существует и принадлежит преподавателю.

    Единая проверка прав: роль преподавателя, существование и владение дисциплиной.
    """
    _require_role(teacher, Role.TEACHER)
    subject = subjects.get(subject_id)
    if not subject:
        raise NotFoundError("Дисциплина не найдена")
    if subject.teacher_id != teacher.id:
        raise PermissionDenied("Это не ваша дисциплина")
    return subject


def _memo(cache: Dict, loader: Callable, key):
    """Загружает объект один раз за операцию: повторные обращения берутся из кэша."""
    if key not in cache:
        cache[key] = loader(key)
    return cache[key]


class AuthService:
    """Регистрация, вход и определение текущего пользователя (FR-01, FR-02)."""

    def __init__(self, users: UserRepository, groups: GroupRepository,
                 secret: str, ttl_seconds: int = DEFAULT_TOKEN_TTL_SECONDS):
        self._users, self._groups = users, groups
        self._secret, self._ttl = secret, ttl_seconds

    def register(self, email: str, password: str, full_name: str,
                 role: Role, group_name: Optional[str] = None) -> User:
        """Создаёт пользователя; студент обязан указать группу."""
        email = email.strip().lower()
        if not EMAIL_RE.match(email):
            raise ValidationError("Некорректный адрес электронной почты")
        if len(password) < MIN_PASSWORD_LEN:
            raise ValidationError(
                f"Пароль должен содержать не менее {MIN_PASSWORD_LEN} символов")
        if not full_name.strip():
            raise ValidationError("Укажите ФИО")
        if self._users.get_by_email(email):
            raise ConflictError("Пользователь с таким email уже существует")
        group_id = None
        if role == Role.STUDENT:
            if not group_name or not group_name.strip():
                raise ValidationError("Студент должен указать группу")
            group_id = self._groups.get_or_create(group_name.strip()).id
        user = User(email=email, password_hash=hash_password(password),
                    full_name=full_name.strip(), role=role, group_id=group_id)
        created = self._users.add(user)
        log.info("registered user id=%s role=%s", created.id, role.value)
        return created

    def login(self, email: str, password: str) -> str:
        """Проверяет пароль и возвращает JWT-токен."""
        user = self._users.get_by_email(email.strip().lower())
        if not user or not verify_password(password, user.password_hash):
            log.warning("failed login attempt")
            raise AuthError("Неверный email или пароль")
        log.info("login user id=%s", user.id)
        return create_token(user.id, user.role.value, self._secret, self._ttl)

    def current_user(self, token: str) -> User:
        """Находит пользователя по токену."""
        user_id, _ = decode_token(token, self._secret)
        user = self._users.get(user_id)
        if not user:
            raise AuthError("Пользователь не найден")
        return user


class SubjectService:
    """Дисциплины преподавателя (FR-03)."""

    def __init__(self, subjects: SubjectRepository, groups: GroupRepository):
        self._subjects, self._groups = subjects, groups

    def create(self, teacher: User, name: str, group_name: str) -> Subject:
        """Создаёт дисциплину для группы; доступно только преподавателю."""
        _require_role(teacher, Role.TEACHER)
        if not name.strip() or not group_name.strip():
            raise ValidationError("Укажите название дисциплины и группу")
        group = self._groups.get_or_create(group_name.strip())
        return self._subjects.add(
            Subject(name=name.strip(), teacher_id=teacher.id, group_id=group.id))

    def list_for_teacher(self, teacher: User) -> List[Subject]:
        """Дисциплины, которые ведёт преподаватель."""
        _require_role(teacher, Role.TEACHER)
        return self._subjects.list_by_teacher(teacher.id)


class AssignmentService:
    """Практические работы дисциплины (FR-04, FR-05)."""

    def __init__(self, assignments: AssignmentRepository, subjects: SubjectRepository,
                 submissions: SubmissionRepository, users: UserRepository):
        self._assignments, self._subjects = assignments, subjects
        self._submissions, self._users = submissions, users

    def create(self, teacher: User, subject_id: int, title: str,
               description: str, deadline: date) -> Assignment:
        """Создаёт работу и сдачи для всех студентов группы дисциплины."""
        subject = owned_subject(self._subjects, teacher, subject_id)
        if not title.strip():
            raise ValidationError("Укажите название работы")
        assignment = self._assignments.add(Assignment(
            subject_id=subject.id, title=title.strip(),
            description=description.strip(), deadline=deadline))
        for student in self._users.list_students(subject.group_id):
            self._submissions.add(Submission(assignment.id, student.id))
        return assignment

    def update(self, teacher: User, assignment_id: int, title: Optional[str] = None,
               description: Optional[str] = None, deadline: Optional[date] = None) -> Assignment:
        """Изменяет переданные поля работы (поля со значением None не меняются)."""
        assignment = self._get(assignment_id)
        owned_subject(self._subjects, teacher, assignment.subject_id)
        if title is not None:
            if not title.strip():
                raise ValidationError("Название не может быть пустым")
            assignment.title = title.strip()
        if description is not None:
            assignment.description = description.strip()
        if deadline is not None:
            assignment.deadline = deadline
        self._assignments.save(assignment)
        return assignment

    def delete(self, teacher: User, assignment_id: int) -> None:
        """Удаляет работу вместе с её сдачами."""
        assignment = self._get(assignment_id)
        owned_subject(self._subjects, teacher, assignment.subject_id)
        self._submissions.delete_by_assignment(assignment.id)
        self._assignments.delete(assignment.id)

    def _get(self, assignment_id: int) -> Assignment:
        assignment = self._assignments.get(assignment_id)
        if not assignment:
            raise NotFoundError("Работа не найдена")
        return assignment


class SubmissionService:
    """Сдачи работ: просмотр, смена статуса, проверка, отчёты (FR-06 … FR-13)."""

    STUDENT_TRANSITIONS = {Status.IN_PROGRESS, Status.SUBMITTED}

    def __init__(self, submissions: SubmissionRepository, assignments: AssignmentRepository,
                 subjects: SubjectRepository, users: UserRepository,
                 observers: Optional[List[StatusObserver]] = None,
                 clock: Callable[[], date] = date.today):
        self._submissions, self._assignments = submissions, assignments
        self._subjects, self._users = subjects, users
        self._observers = list(observers or [])
        self._clock = clock

    def subscribe(self, observer: StatusObserver) -> None:
        """Подписывает наблюдателя на смену статуса сдачи."""
        self._observers.append(observer)

    def _notify(self, submission, old, new):
        for obs in self._observers:
            obs.on_status_changed(submission, old, new)

    @staticmethod
    def _new_cache() -> Dict:
        return {"assignments": {}, "subjects": {}}

    def _view(self, sub: Submission, cache: Optional[Dict] = None) -> Dict:
        """Представление сдачи для интерфейса; cache избавляет от повторных запросов."""
        cache = cache if cache is not None else self._new_cache()
        a = _memo(cache["assignments"], self._assignments.get, sub.assignment_id)
        s = _memo(cache["subjects"], self._subjects.get, a.subject_id)
        today = self._clock()
        return {"id": sub.id, "assignment_id": a.id, "title": a.title,
                "subject_id": s.id, "subject": s.name,
                "deadline": a.deadline.isoformat(), "status": sub.status.value,
                "comment": sub.comment,
                "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
                "days_left": days_left(a.deadline, today),
                "flag": deadline_flag(a.deadline, today, sub.status)}

    def list_for_student(self, student: User, subject_id: Optional[int] = None,
                         status: Optional[Status] = None) -> List[Dict]:
        """Работы студента с фильтрами по дисциплине и статусу, по возрастанию срока."""
        _require_role(student, Role.STUDENT)
        self._ensure_submissions(student)
        cache = self._new_cache()
        views = [self._view(s, cache) for s in self._submissions.list_by_student(student.id)]
        if subject_id is not None:
            views = [v for v in views if v["subject_id"] == subject_id]
        if status is not None:
            views = [v for v in views if v["status"] == status.value]
        return sorted(views, key=lambda v: v["deadline"])

    def progress(self, student: User) -> Dict:
        """Процент принятых работ студента (связь с ПР9)."""
        _require_role(student, Role.STUDENT)
        self._ensure_submissions(student)
        statuses = [s.status for s in self._submissions.list_by_student(student.id)]
        return {"percent": calculate_progress(statuses), "total": len(statuses),
                "accepted": sum(1 for s in statuses if s == Status.ACCEPTED)}

    def _ensure_submissions(self, student: User) -> None:
        """Создаёт сдачи по работам, выданным до регистрации студента (DEF-01)."""
        existing = {s.assignment_id for s in self._submissions.list_by_student(student.id)}
        for subject in self._subjects.list_by_group(student.group_id):
            for assignment in self._assignments.list_by_subject(subject.id):
                if assignment.id not in existing:
                    self._submissions.add(Submission(assignment.id, student.id))

    def change_status_by_student(self, student: User, submission_id: int,
                                 new_status: Status) -> Dict:
        """Студент начинает работу или сдаёт её; остальные переходы запрещены."""
        _require_role(student, Role.STUDENT)
        sub = self._get(submission_id)
        if sub.student_id != student.id:
            raise PermissionDenied("Это не ваша сдача")
        if new_status not in self.STUDENT_TRANSITIONS:
            raise PermissionDenied("Студент может только начать работу или сдать её")
        old = sub.change_status(new_status)
        self._submissions.save(sub)
        self._notify(sub, old, new_status)
        return self._view(sub)

    def review(self, teacher: User, submission_id: int, accept: bool,
               comment: str = "") -> Dict:
        """Преподаватель принимает работу или возвращает её на доработку с комментарием."""
        _require_role(teacher, Role.TEACHER)
        sub = self._get(submission_id)
        assignment = self._assignments.get(sub.assignment_id)
        if not assignment:
            raise NotFoundError("Работа не найдена")
        owned_subject(self._subjects, teacher, assignment.subject_id)
        new = Status.ACCEPTED if accept else Status.REWORK
        old = sub.change_status(new, comment)
        self._submissions.save(sub)
        self._notify(sub, old, new)
        return self._view(sub)

    def list_for_assignment(self, teacher: User, assignment_id: int) -> List[Dict]:
        """Сдачи студентов группы по выбранной работе (FR-12)."""
        _require_role(teacher, Role.TEACHER)
        assignment = self._assignments.get(assignment_id)
        if not assignment:
            raise NotFoundError("Работа не найдена")
        owned_subject(self._subjects, teacher, assignment.subject_id)
        rows = []
        for sub in self._submissions.list_by_assignment(assignment_id):
            student = self._users.get(sub.student_id)
            rows.append({"submission_id": sub.id, "student": student.full_name,
                         "status": sub.status.value, "comment": sub.comment})
        return sorted(rows, key=lambda r: r["student"])

    def debtors_report(self, teacher: User, subject_id: int) -> List[Dict]:
        """FR-13: студенты и непринятые работы по дисциплине."""
        owned_subject(self._subjects, teacher, subject_id)
        rows = []
        for assignment in self._assignments.list_by_subject(subject_id):
            for sub in self._submissions.list_by_assignment(assignment.id):
                if sub.status != Status.ACCEPTED:
                    student = self._users.get(sub.student_id)
                    rows.append({"student": student.full_name,
                                 "assignment": assignment.title,
                                 "status": sub.status.value})
        return sorted(rows, key=lambda r: (r["student"], r["assignment"]))

    def _get(self, submission_id: int) -> Submission:
        sub = self._submissions.get(submission_id)
        if not sub:
            raise NotFoundError("Сдача не найдена")
        return sub
