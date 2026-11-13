#!/usr/bin/env python3
"""vc-setup installer.

Usage:
  install.py plan  [--target DIR]    show what would change (writes nothing)
  install.py apply [--target DIR]    do it

Rules:
  - Never overwrite a file you own. If a file differs, write <file>.vc-new and report CONFLICT.
  - Safe to run twice. A second run reports SKIP for everything.
  - .githooks/config belongs to you after the first run.
"""
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

GUARD_CMD = 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/vc-guard.py"'
GUARD_MATCHER = "Bash|Edit|Write|MultiEdit"
MARK_START, MARK_END = "<!-- vc:start -->", "<!-- vc:end -->"

NODE_STEPS = """      - uses: actions/setup-node@v4
        with:
          node-version: "lts/*"
      - run: if [ -f package-lock.json ]; then npm ci; else npm install; fi"""
PY_STEPS = """      - uses: actions/setup-python@v5
        with:
          python-version: "3.x"
      - run: |
          pip install ruff pytest
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          if [ -f pyproject.toml ]; then pip install -e . || true; fi"""
GO_STEPS = """      - uses: actions/setup-go@v5
        with:
          go-version-file: go.mod"""


def detect_stack(t: Path):
    if (t / "package.json").exists():
        pm = "pnpm" if (t / "pnpm-lock.yaml").exists() else "npm"
        return "node (%s)" % pm, f"{pm} run lint --if-present", f"{pm} run test --if-present", NODE_STEPS
    if any((t / f).exists() for f in ("pyproject.toml", "requirements.txt", "setup.py")):
        return "python", "ruff check .", "pytest -q", PY_STEPS
    if (t / "go.mod").exists():
        return "go", "go vet ./...", "go test ./...", GO_STEPS
    if (t / "Cargo.toml").exists():
        return "rust", "cargo clippy -- -D warnings", "cargo test", ""
    return "unknown", "", "", ""


def read(p: Path):
    return p.read_text() if p.exists() else None


def sh(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


class Plan:
    def __init__(self, target: Path):
        self.t = target
        self.items = []  # (kind, rel, note, writer)

    def add(self, kind, rel, note="", writer=None):
        self.items.append((kind, rel, note, writer))

    def file(self, rel, content: str, executable=False, user_owned=False):
        dest = self.t / rel
        cur = read(dest)

        def write(path=dest):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            if executable:
                path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        if cur is None:
            self.add("CREATE", rel, writer=write)
        elif cur == content:
            self.add("SKIP", rel, "already up to date")
        elif user_owned:
            self.add("SKIP", rel, "yours, not touched")
        else:
            alt = dest.with_name(dest.name + ".vc-new")
            self.add("CONFLICT", rel, f"differs. Will write {rel}.vc-new for you to compare", lambda: write(alt))


def build(target: Path) -> Plan:
    p = Plan(target)
    stack, lint, test, steps = detect_stack(target)
    p.add("INFO", "stack", f"{stack}  lint='{lint or '-'}'  test='{test or '-'}'")

    for name in ("commit-msg", "pre-commit", "pre-push", "run-checks.sh"):
        p.file(f".githooks/{name}", read(ASSETS / "githooks" / name), executable=True)
    p.file(".githooks/config", f'LINT_CMD="{lint}"\nTEST_CMD="{test}"\n', user_owned=True)

    p.file(".github/PULL_REQUEST_TEMPLATE.md", read(ASSETS / "github/PULL_REQUEST_TEMPLATE.md"))
    ci = read(ASSETS / "github/workflows/ci.yml").replace("{{SETUP_STEPS}}\n", (steps + "\n") if steps else "")
    p.file(".github/workflows/ci.yml", ci)
    p.file(".github/workflows/pr-title.yml", read(ASSETS / "github/workflows/pr-title.yml"))
    p.file(".github/workflows/release.yml", read(ASSETS / "github/workflows/release.yml"))
    p.file(".releaserc.json", read(ASSETS / "releaserc.json"))
    p.file(".claude/hooks/vc-guard.py", read(ASSETS / "claude/vc-guard.py"), executable=True)

    # .claude/settings.json: merge, keep everything the user has
    sp = target / ".claude/settings.json"
    try:
        cur = json.loads(read(sp) or "{}")
    except json.JSONDecodeError:
        p.add("CONFLICT", ".claude/settings.json", "is not valid JSON. Fix it by hand, then run again")
        cur = None
    if cur is not None:
        new = json.loads(json.dumps(cur))
        pre = new.setdefault("hooks", {}).setdefault("PreToolUse", [])
        has = any("vc-guard.py" in h.get("command", "") for e in pre for h in e.get("hooks", []))
        if not has:
            pre.append({"matcher": GUARD_MATCHER, "hooks": [{"type": "command", "command": GUARD_CMD}]})
            def w(sp=sp, new=new):
                sp.parent.mkdir(parents=True, exist_ok=True)
                sp.write_text(json.dumps(new, indent=2) + "\n")
            p.add("MERGE" if sp.exists() else "CREATE", ".claude/settings.json", "add the vc-guard hook", w)
        else:
            p.add("SKIP", ".claude/settings.json", "guard already registered")

    # AGENTS.md: own a marked block only
    block = f"{MARK_START}\n{read(ASSETS / 'agents-section.md').rstrip()}\n{MARK_END}\n"
    ap = target / "AGENTS.md"
    cur = read(ap)
    if cur is None:
        p.add("CREATE", "AGENTS.md", writer=lambda ap=ap, block=block: ap.write_text(block))
    elif MARK_START in cur:
        new = re.sub(re.escape(MARK_START) + r".*?" + re.escape(MARK_END) + r"\n?", lambda m: block, cur, flags=re.S)
        if new == cur:
            p.add("SKIP", "AGENTS.md", "rules block up to date")
        else:
            p.add("MERGE", "AGENTS.md", "refresh the vc rules block", lambda ap=ap, new=new: ap.write_text(new))
    else:
        p.add("MERGE", "AGENTS.md", "append the vc rules block", lambda ap=ap, cur=cur, block=block: ap.write_text(cur.rstrip("\n") + "\n\n" + block))

    cp = target / "CLAUDE.md"
    cur = read(cp)
    if cur is None:
        p.add("CREATE", "CLAUDE.md", "imports AGENTS.md", lambda cp=cp: cp.write_text("@AGENTS.md\n"))
    elif "@AGENTS.md" in cur:
        p.add("SKIP", "CLAUDE.md", "already imports AGENTS.md")
    else:
        p.add("MERGE", "CLAUDE.md", "add @AGENTS.md import", lambda cp=cp, cur=cur: cp.write_text(cur.rstrip("\n") + "\n\n@AGENTS.md\n"))

    gp = target / ".gitignore"
    cur = read(gp)
    if cur is not None and ".claude/worktrees" in cur:
        p.add("SKIP", ".gitignore", "worktrees already ignored")
    else:
        p.add("MERGE" if cur is not None else "CREATE", ".gitignore", "ignore .claude/worktrees",
              lambda gp=gp, cur=cur: gp.write_text((cur or "").rstrip("\n") + ("\n" if cur else "") + ".claude/worktrees\n"))

    if (target / ".git").exists():
        got = sh(["git", "config", "--local", "--get", "core.hooksPath"], target).stdout.strip()
        if got == ".githooks":
            p.add("SKIP", "git config core.hooksPath", "already .githooks")
        else:
            p.add("CONFIG", "git config core.hooksPath", "set to .githooks (each new clone must run this once)",
                  lambda target=target: sh(["git", "config", "--local", "core.hooksPath", ".githooks"], target))
    else:
        p.add("INFO", "git config core.hooksPath", "not a git repo here. Run git init first")
    return p


def main():
    args = sys.argv[1:]
    if not args or args[0] not in ("plan", "apply"):
        print(__doc__)
        sys.exit(2)
    target = Path(".").resolve()
    if "--target" in args:
        target = Path(args[args.index("--target") + 1]).resolve()
    plan = build(target)
    for kind, rel, note, writer in plan.items:
        print(f"{kind:9} {rel}" + (f"   {note}" if note else ""))
        if args[0] == "apply" and writer and kind != "INFO":
            writer()
    counts = {}
    for kind, *_ in plan.items:
        counts[kind] = counts.get(kind, 0) + 1
    print("--")
    print(("applied: " if args[0] == "apply" else "plan only, nothing written: ") +
          ", ".join(f"{v} {k}" for k, v in sorted(counts.items())))
    if any(k == "CONFLICT" for k, *_ in plan.items):
        print("CONFLICT files were not changed. Compare the .vc-new copies and merge by hand.")


if __name__ == "__main__":
    main()
