"""Проверка миграций без установки Alembic и SQLAlchemy.

Скрипт подставляет упрощённые заменители op и sa, превращающие вызовы миграций в SQL для
SQLite, выполняет upgrade и downgrade и сравнивает результат со схемой db/schema.sql и с
моделями app/db/models.py. Это проверка содержимого миграций, а не замена `alembic upgrade`.
"""
import ast
import importlib.util
import re
import sqlite3
import sys
import types
from contextlib import contextmanager

TYPES = {"Integer": "INTEGER", "Text": "TEXT", "Date": "DATE", "DateTime": "DATETIME"}


class T:
    def __init__(self, kind, length=None):
        self.sql = f"VARCHAR({length})" if kind == "String" else TYPES[kind]


class Column:
    def __init__(self, name, type_, nullable=True, server_default=None):
        self.name, self.type, self.nullable, self.default = name, type_, nullable, server_default

    def ddl(self):
        out = f"{self.name} {self.type.sql}"
        if not self.nullable:
            out += " NOT NULL"
        if self.default is not None:
            out += f" DEFAULT '{self.default}'"
        return out


def _named(name):
    return f"CONSTRAINT {name} " if name else ""


class PrimaryKeyConstraint:
    def __init__(self, *cols):
        self.ddl = lambda: f"PRIMARY KEY ({', '.join(cols)})"


class UniqueConstraint:
    def __init__(self, *cols, name=None):
        self.ddl = lambda: f"{_named(name)}UNIQUE ({', '.join(cols)})"


class CheckConstraint:
    def __init__(self, text, name=None):
        self.ddl = lambda: f"{_named(name)}CHECK ({text})"


class ForeignKeyConstraint:
    def __init__(self, cols, refs, ondelete=None):
        table, ref_cols = refs[0].split(".")[0], [r.split(".")[1] for r in refs]
        tail = f" ON DELETE {ondelete}" if ondelete else ""
        self.ddl = lambda: (f"FOREIGN KEY({', '.join(cols)}) "
                            f"REFERENCES {table}({', '.join(ref_cols)}){tail}")


class Op:
    def __init__(self, db):
        self.db, self.log = db, []

    def _run(self, sql):
        self.log.append(sql)
        self.db.execute(sql)

    def create_table(self, name, *items):
        parts = [i.ddl() for i in items]
        self._run(f"CREATE TABLE {name} ({', '.join(parts)})")

    def drop_table(self, name):
        self._run(f"DROP TABLE {name}")

    def create_index(self, name, table, cols):
        self._run(f"CREATE INDEX {name} ON {table} ({', '.join(cols)})")

    def drop_index(self, name, table_name=None):
        self._run(f"DROP INDEX {name}")

    @contextmanager
    def batch_alter_table(self, table):
        op = self

        class Batch:
            def add_column(self, col):
                op._run(f"ALTER TABLE {table} ADD COLUMN {col.ddl()}")

            def drop_column(self, name):
                op._run(f"ALTER TABLE {table} DROP COLUMN {name}")
        yield Batch()


def load_migrations(db):
    op = Op(db)
    sa = types.ModuleType("sqlalchemy")
    sa.Integer, sa.Text, sa.Date, sa.DateTime = (lambda: T("Integer"), lambda: T("Text"),
                                                 lambda: T("Date"), lambda: T("DateTime"))
    sa.String = lambda length: T("String", length)
    sa.Column, sa.PrimaryKeyConstraint, sa.UniqueConstraint = (
        Column, PrimaryKeyConstraint, UniqueConstraint)
    sa.CheckConstraint, sa.ForeignKeyConstraint = CheckConstraint, ForeignKeyConstraint
    alembic = types.ModuleType("alembic")
    alembic.op = op
    sys.modules["sqlalchemy"], sys.modules["alembic"] = sa, alembic
    mods = {}
    for rev, path in (("0001", "alembic/versions/0001_initial_schema.py"),
                      ("0002", "alembic/versions/0002_add_submitted_at.py")):
        spec = importlib.util.spec_from_file_location("m" + rev, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mods[rev] = mod
    return op, mods


def structure(db):
    info = {}
    tables = [r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    for t in sorted(tables):
        cols = {}
        for _, name, typ, notnull, default, pk in db.execute(f"PRAGMA table_info({t})"):
            typ = typ.upper().replace("TIMESTAMP", "DATETIME")
            cols[name] = (typ, 0 if pk else notnull, (default or "").strip(), pk)
        fks = {(r[3], r[2], r[4], r[6]) for r in db.execute(f"PRAGMA foreign_key_list({t})")}
        idx, uniq = set(), set()
        for _, iname, unique, origin, _ in db.execute(f"PRAGMA index_list({t})"):
            cols_i = tuple(r[2] for r in db.execute(f"PRAGMA index_info({iname})"))
            if origin == "c":
                idx.add((iname, cols_i))
            elif origin == "u":
                uniq.add(cols_i)
        sql = db.execute("SELECT sql FROM sqlite_master WHERE name=?", (t,)).fetchone()[0]
        checks = set(re.findall(r"CONSTRAINT (\w+) CHECK", sql))
        info[t] = {"columns": cols, "fks": fks, "indexes": idx, "unique": uniq, "checks": checks}
    return info


def models_columns():
    tree = ast.parse(open("app/db/models.py", encoding="utf-8").read())
    result = {}
    for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
        table = next((s.value.value for s in cls.body if isinstance(s, ast.Assign)
                      and s.targets[0].id == "__tablename__"), None)
        if table:
            result[table] = {a.target.id for a in cls.body if isinstance(a, ast.AnnAssign)}
    return result


def main():
    ok = True

    def check(label, cond):
        nonlocal ok
        ok = ok and cond
        print(("OK   " if cond else "СБОЙ ") + label)

    mig = sqlite3.connect(":memory:")
    mig.execute("PRAGMA foreign_keys=ON")
    op, m = load_migrations(mig)
    m["0001"].upgrade()
    after1 = structure(mig)
    check("0001 upgrade: созданы 5 таблиц", sorted(after1) == [
        "assignments", "groups", "subjects", "submissions", "users"])
    check("0001 upgrade: submitted_at ещё нет",
          "submitted_at" not in after1["submissions"]["columns"])
    m["0002"].upgrade()
    head = structure(mig)
    check("0002 upgrade: колонка submitted_at добавлена",
          head["submissions"]["columns"].get("submitted_at", ("",))[0] == "DATETIME")

    ref = sqlite3.connect(":memory:")
    ddl = open("db/schema.sql", encoding="utf-8").read().replace(
        "INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
    ref.executescript(ddl)
    expected = structure(ref)
    for table in sorted(expected):
        for part in ("columns", "fks", "indexes", "unique", "checks"):
            same = expected[table][part] == head[table][part]
            if not same:
                print("   различие:", table, part, expected[table][part] ^ head[table][part]
                      if part != "columns" else (expected[table][part], head[table][part]))
            ok = ok and same
    print("OK   структура после миграций 0001+0002 совпадает с db/schema.sql "
          "(колонки, типы, NOT NULL, значения по умолчанию, внешние ключи, индексы, UNIQUE, CHECK)"
          if ok else "СБОЙ структура не совпадает со schema.sql")

    models = models_columns()
    same_models = all(set(head[t]["columns"]) == cols for t, cols in models.items()) \
        and set(models) == set(head)
    check("Таблицы и колонки в app/db/models.py совпадают с базой после миграций", same_models)

    mig.execute("INSERT INTO groups(name) VALUES ('БИС 31с')")
    try:
        mig.execute("INSERT INTO groups(name) VALUES ('БИС 31с')")
        check("UNIQUE(groups.name) работает", False)
    except sqlite3.IntegrityError:
        check("UNIQUE(groups.name) работает после миграций", True)
    try:
        mig.execute("INSERT INTO users(email,password_hash,full_name,role) "
                    "VALUES('a','h','n','admin')")
        check("CHECK(users.role) работает", False)
    except sqlite3.IntegrityError:
        check("CHECK(users.role) работает после миграций", True)

    m["0002"].downgrade()
    d1 = structure(mig)
    check("0002 downgrade: submitted_at удалена, остальное не тронуто",
          "submitted_at" not in d1["submissions"]["columns"] and set(d1) == set(after1))
    m["0001"].downgrade()
    check("0001 downgrade: все таблицы и индексы удалены", structure(mig) == {})
    m["0001"].upgrade()
    m["0002"].upgrade()
    check("Повторный upgrade после downgrade даёт ту же структуру", structure(mig) == head)
    print(f"\nВыполнено SQL-команд миграциями: {len(op.log)}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
