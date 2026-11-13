import json, os, re, subprocess, sys, tempfile, yaml
from pathlib import Path
SK = Path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills")).resolve(); GUARD = SK/"vc-setup/assets/claude/vc-guard.py"
env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
fails = n = 0
def check(c, m):
    global fails, n; n += 1
    if not c: fails += 1; print("FAIL:", m)
def sh(cmd, cwd, **kw): return subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, env=env, **kw)
def guard(cmd, cwd):
    p = subprocess.run([sys.executable, str(GUARD)], input=json.dumps({"tool_name":"Bash","tool_input":{"command":cmd},"cwd":str(cwd)}), capture_output=True, text=True)
    return "deny" if p.returncode == 2 else ("ask" if p.stdout.strip() else "allow")

# ---------- G6: skill validity
for d in sorted(SK.iterdir()):
    f = d/"SKILL.md"
    if not f.exists(): continue
    txt = f.read_text(); m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    check(m, f"{d.name}: has frontmatter")
    fm = yaml.safe_load(m.group(1))
    check(fm["name"] == d.name, f"{d.name}: name matches dir")
    check(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", fm["name"]) and len(fm["name"]) <= 64, f"{d.name}: name format")
    check(40 <= len(fm["description"]) <= 1024, f"{d.name}: description length {len(fm['description'])}")
    check(len(txt.splitlines()) < 500, f"{d.name}: under 500 lines")
    check("TODO" not in txt and "{{" not in txt, f"{d.name}: no placeholders")
    for rel in re.findall(r"(?:scripts|references|assets)/[\w./-]+\.\w+", txt):
        check((d/rel).exists() or (SK/"vc"/rel).exists() or (SK/"vc-setup"/rel).exists(), f"{d.name}: referenced file exists: {rel}")
    for s in (d/"scripts").glob("*") if (d/"scripts").exists() else []:
        check(os.access(s, os.X_OK), f"{d.name}: {s.name} executable")
check(len(list(SK.glob("*/SKILL.md"))) == 5, "five skills present")

# ---------- state.sh in several states
STATE = str(SK/"vc/scripts/state.sh")
def state(cwd): return dict(l.split("=",1) for l in sh(f"sh {STATE}", cwd).stdout.splitlines() if "=" in l and not l.startswith(("---"," ","?","M ","A ")))
x = tempfile.mkdtemp(); check(state(x).get("repo") == "false", "state: not a repo")
d = Path(tempfile.mkdtemp()); sh("git init -q -b main", d)
s = state(d); check(s["has_commits"] == "false" and s["on_default"] == "false" or s["branch"] == "main", "state: empty repo")
(d/"package.json").write_text('{"scripts":{"lint":"echo ok","test":"echo ok"}}'); (d/"a.txt").write_text("a")
sh("git add -A && git -c core.hooksPath=/dev/null commit -q -m 'chore: init'", d)
(d/"a.txt").write_text("b"); (d/"new.txt").write_text("n")
s = state(d); check(s["on_default"] == "true" and s["unstaged"] == "1" and s["untracked"] == "1", f"state: main dirty {s}")
check(s["hooks_installed"] == "false" and any(k=="missing" for k in s) or "missing" in sh(f"sh {STATE}", d).stdout, "state: reports missing setup")
check(s["gh"] == "not_installed" or s.get("gh_auth") in ("true","false"), "state: gh handled")

# ---------- G7: full router flow in a fresh repo with a bare remote
base = Path(tempfile.mkdtemp()); sh("git init -q --bare remote.git", base)
w = base/"work"; sh("git init -q -b main work", base)
(w/"package.json").write_text('{"scripts":{"lint":"echo lint-ok","test":"echo test-ok"}}'); (w/"app.js").write_text("v1\n")
sh(f"git remote add origin {base}/remote.git", w)
r = sh(f"python3 {SK}/vc-setup/scripts/install.py apply", w); check(r.returncode == 0, "e2e: install applied")
sh("git add -A", w); r = sh("git commit -q -m 'chore: add vc setup'", w); check(r.returncode == 0, f"e2e: first commit on empty repo ok {r.stderr}")
sh("git push -q origin main", w, check=False)  # bootstrap push blocked by hook? (expected)
sh(f"git push -q --no-verify origin main", w)   # test scaffolding only: seed the remote, not via the guard
# agent flow, each command first passes through the guard
(w/"app.js").write_text("v2\n"); (w/"README.md").write_text("hi\n")
flow = [("git switch -c fix/app-version", "allow"), ("git add app.js", "allow"),
        ("git commit -m 'fix(app): bump version string'", "allow"), ("git add README.md", "allow"),
        ("git commit -m 'docs(readme): add readme'", "allow"), ("git push -u origin HEAD", "allow"),
        ("gh pr create --title 'fix(app): bump version string' --body-file /tmp/b.md", "allow"),
        ("gh pr checks --watch --interval 30", "allow"), ("gh pr merge 1 --squash --delete-branch", "allow"),
        ("git switch main && git pull --ff-only", "allow"), ("git branch -d fix/app-version", "allow"), ("git fetch --tags", "allow")]
for cmd, want in flow: check(guard(cmd, w) == want, f"e2e guard {want}: {cmd}")
# run the real commands
r = sh("git switch -c fix/app-version", w); check(r.returncode == 0, "e2e: branch")
r = sh("git add app.js && git commit -q -m 'update stuff'", w); check(r.returncode != 0, "e2e: bad title blocked by real hook")
r = sh("git commit -q -m 'fix(app): bump version string'", w); check(r.returncode == 0, "e2e: good title passes")
r = sh("git add README.md && git commit -q -m 'docs(readme): add readme'", w); check(r.returncode == 0, "e2e: second commit")
r = sh("git push -q -u origin HEAD", w); check(r.returncode == 0, f"e2e: feature push ok {r.stderr[-200:]}")
r = sh("git push -q origin HEAD:main", w); check(r.returncode != 0, "e2e: push to main blocked by real hook")
check(sh("git log --format=%s -3", w).stdout.splitlines()[0] == "docs(readme): add readme", "e2e: history reads clean")
# PR template renders the title rules; workflows parse
for f in ("ci","pr-title","release"): yaml.safe_load((w/f".github/workflows/{f}.yml").read_text())
# state script on the feature branch
s = state(w); check(s["branch"] == "fix/app-version" and s["commits_ahead_of_default"] == "2" and s["hooks_installed"] == "true", f"e2e: state on feature {s}")
check("missing=" not in sh(f"sh {STATE}", w).stdout, "e2e: nothing missing after setup")
print(f"{n} checks, {fails} failed"); sys.exit(1 if fails else 0)
