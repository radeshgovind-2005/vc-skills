import json, os, subprocess, sys, tempfile, hashlib, yaml
from pathlib import Path
INST = os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills"), "vc-setup/scripts/install.py")
env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
fails = 0; n = 0
def check(cond, msg):
    global fails, n; n += 1
    if not cond: fails += 1; print("FAIL:", msg)
def run(cmd, cwd, **kw): return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env, **kw)
def inst(mode, cwd): return run([sys.executable, INST, mode], cwd)
def tree(d): return {str(p.relative_to(d)): hashlib.md5(p.read_bytes()).hexdigest() for p in Path(d).rglob("*") if p.is_file() and ".git/" not in str(p)}

# --- node repo with pre-existing user files
d = tempfile.mkdtemp(); run(["git","init","-q","-b","main"], d)
Path(d,"package.json").write_text('{"scripts":{"lint":"echo lint","test":"echo test"}}')
Path(d,"AGENTS.md").write_text("# My rules\n\nKeep functions small.\n")
Path(d,"CLAUDE.md").write_text("# Claude notes\nUse tabs.\n")
Path(d,".gitignore").write_text("node_modules\n")
Path(d,".claude").mkdir(); Path(d,".claude/settings.json").write_text(json.dumps({"permissions":{"allow":["Bash(npm test)"]},"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"type":"command","command":"echo mine"}]}]}}))
before = tree(d)
r = inst("plan", d)
check(r.returncode == 0, "plan exits 0")
check(tree(d) == before, "plan writes nothing")
check("node (npm)" in r.stdout, "detects node")

r = inst("apply", d); check(r.returncode == 0, "apply exits 0: " + r.stderr)
s = json.loads(Path(d,".claude/settings.json").read_text())
check(s["permissions"]["allow"] == ["Bash(npm test)"], "keeps user permissions")
cmds = [h["command"] for e in s["hooks"]["PreToolUse"] for h in e["hooks"]]
check("echo mine" in cmds and any("vc-guard.py" in c for c in cmds), "keeps user hook, adds guard")
a = Path(d,"AGENTS.md").read_text()
check(a.startswith("# My rules") and "Keep functions small." in a and "<!-- vc:start -->" in a, "AGENTS.md keeps user text, adds block")
c = Path(d,"CLAUDE.md").read_text(); check("Use tabs." in c and "@AGENTS.md" in c, "CLAUDE.md keeps text, adds import")
check(Path(d,".gitignore").read_text().startswith("node_modules") and ".claude/worktrees" in Path(d,".gitignore").read_text(), ".gitignore appended")
check(run(["git","config","--get","core.hooksPath"], d).stdout.strip() == ".githooks", "hooksPath set")
for f in (".githooks/commit-msg",".githooks/pre-commit",".githooks/pre-push",".githooks/run-checks.sh",".claude/hooks/vc-guard.py"):
    check(os.access(Path(d,f), os.X_OK), f"{f} executable")
ci = yaml.safe_load(Path(d,".github/workflows/ci.yml").read_text())
check("{{" not in Path(d,".github/workflows/ci.yml").read_text(), "ci has no placeholder")
check(any("setup-node" in str(s) for s in ci["jobs"]["checks"]["steps"]), "ci has node setup")
check("npm run lint --if-present" in Path(d,".githooks/config").read_text(), "config has lint cmd")

# second run is a no-op
after1 = tree(d); r = inst("apply", d)
check(tree(d) == after1, "second apply changes nothing")
check(all(not l.startswith(("CREATE","MERGE","CONFLICT","CONFIG")) for l in r.stdout.splitlines()), "second apply all SKIP/INFO: " + r.stdout)

# user edits an owned file and a user-owned file: never overwritten
Path(d,".githooks/pre-commit").write_text("#!/bin/sh\n# my custom\nexit 0\n")
Path(d,".githooks/config").write_text('LINT_CMD="make lint"\nTEST_CMD="make test"\n')
Path(d,".github/PULL_REQUEST_TEMPLATE.md").write_text("my template\n")
mine = tree(d); r = inst("apply", d)
check(Path(d,".githooks/pre-commit").read_text().startswith("#!/bin/sh\n# my custom"), "custom pre-commit kept")
check(Path(d,".githooks/pre-commit.vc-new").exists(), "pre-commit.vc-new written")
check(Path(d,".github/PULL_REQUEST_TEMPLATE.md").read_text() == "my template\n", "custom PR template kept")
check('make lint' in Path(d,".githooks/config").read_text(), "config never touched")
check("CONFLICT" in r.stdout, "conflict reported")

# rules block refreshes without touching user text
a = Path(d,"AGENTS.md").read_text().replace("Never commit on `main`", "OLD LINE"); Path(d,"AGENTS.md").write_text(a)
inst("apply", d); a2 = Path(d,"AGENTS.md").read_text()
check("OLD LINE" not in a2 and "Keep functions small." in a2 and a2.count("<!-- vc:start -->") == 1, "block refreshed once, user text intact")

# --- invalid settings.json
d2 = tempfile.mkdtemp(); run(["git","init","-q","-b","main"], d2)
Path(d2,".claude").mkdir(); Path(d2,".claude/settings.json").write_text("{ not json")
r = inst("apply", d2); check(r.returncode == 0 and Path(d2,".claude/settings.json").read_text() == "{ not json", "bad settings.json left alone")
check("CONFLICT" in r.stdout and "not valid JSON" in r.stdout, "bad settings.json reported")

# --- not a git repo
d3 = tempfile.mkdtemp(); r = inst("apply", d3)
check(r.returncode == 0 and "git init" in r.stdout, "non-git dir handled")

# --- every stack renders valid YAML
for name, files in [("python",["pyproject.toml"]),("go",["go.mod"]),("rust",["Cargo.toml"]),("unknown",[]),("pnpm",["package.json","pnpm-lock.yaml"])]:
    x = tempfile.mkdtemp(); run(["git","init","-q","-b","main"], x)
    for f in files: Path(x,f).write_text("{}" if f.endswith(".json") else "")
    r = inst("apply", x); check(r.returncode == 0, f"{name} apply")
    y = yaml.safe_load(Path(x,".github/workflows/ci.yml").read_text())
    steps = y["jobs"]["checks"]["steps"]
    check(steps[0]["uses"].startswith("actions/checkout") and "run-checks" in steps[-1]["run"], f"{name} ci steps ok")
    check("{{" not in Path(x,".github/workflows/ci.yml").read_text(), f"{name} no placeholder")
    cfg = Path(x,".githooks/config").read_text()
    print(f"  {name:8} -> {cfg.strip().replace(chr(10),'  ')}")
print(f"{n} checks, {fails} failed"); sys.exit(1 if fails else 0)
