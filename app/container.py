"""Контейнер зависимостей: собирает сервисы поверх репозиториев (память или SQL)."""
from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Iterator, Optional

from .observers import LoggingObserver, StatusObserver
from .repositories import (AssignmentRepository, GroupRepository, InMemoryAssignmentRepository,
                           InMemoryGroupRepository, InMemorySubjectRepository,
                           InMemorySubmissionRepository, InMemoryUserRepository,
                           SubjectRepository, SubmissionRepository, UserRepository)
from .security import DEFAULT_TOKEN_TTL_SECONDS
from .services import AssignmentService, AuthService, SubjectService, SubmissionService


@dataclass
class Repositories:
    """Набор репозиториев, на которых строятся сервисы (параметр-объект)."""
    users: UserRepository
    groups: GroupRepository
    subjects: SubjectRepository
    assignments: AssignmentRepository
    submissions: SubmissionRepository


@dataclass
class Container:
    """Сервисы приложения и функция фиксации транзакции."""
    auth: AuthService
    subjects: SubjectService
    assignments: AssignmentService
    submissions: SubmissionService
    commit: Callable[[], None] = field(default=lambda: None)


def _build(repos: Repositories, secret, ttl, clock, observers, commit) -> Container:
    return Container(
        auth=AuthService(repos.users, repos.groups, secret, ttl),
        subjects=SubjectService(repos.subjects, repos.groups),
        assignments=AssignmentService(repos.assignments, repos.subjects, repos.submissions,
                                      repos.users),
        submissions=SubmissionService(repos.submissions, repos.assignments, repos.subjects,
                                      repos.users, observers=observers, clock=clock),
        commit=commit)


def build_memory_container(secret: str = "test-secret", ttl: int = DEFAULT_TOKEN_TTL_SECONDS,
                           clock: Callable[[], date] = date.today,
                           observers: Optional[list[StatusObserver]] = None) -> Container:
    """Контейнер с репозиториями в памяти: для тестов и быстрых проверок."""
    repos = Repositories(InMemoryUserRepository(), InMemoryGroupRepository(),
                         InMemorySubjectRepository(), InMemoryAssignmentRepository(),
                         InMemorySubmissionRepository())
    return _build(repos, secret, ttl, clock, observers or [], lambda: None)


def build_sql_container(session, secret: str, ttl: int,
                        clock: Callable[[], date] = date.today) -> Container:
    """Контейнер с репозиториями SQLAlchemy на одном сеансе БД."""
    from .db.repositories import (SqlAssignmentRepository, SqlGroupRepository,
                                  SqlSubjectRepository, SqlSubmissionRepository,
                                  SqlUserRepository)
    repos = Repositories(SqlUserRepository(session), SqlGroupRepository(session),
                         SqlSubjectRepository(session), SqlAssignmentRepository(session),
                         SqlSubmissionRepository(session))
    return _build(repos, secret, ttl, clock, [LoggingObserver()], session.commit)


def sql_container_dependency(session_factory, secret: str, ttl: int):
    """Возвращает зависимость FastAPI: один сеанс БД на запрос."""
    def dependency() -> Iterator[Container]:
        session = session_factory()
        try:
            yield build_sql_container(session, secret, ttl)
        finally:
            session.close()
    return dependency
