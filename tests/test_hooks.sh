#!/bin/bash
# G1-G3: run the real hooks in a scratch repo with a bare remote.
SRC="$(cd "$(dirname "$0")/../skills/vc-setup/assets/githooks" && pwd)"
T=$(mktemp -d); cd "$T"
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
git init -q --bare remote.git
git init -q -b main work && cd work
cp -r "$SRC" .githooks && git config core.hooksPath .githooks
git remote add origin "$T/remote.git"
pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "FAIL: $1"; }
expect_ok()   { if "${@:2}" >/dev/null 2>&1; then ok; else bad "should pass: $1"; fi; }
expect_fail() { if "${@:2}" >/dev/null 2>&1; then bad "should block: $1"; else ok; fi; }
commit() { git commit -q -m "$1"; }

echo 'LINT_CMD=""
TEST_CMD=""' > .githooks/config
echo a > a.txt; git add -A

# first commit on a fresh repo may land on main
expect_ok "first commit on empty repo" commit "chore: initial commit"
# G2: no commits on main afterwards
echo b >> a.txt; git add -A
expect_fail "commit on main" commit "fix: edit on main"
git switch -q -c feat/x

# G1: title table
echo c >> a.txt; git add -A
for t in "feat: add thing" "fix(cart): stop double discount" "feat(api)!: drop v1" "docs: update readme" "refactor(core/io): split reader" "chore(deps): bump x.y" "perf: speed up parse" "revert: undo thing" "test(auth): cover expiry" "ci: pin actions" "build: add makefile" "style: format files"; do
  expect_ok "valid title '$t'" git commit -q --allow-empty -m "$t"
done
for t in "update stuff" "fix" "WIP" "Fix: capital type" "feat:no space" "feat(): empty scope" "feat(Scope): caps scope" "feat: ends with period." "feat:  two spaces" "added feature" "feat add thing" "FEAT: x" "feat: $(printf 'x%.0s' $(seq 1 80))"; do
  expect_fail "bad title '$t'" git commit -q --allow-empty -m "$t"
done
expect_ok "git-made merge title" bash -c 'git commit -q --allow-empty -m "Merge branch x"'
expect_ok "git-made revert title" bash -c 'git commit -q --allow-empty -m "Revert \"feat: add thing\""'

# G2: secret scan
echo 'key=AKI''AABCDEFGHIJKLMNOP' > s.txt; git add s.txt
expect_fail "aws key" commit "chore: add config"
echo 'token=gh''p_abcdefghijklmnopqrstuvwxyz0123456789' > s.txt; git add s.txt
expect_fail "github token" commit "chore: add config"
echo 'k=s''k-ant-api03-abcdefghijklmnopqrstuvwx' > s.txt; git add s.txt
expect_fail "sk- key" commit "chore: add config"
printf -- '-----BEGIN RSA PRIV''ATE KEY-----\nxx\n' > s.txt; git add s.txt
expect_fail "private key" commit "chore: add config"
echo 'see disk-encryption-configuration-guide-for-linux' > s.txt; git add s.txt
expect_ok "no false positive on disk-encryption" commit "docs: add disk note"

# G2: lint
echo 'LINT_CMD="! test -f BAD"
TEST_CMD=""' > .githooks/config
touch BAD; git add BAD
expect_fail "lint failure blocks commit" commit "chore: add bad file"
git rm -q --cached BAD; rm BAD; echo z > z.txt; git add z.txt
expect_ok "lint passes" commit "chore: add z"

# run-checks: missing tool skips locally, fails in CI
echo 'LINT_CMD="nonexistent-tool-xyz --check"' > .githooks/config
expect_ok   "missing tool skipped locally" env -u CI sh .githooks/run-checks.sh lint
expect_fail "missing tool fails in CI"     env CI=true sh .githooks/run-checks.sh lint
expect_fail "unknown step"                 sh .githooks/run-checks.sh nope

# G3: pre-push
echo 'LINT_CMD=""
TEST_CMD=""' > .githooks/config
expect_ok   "push feature branch" git push -q -u origin feat/x
expect_fail "push HEAD to main"   git push -q origin HEAD:main
expect_fail "push main to main"   git push -q origin feat/x:refs/heads/main
echo 'TEST_CMD="false"' > .githooks/config
echo q > q.txt; git add q.txt; commit "chore: q"
expect_fail "failing tests block push" git push -q origin feat/x
echo 'TEST_CMD="true"' > .githooks/config
expect_ok   "passing tests allow push" git push -q origin feat/x

echo "hooks: $pass passed, $fail failed"; [ "$fail" -eq 0 ]
