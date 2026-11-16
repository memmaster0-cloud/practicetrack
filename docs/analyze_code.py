"""Статический анализ app/: проверки по образцу Pylint, цикломатическая сложность, дублирование.

Pylint в среде подготовки отчёта не установлен, поэтому часть его проверок реализована здесь:
C0114/C0115/C0116 (нет docstring), R0913 (много аргументов), R0912 (много ветвлений),
R0915 (много операторов), R0801 (дублирование кода, приближённо), W0105-подобные не проверяются.
"""
import ast
import glob
import os
import sys
from collections import defaultdict

MAX_ARGS, MAX_BRANCHES, MAX_STATEMENTS, MAX_COMPLEXITY = 5, 12, 50, 10
DUP_WINDOW, DUP_MIN_CHARS = 4, 140
BRANCH_NODES = (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.IfExp, ast.comprehension)


def complexity(fn):
    score = 1
    for n in ast.walk(fn):
        if isinstance(n, BRANCH_NODES):
            score += 1
        elif isinstance(n, ast.BoolOp):
            score += len(n.values) - 1
    return score


def statements(fn):
    return sum(isinstance(n, ast.stmt) for n in ast.walk(fn)) - 1


def class_methods(files):
    """Имя класса -> множество имён методов (для определения переопределённых методов)."""
    result = {}
    for f in files:
        for node in ast.walk(ast.parse(open(f, encoding="utf-8").read())):
            if isinstance(node, ast.ClassDef):
                result[node.name] = {m.name for m in node.body if isinstance(m, ast.FunctionDef)}
    return result


def overridden(cls, name, methods):
    """True, если метод name есть у одного из базовых классов проекта."""
    stack = [b.id for b in cls.bases if isinstance(b, ast.Name)]
    while stack:
        base = stack.pop()
        if name in methods.get(base, ()):
            return True
    return False


def analyze(root="app"):
    base = os.path.dirname(os.path.abspath(root))
    files = sorted(glob.glob(f"{root}/**/*.py", recursive=True))
    methods = class_methods(files)
    messages, funcs, total_lines = [], [], 0
    for f in files:
        src = open(f, encoding="utf-8").read()
        total_lines += len([line for line in src.split("\n") if line.strip()])
        tree = ast.parse(src)
        if f.endswith("__init__.py"):
            continue
        if not ast.get_docstring(tree):
            messages.append((f, 1, "C0114", "Missing module docstring"))
        owner = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for member in node.body:
                    if isinstance(member, ast.FunctionDef):
                        owner[id(member)] = node
        for node in ast.walk(tree):
            if (isinstance(node, ast.ClassDef) and not node.name.startswith("_")
                    and not ast.get_docstring(node)):
                messages.append((f, node.lineno, "C0115",
                                 f"Missing class docstring: {node.name}"))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                cls = owner.get(id(node))
                is_override = cls is not None and overridden(cls, node.name, methods)
                length = node.end_lineno - node.lineno + 1
                cx, st = complexity(node), statements(node)
                nargs = len(node.args.args) + len(node.args.kwonlyargs)
                funcs.append((f, node.name, node.lineno, length, cx))
                if (not node.name.startswith("_") and not is_override
                        and not ast.get_docstring(node)):
                    messages.append((f, node.lineno, "C0116",
                                     f"Missing function docstring: {node.name}"))
                if nargs > MAX_ARGS:
                    messages.append((f, node.lineno, "R0913",
                                     f"Too many arguments ({nargs}/{MAX_ARGS}): {node.name}"))
                if cx > MAX_BRANCHES:
                    messages.append((f, node.lineno, "R0912",
                                     f"Too many branches ({cx}): {node.name}"))
                if st > MAX_STATEMENTS:
                    messages.append((f, node.lineno, "R0915",
                                     f"Too many statements ({st}): {node.name}"))
    messages += duplicates(files)
    messages = [(os.path.relpath(os.path.abspath(f), base), ln, code,
                 text.replace(base + os.sep, ""))
                for f, ln, code, text in messages]
    return files, total_lines, messages, funcs


def duplicates(files):
    """R0801 (приближённо): одинаковые подряд идущие 4 строки в разных местах."""
    windows = defaultdict(list)
    for f in files:
        lines = [(i + 1, l.strip()) for i, l in enumerate(open(f, encoding="utf-8"))
                 if l.strip() and not l.strip().startswith(("#", '"""', "import ", "from "))]
        for k in range(len(lines) - DUP_WINDOW + 1):
            chunk = lines[k:k + DUP_WINDOW]
            text = "\n".join(c[1] for c in chunk)
            if len(text) >= DUP_MIN_CHARS:
                windows[text].append((f, chunk[0][0]))
    groups, seen = [], set()
    for text, places in windows.items():
        uniq = []
        for f, ln in places:
            if not any(f == f2 and abs(ln - l2) < DUP_WINDOW + 2 for f2, l2 in uniq):
                uniq.append((f, ln))
        if len(uniq) >= 2 and not any(p in seen for p in uniq):
            seen.update(uniq)
            groups.append(uniq)
    return [(g[0][0], g[0][1], "R0801", "Similar lines in %d places: %s" % (
        len(g), ", ".join(f"{f}:{ln}" for f, ln in g))) for g in groups]


def main():
    files, lines, messages, funcs = analyze(sys.argv[1] if len(sys.argv) > 1 else "app")
    for f, ln, code, text in sorted(messages):
        print(f"{f}:{ln}: {code}: {text}")
    by_code = defaultdict(int)
    for m in messages:
        by_code[m[2]] += 1
    print()
    print("Файлов:", len(files), "| непустых строк:", lines, "| функций и методов:", len(funcs))
    summary = ", ".join(f"{k}={v}" for k, v in sorted(by_code.items()))
    print("Замечаний всего:", len(messages), "|", summary)
    longest = max(funcs, key=lambda x: x[3])
    most_complex = max(funcs, key=lambda x: x[4])
    print(f"Самая длинная функция: {longest[1]} ({longest[3]} строк, {longest[0]})")
    print(f"Наибольшая цикломатическая сложность: {most_complex[4]} ({most_complex[1]})")
    print(f"Средняя сложность: {sum(f[4] for f in funcs) / len(funcs):.2f}")
    over = sum(f[4] > MAX_COMPLEXITY for f in funcs)
    print("Функций со сложностью выше %d: %d" % (MAX_COMPLEXITY, over))


if __name__ == "__main__":
    sys.exit(main())
