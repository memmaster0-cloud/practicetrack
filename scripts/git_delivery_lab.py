"""Create an explicitly local Git exercise; no publishing or external identity."""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "delivery/git_lab"
EVIDENCE = ROOT / "delivery/evidence"


def main():
    if LAB.exists():
        raise SystemExit("Git lab already exists; retain it as evidence.")
    LAB.mkdir(parents=True)
    for folder in ("app", "tests", "alembic"):
        shutil.copytree(ROOT / folder, LAB / folder,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("README.md", "requirements.txt", "alembic.ini", ".gitignore"):
        shutil.copy2(ROOT / name, LAB / name)
    history = []

    def git(*args, success=True):
        command = ["git", "-c", "user.name=PracticeTrack automated exercise",
                   "-c", "user.email=local-exercise@example.invalid", *args]
        result = subprocess.run(command, cwd=LAB, capture_output=True,
                                encoding="utf-8", errors="replace")
        history.append("git " + " ".join(args) + "\n" + result.stdout + result.stderr)
        if success and result.returncode:
            raise RuntimeError(history[-1])
        return result

    git("init", "-b", "main")
    notes = LAB / "REVIEW_NOTES.md"
    notes.write_text("Review focus: pending\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "Import project snapshot for explicitly local exercise")
    git("switch", "-c", "docs/review-notes")
    notes.write_text("Review focus: role and resource ownership\n", encoding="utf-8")
    git("add", "REVIEW_NOTES.md")
    git("commit", "-m", "Record permission review focus")
    git("switch", "main")
    git("switch", "-c", "docs/test-notes")
    notes.write_text("Review focus: validation and status tests\n", encoding="utf-8")
    git("add", "REVIEW_NOTES.md")
    git("commit", "-m", "Record test review focus")
    git("switch", "main")
    git("merge", "--no-ff", "docs/review-notes", "-m", "Merge permission notes")
    conflict = git("merge", "--no-ff", "docs/test-notes", success=False)
    assert conflict.returncode != 0 and "<<<<<<<" in notes.read_text(encoding="utf-8")
    (EVIDENCE / "git_conflict.txt").write_text(notes.read_text(encoding="utf-8"),
                                               encoding="utf-8")
    notes.write_text("Review focus:\n- role and resource ownership\n"
                     "- validation and status tests\n", encoding="utf-8")
    git("add", "REVIEW_NOTES.md")
    git("commit", "-m", "Resolve real notes conflict preserving both review checks")
    graph = git("log", "--graph", "--oneline", "--all")
    (EVIDENCE / "git_graph.txt").write_text(graph.stdout, encoding="utf-8")
    git("bundle", "create", str(EVIDENCE / "git_lab.bundle"), "--all")
    (EVIDENCE / "git_commands.txt").write_text("\n".join(history), encoding="utf-8")
    print("Created local project history, two branches, real merge conflict and Git bundle.")


if __name__ == "__main__":
    main()
