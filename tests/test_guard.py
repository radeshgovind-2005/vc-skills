import json, subprocess, sys, os, tempfile
GUARD = os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills"), "vc-setup/assets/claude/vc-guard.py")

# make a scratch repo on a feature branch and one on main, for bare-push checks
def mkrepo(branch):
    d = tempfile.mkdtemp()
    subprocess.run(f"git init -q -b main {d} && cd {d} && git -c user.email=a@b -c user.name=t commit -q --allow-empty -m 'chore: init'", shell=True, check=True)
    if branch != "main":
        subprocess.run(f"cd {d} && git switch -q -c {branch}", shell=True, check=True)
    return d
ON_MAIN, ON_FEAT = mkrepo("main"), mkrepo("feat/x")

def run(cmd, cwd):
    p = subprocess.run([sys.executable, GUARD], input=json.dumps({"tool_name":"Bash","tool_input":{"command":cmd},"cwd":cwd}),
                       capture_output=True, text=True)
    if p.returncode == 2: return "deny"
    if p.stdout.strip():
        return json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"]
    return "allow"

CASES = [
 # --- must DENY
 ("git commit --no-verify -m 'x'", "deny"),
 ("git commit -n -m 'x'", "deny"),
 ("git commit -anm 'x'", "deny"),
 ("git commit -m 'x' --no-ver", "deny"),
 ("git push --no-verify", "deny"),
 ("git -C . commit --no-verify -m x", "deny"),
 ("HUSKY=0 git commit -m 'fix: a'", "deny"),
 ("LEFTHOOK=0 git commit -m 'fix: a'", "deny"),
 ("LEFTHOOK_EXCLUDE=lint git commit -m 'fix: a'", "deny"),
 ("env HUSKY=0 git commit -m 'fix: a'", "deny"),
 ("export HUSKY=0 && git commit -m 'fix: a'", "deny"),
 ("SKIP=lint git commit -m 'fix: a'", "deny"),
 ("git -c core.hooksPath=/dev/null commit -m 'fix: a'", "deny"),
 ("git config core.hooksPath /dev/null", "deny"),
 ("git config --local core.hooksPath ''", "deny"),
 ("bash -c 'git commit --no-verify -m x'", "deny"),
 ("sh -c \"HUSKY=0 git commit -m x\"", "deny"),
 ("echo hi; git commit --no-verify -m x", "deny"),
 ("git add . && git commit -n -m x", "deny"),
 ("git push --force origin feat/x", "deny"),
 ("git push -f origin feat/x", "deny"),
 ("git push -fu origin feat/x", "deny"),
 ("git push origin +feat/x", "deny"),
 ("git push origin main", "deny"),
 ("git push origin HEAD:main", "deny"),
 ("git push origin feat/x:refs/heads/main", "deny"),
 ("git push origin :main", "deny"),
 ("git push origin --delete main", "deny"),
 ("git push --all", "deny"),
 ("git push --mirror", "deny"),
 ("rm -rf .githooks", "deny"),
 ("chmod -x .githooks/pre-commit", "deny"),
 ("gh pr merge 12 --squash --admin", "deny"),
 ("gh repo delete foo/bar --yes", "deny"),
 # --- must ASK
 ("gh pr merge 12 --squash --delete-branch", "ask"),
 ("gh release create v1.0.0", "ask"),
 ("git tag v1.2.3", "ask"),
 ("git reset --hard HEAD~1", "ask"),
 ("git clean -fd", "ask"),
 ("git branch -D old", "ask"),
 ("git checkout .", "ask"),
 ("git restore .", "ask"),
 ("git stash drop", "ask"),
 ("git push --tags", "ask"),
 ("gh api -X POST repos/{owner}/{repo}/rulesets --input r.json", "ask"),
 ("gh api -X PATCH repos/{owner}/{repo} -f a=b", "ask"),
 # --- must ALLOW (normal work)
 ("git status", "allow"),
 ("git diff main...HEAD --stat", "allow"),
 ("git log --oneline -20", "allow"),
 ("git switch -c feat/new-thing", "allow"),
 ("git add src/a.py src/b.py", "allow"),
 ("git commit -m 'fix(cart): stop double discount on reuse'", "allow"),
 ("git commit -m 'docs: explain the -n flag and --no-verify'", "allow"),
 ("git commit -m 'fix: handle HUSKY=0 in docs'", "allow"),
 ("git commit -am 'fix: a'", "allow"),
 ("git commit -m 'fix: a' -m 'body line'", "allow"),
 ("git push -u origin feat/x", "allow"),
 ("git push origin HEAD", "allow"),
 ("git push origin feat/main-menu", "allow"),
 ("git push --force-with-lease origin feat/x", "allow"),
 ("git push origin feat/x:feat/y", "allow"),
 ("git config core.hooksPath .githooks", "allow"),
 ("git config user.name foo", "allow"),
 ("git tag --list", "allow"),
 ("git tag -l 'v*'", "allow"),
 ("git branch -d merged-one", "allow"),
 ("git branch --show-current", "allow"),
 ("git fetch --tags", "allow"),
 ("git pull --ff-only", "allow"),
 ("git rebase origin/main", "allow"),
 ("git stash push -m wip", "allow"),
 ("git worktree add ../wt -b feat/y", "allow"),
 ("gh pr create --title 'feat: x' --body-file b.md", "allow"),
 ("gh pr checks --watch", "allow"),
 ("gh pr view --json state", "allow"),
 ("gh api repos/{owner}/{repo}/rulesets", "allow"),
 ("npm test && git status", "allow"),
 ("ls .githooks", "allow"),
 ("cat .githooks/commit-msg", "allow"),
 ("echo 'git commit --no-verify' > notes.txt", "allow"),
 ("command git commit --no-verify -m x", "deny"),
 ("time git commit -n -m x", "deny"),
 ("sudo git commit -n -m x", "deny"),
 ("xargs git commit -n -m x", "deny"),
 ("GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/dev/null git commit -m 'fix: a'", "deny"),
 ("(git commit -n -m x)", "deny"),
 ("{ git commit -n -m x; }", "deny"),
 ("git -c alias.c='commit -n' c -m x", "deny"),
 ("git config alias.c 'commit -n'", "deny"),
 ("python3 -c \"import subprocess;subprocess.run(['git','commit','-n'])\"", "deny"),
 ("eval 'git commit -n -m x'", "deny"),
 ("echo 'git commit -n -m x' | sh", "ask"),
 ("$(echo git) commit -n -m x", "ask"),
 ("git update-ref refs/heads/main HEAD", "deny"),
 ("git branch -f main HEAD~1", "deny"),
 ("cp /dev/null .githooks/pre-commit", "ask"),
 ("echo '' > .githooks/commit-msg", "ask"),
 ("sed -i 's/exit 1/exit 0/' .githooks/pre-commit", "ask"),
 ("tee .github/workflows/ci.yml", "ask"),
 ("python3 vc-setup/scripts/install.py plan", "allow"),
 ("git add .githooks/ .github/", "allow"),
 ("git commit -m 'ci: update .github/workflows/ci.yml'", "allow"),
 ("grep -r lint .github/workflows", "allow"),
]

# bare pushes depend on branch
BARE = [("git push", ON_MAIN, "deny"), ("git push", ON_FEAT, "allow"), ("git push origin", ON_MAIN, "deny"), ("git push origin", ON_FEAT, "allow")]

def run_tool(tool, path):
    p = subprocess.run([sys.executable, GUARD], input=json.dumps({"tool_name":tool,"tool_input":{"file_path":path},"cwd":ON_FEAT}), capture_output=True, text=True)
    return json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"] if p.stdout.strip() else "allow"
TOOLS = [("Edit","/r/.githooks/pre-commit","ask"),("Write","/r/.github/workflows/ci.yml","ask"),("Edit","/r/.claude/settings.json","ask"),
         ("Edit","/r/.claude/hooks/vc-guard.py","ask"),("MultiEdit","/r/.releaserc.json","ask"),("Edit","/r/src/app.py","allow"),("Write","/r/README.md","allow"),("Edit","/r/.githooks/config","ask")]
fails = 0
for tool, path, want in TOOLS:
    got = run_tool(tool, path)
    if got != want: fails += 1; print(f"FAIL want={want} got={got} {tool} {path}")
for cmd, want in CASES:
    got = run(cmd, ON_FEAT)
    if got != want:
        fails += 1; print(f"FAIL want={want:5} got={got:5}  {cmd}")
for cmd, cwd, want in BARE:
    got = run(cmd, cwd)
    if got != want:
        fails += 1; print(f"FAIL want={want:5} got={got:5}  {cmd}  (cwd branch)")
# non-Bash tool and broken input must fail open
p = subprocess.run([sys.executable, GUARD], input="not json", capture_output=True, text=True)
if p.returncode != 0: fails += 1; print("FAIL: bad JSON must fail open")
print(f"{len(CASES)+len(BARE)+len(TOOLS)+1} checks, {fails} failed")
sys.exit(1 if fails else 0)
