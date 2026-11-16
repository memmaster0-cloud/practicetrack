"""Окружение behave: добавляем корень проекта в путь импорта."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
