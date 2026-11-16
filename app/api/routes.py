"""REST API ПрактикаТрек: ресурсы с именами-существительными, коды 200/201/204/4xx."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..container import Container
from ..domain import Status, User
from . import schemas as sc

router = APIRouter(prefix="/api")
bearer = HTTPBearer(auto_error=False)


def get_container() -> Container:
    """Заменяется при настройке приложения (SQL в проде, память в тестах)."""
    raise RuntimeError("Контейнер зависимостей не настроен")


def current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
                 c: Container = Depends(get_container)) -> User:
    if creds is None:
        raise HTTPException(status_code=401, detail="Требуется авторизация",
                            headers={"WWW-Authenticate": "Bearer"})
    return c.auth.current_user(creds.credentials)


def _assignment_out(a) -> sc.AssignmentOut:
    return sc.AssignmentOut(id=a.id, subject_id=a.subject_id, title=a.title,
                            description=a.description, deadline=a.deadline)


# --- Аутентификация -------------------------------------------------------------------

@router.post("/auth/register", response_model=sc.UserOut, status_code=201, tags=["auth"],
             summary="Регистрация пользователя")
def register(body: sc.RegisterRequest, c: Container = Depends(get_container)):
    user = c.auth.register(body.email, body.password, body.full_name, body.role, body.group)
    c.commit()
    return sc.UserOut(id=user.id, email=user.email, full_name=user.full_name,
                      role=user.role, group_id=user.group_id)


@router.post("/auth/login", response_model=sc.TokenOut, tags=["auth"],
             summary="Вход: получение токена")
def login(body: sc.LoginRequest, c: Container = Depends(get_container)):
    return sc.TokenOut(access_token=c.auth.login(body.email, body.password))


@router.get("/auth/me", response_model=sc.UserOut, tags=["auth"],
            summary="Текущий пользователь")
def me(user: User = Depends(current_user)):
    return sc.UserOut(id=user.id, email=user.email, full_name=user.full_name,
                      role=user.role, group_id=user.group_id)


# --- Дисциплины и работы (преподаватель) -----------------------------------------------

@router.post("/subjects", response_model=sc.SubjectOut, status_code=201, tags=["subjects"],
             summary="Создать дисциплину")
def create_subject(body: sc.SubjectCreate, user: User = Depends(current_user),
                   c: Container = Depends(get_container)):
    s = c.subjects.create(user, body.name, body.group)
    c.commit()
    return sc.SubjectOut(id=s.id, name=s.name, group_id=s.group_id)


@router.get("/subjects", response_model=List[sc.SubjectOut], tags=["subjects"],
            summary="Мои дисциплины (преподаватель)")
def list_subjects(user: User = Depends(current_user), c: Container = Depends(get_container)):
    return [sc.SubjectOut(id=s.id, name=s.name, group_id=s.group_id)
            for s in c.subjects.list_for_teacher(user)]


@router.post("/subjects/{subject_id}/assignments", response_model=sc.AssignmentOut,
             status_code=201, tags=["assignments"], summary="Добавить практическую работу")
def create_assignment(subject_id: int, body: sc.AssignmentCreate,
                      user: User = Depends(current_user),
                      c: Container = Depends(get_container)):
    a = c.assignments.create(user, subject_id, body.title, body.description, body.deadline)
    c.commit()
    return _assignment_out(a)


@router.patch("/assignments/{assignment_id}", response_model=sc.AssignmentOut,
              tags=["assignments"], summary="Изменить практическую работу")
def update_assignment(assignment_id: int, body: sc.AssignmentUpdate,
                      user: User = Depends(current_user),
                      c: Container = Depends(get_container)):
    a = c.assignments.update(user, assignment_id, body.title, body.description, body.deadline)
    c.commit()
    return _assignment_out(a)


@router.delete("/assignments/{assignment_id}", status_code=204, tags=["assignments"],
               summary="Удалить практическую работу")
def delete_assignment(assignment_id: int, user: User = Depends(current_user),
                      c: Container = Depends(get_container)):
    c.assignments.delete(user, assignment_id)
    c.commit()
    return Response(status_code=204)


@router.get("/assignments/{assignment_id}/submissions", response_model=List[sc.SubmissionRowOut],
            tags=["assignments"], summary="Сдачи группы по работе (преподаватель)")
def assignment_submissions(assignment_id: int, user: User = Depends(current_user),
                           c: Container = Depends(get_container)):
    return c.submissions.list_for_assignment(user, assignment_id)


@router.get("/subjects/{subject_id}/debtors", response_model=List[sc.DebtorOut],
            tags=["reports"], summary="Отчёт о задолженностях (преподаватель)")
def debtors(subject_id: int, user: User = Depends(current_user),
            c: Container = Depends(get_container)):
    return c.submissions.debtors_report(user, subject_id)


# --- Сдачи (студент и преподаватель) ---------------------------------------------------

@router.get("/submissions", response_model=List[sc.SubmissionOut], tags=["submissions"],
            summary="Мои работы (студент) с фильтрами")
def list_submissions(subject_id: Optional[int] = None, status: Optional[Status] = None,
                     user: User = Depends(current_user),
                     c: Container = Depends(get_container)):
    rows = c.submissions.list_for_student(user, subject_id, status)
    c.commit()
    return rows


@router.get("/submissions/progress", response_model=sc.ProgressOut, tags=["submissions"],
            summary="Прогресс студента: процент принятых работ")
def progress(user: User = Depends(current_user), c: Container = Depends(get_container)):
    result = c.submissions.progress(user)
    c.commit()
    return result


@router.patch("/submissions/{submission_id}/status", response_model=sc.SubmissionOut,
              tags=["submissions"], summary="Студент: начать работу или сдать её")
def change_status(submission_id: int, body: sc.StatusChange,
                  user: User = Depends(current_user), c: Container = Depends(get_container)):
    view = c.submissions.change_status_by_student(user, submission_id, body.status)
    c.commit()
    return view


@router.post("/submissions/{submission_id}/review", response_model=sc.SubmissionOut,
             tags=["submissions"], summary="Преподаватель: принять или вернуть на доработку")
def review(submission_id: int, body: sc.ReviewRequest, user: User = Depends(current_user),
           c: Container = Depends(get_container)):
    view = c.submissions.review(user, submission_id, body.accept, body.comment)
    c.commit()
    return view
