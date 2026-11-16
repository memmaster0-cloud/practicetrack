"""Логирование в stdout: контейнер не хранит файлы логов, их собирает Docker."""
import logging
import sys

FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_HANDLER_NAME = "practicetrack-stdout"


def configure_logging(level: str = "INFO") -> logging.Logger:
    """Настраивает корневой логгер приложения; повторный вызов не дублирует обработчики."""
    logger = logging.getLogger("practicetrack")
    logger.setLevel(level)
    if not any(h.get_name() == _HANDLER_NAME for h in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.set_name(_HANDLER_NAME)
        handler.setFormatter(logging.Formatter(FORMAT))
        logger.addHandler(handler)
    logger.propagate = False
    return logger
