"""Паттерн Observer: уведомления о смене статуса (из ПР5)."""
import logging
from abc import ABC, abstractmethod
from typing import List

from .domain import Status, Submission


class StatusObserver(ABC):
    """Подписчик на смену статуса сдачи (паттерн Observer)."""

    @abstractmethod
    def on_status_changed(self, submission: Submission, old: Status, new: Status) -> None:
        """Вызывается после успешной смены статуса."""


class RecordingObserver(StatusObserver):
    """Сохраняет события в списке: используется для журнала и в тестах."""
    def __init__(self):
        self.events: List[tuple] = []

    def on_status_changed(self, submission, old, new):
        self.events.append((submission.id, old.value, new.value))


class LoggingObserver(StatusObserver):
    """Пишет в журнал каждую смену статуса (без персональных данных)."""
    def __init__(self, logger: logging.Logger = None):
        self._log = logger or logging.getLogger("practicetrack.submissions")

    def on_status_changed(self, submission, old, new):
        self._log.info("submission=%s status %s -> %s", submission.id, old.value, new.value)
