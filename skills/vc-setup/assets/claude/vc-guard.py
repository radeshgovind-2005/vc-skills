#!/usr/bin/env python3
"""vc-guard: Claude Code PreToolUse hook for the Bash tool.

Reads the hook JSON on stdin.
  deny  -> message on stderr, exit 2 (the command does not run)
  ask   -> JSON on stdout, exit 0 (the agent must get your approval)
  allow -> no output, exit 0

Policy:
  DENY  hook bypasses (--no-verify, commit -n, HUSKY=0, LEFTHOOK=0, GIT_CONFIG_* injection,
        core.hooksPath changes, git aliases), force push, any push to main/master, pushing all
        branches, removing or disabling .githooks, gh pr merge --admin
  ASK   merge, release, tag, reset --hard, clean -f, branch -D, discard-all, non-GET gh api,
        writes to .githooks / CI workflows / agent settings (Bash or Edit/Write tools),
        eval, pipe-to-shell, dynamic command names

Limit: this is a text guard. It stops lazy and accidental bypass. It cannot stop code that
builds a command at run time. CI and branch rules are the real gate.
"""
import json
import os
import re
import shlex
import subprocess
import sys

MAIN = {"main", "master"}
ENV_BYPASS = {
    "HUSKY": lambda v: v == "0",
    "HUSKY_SKIP_HOOKS": lambda v: True,
    "LEFTHOOK": lambda v: v.lower() in ("0", "false"),
    "LEFTHOOK_EXCLUDE": lambda v: True,
    "SKIP": lambda v: True,
    "PRE_COMMIT_ALLOW_NO_CONFIG": lambda v: True,
}
HOOKED = {"commit", "push", "merge", "cherry-pick", "rebase", "am", "revert"}
WRAPPERS = {"command", "time", "nohup", "sudo", "xargs", "exec", "nice", "builtin", "stdbuf", "timeout", "doas"}
INTERPRETERS = {"python", "python3", "node", "perl", "ruby", "php", "deno", "bun"}
PROTECTED_CORE = r"(\.githooks/|\.github/workflows/|\.claude/(hooks/|settings(\.local)?\.json)|\.releaserc|\.husky/|lefthook\.ya?ml)"
PROTECTED_PATH = re.compile(r"(^|[/\s'\"=>])" + PROTECTED_CORE)
PROTECTED_REDIRECT = re.compile(r">>?\s*['\"]?\S*" + PROTECTED_CORE)
WRITERS = {"cp", "mv", "rm", "sed", "tee", "ln", "install", "truncate", "chmod", "unlink", "dd", "patch", "perl", "awk"}
HARD_WRITERS = {"rm", "mv", "unlink", "chmod", "truncate"}
ASSIGN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def split_segments(cmd):
    """Split on && || ; | and newlines, but not inside quotes."""
    segs, cur, quote, i = [], [], None, 0
    while i < len(cmd):
        ch = cmd[i]
        if quote:
            cur.append(ch)
            if ch == "\\" and quote == '"' and i + 1 < len(cmd):
                cur.append(cmd[i + 1])
                i += 1
            elif ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            cur.append(ch)
        elif cmd.startswith("&&", i) or cmd.startswith("||", i):
            segs.append("".join(cur))
            cur = []
            i += 1
        elif ch in ";|\n":
            segs.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
        i += 1
    segs.append("".join(cur))
    out = []
    for s in segs:
        s = s.strip().lstrip("({").rstrip(")}").strip()
        if s:
            out.append(s)
    return out


def argv_of(seg):
    try:
        return shlex.split(seg, posix=True)
    except ValueError:
        return seg.split()


def current_branch(cwd):
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd or None, capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def short_flags(args, stop="mFCctS"):
    """Return the set of short-flag letters in args, ignoring letters after a value-taking flag."""
    letters = set()
    for a in args:
        if a.startswith("-") and not a.startswith("--") and len(a) > 1:
            for ch in a[1:]:
                letters.add(ch)
                if ch in stop:
                    break
    return letters


def dest_of(refspec):
    r = refspec.lstrip("+")
    if ":" in r:
        r = r.split(":", 1)[1]
    if r.startswith("refs/heads/"):
        r = r[len("refs/heads/"):]
    return r


def env_bypass(name, value):
    if name in ENV_BYPASS:
        return ENV_BYPASS[name](value)
    return name.startswith("GIT_CONFIG_KEY_") or name in ("GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS")


def check_git(argv, cwd):
    """argv starts at 'git'. Returns ('deny'|'ask'|None, reason)."""
    i, hooks_override, alias_override = 1, None, False
    while i < len(argv):
        a = argv[i]
        if a == "-c" and i + 1 < len(argv):
            kv = argv[i + 1]
            if kv.lower().startswith("core.hookspath"):
                hooks_override = kv
            if kv.lower().startswith("alias."):
                alias_override = True
            i += 2
        elif a in ("-C", "--git-dir", "--work-tree", "--namespace") and i + 1 < len(argv):
            i += 2
        elif a.startswith("-"):
            i += 1
        else:
            break
    if alias_override:
        return "deny", "git aliases can hide --no-verify. Aliases from -c are blocked."
    if hooks_override and not hooks_override.endswith("=.githooks"):
        return "deny", "Changing core.hooksPath would skip the repo hooks."
    if i >= len(argv):
        return None, ""
    sub, args = argv[i], argv[i + 1:]

    if sub in HOOKED and any(a.startswith("--no-ve") for a in args):
        return "deny", "--no-verify skips the hooks. Fix the failing check instead."
    if sub == "commit" and "n" in short_flags(args):
        return "deny", "commit -n is --no-verify. Fix the failing check instead."

    if sub == "update-ref" and any(dest_of(a) in MAIN or dest_of(a).startswith("main") for a in args if not a.startswith("-")):
        return "deny", "Moving main by hand skips the PR flow."
    if sub == "branch" and ("f" in short_flags(args) or "--force" in args) and any(a in MAIN for a in args):
        return "deny", "Moving main by hand skips the PR flow."

    if sub == "config":
        joined = " ".join(args)
        if re.search(r"(^|\s)alias\.", joined, re.I):
            return "deny", "git aliases can hide --no-verify. Do not set them from the agent."
        if re.search(r"core\.hookspath", joined, re.I):
            ok = re.search(r"core\.hookspath\s+\.githooks\s*$", joined, re.I)
            if not ok:
                return "deny", "Only 'git config core.hooksPath .githooks' is allowed."

    if sub == "push":
        opts = [a for a in args if a.startswith("-")]
        pos = [a for a in args if not a.startswith("-")]
        if "--all" in opts or "--mirror" in opts:
            return "deny", "Pushing all branches can touch main. Push one branch."
        if "--force" in opts or any(o.startswith("--force=") for o in opts) or "f" in short_flags(args):
            return "deny", "Force push is blocked. Use --force-with-lease on your own feature branch."
        if any(p.startswith("+") for p in pos[1:]):
            return "deny", "A '+' refspec is a force push. It is blocked."
        refspecs = pos[1:]
        if any(dest_of(p) in MAIN for p in refspecs):
            return "deny", "Direct push to main is blocked. Open a PR."
        if not refspecs and current_branch(cwd) in MAIN:
            return "deny", "You are on main. Direct push is blocked. Open a PR from a branch."
        if "--tags" in opts or "--delete" in opts or "-d" in args:
            return "ask", "This push changes or deletes tags or remote refs."
        return None, ""

    if sub == "reset" and "--hard" in args:
        return "ask", "git reset --hard discards work."
    if sub == "clean" and ("f" in short_flags(args) or "--force" in args):
        return "ask", "git clean -f deletes untracked files."
    if sub == "branch" and ("D" in short_flags(args) or "--force" in args):
        return "ask", "Force-deleting a branch can lose commits."
    if sub in ("checkout", "restore") and args and args[-1] in (".", "--", ":/"):
        return "ask", "This discards all local changes."
    if sub == "stash" and args and args[0] in ("drop", "clear"):
        return "ask", "Dropping a stash cannot be undone."
    if sub == "tag" and args and not any(a in ("-l", "--list", "-n") for a in args):
        return "ask", "Tags trigger releases. The release workflow creates them."
    return None, ""


def check_segment(seg, cwd, depth=0):
    argv = argv_of(seg)
    if not argv:
        return None, ""

    # env assignments before the command, and `env VAR=1 cmd`
    while argv and (ASSIGN.match(argv[0]) or argv[0] == "env"):
        m = ASSIGN.match(argv[0])
        if m and env_bypass(m.group(1), m.group(2)):
            return "deny", f"{m.group(1)} turns off or rewrites the hooks."
        argv = argv[1:]
    if not argv:
        return None, ""

    while argv and os.path.basename(argv[0]) in WRAPPERS:
        argv = argv[1:]
        while argv and (ASSIGN.match(argv[0]) or argv[0].startswith("-")):
            m = ASSIGN.match(argv[0])
            if m and env_bypass(m.group(1), m.group(2)):
                return "deny", f"{m.group(1)} turns off or rewrites the hooks."
            argv = argv[1:]
    if not argv:
        return None, ""

    head = os.path.basename(argv[0])

    if "$(" in argv[0] or "`" in argv[0] or argv[0].startswith("$"):
        return "ask", "The command name is built at run time, so the guard cannot read it."
    if head == "eval" and depth < 3:
        return check_command(" ".join(argv[1:]), cwd, depth + 1) if len(argv) > 1 else (None, "")
    if head in INTERPRETERS and re.search(r"no-verify|hookspath|HUSKY=0|LEFTHOOK=0|['\"]-n['\"]", seg, re.I):
        return "deny", "Inline code that skips hooks is blocked."

    if head in ("export", "set", "declare"):
        for tok in argv[1:]:
            m = ASSIGN.match(tok)
            if m and env_bypass(m.group(1), m.group(2)):
                return "deny", f"{m.group(1)} turns off or rewrites the hooks."
        return None, ""

    if head in ("sh", "bash", "zsh", "dash") and len(argv) == 1:
        return "ask", "Piping text into a shell hides the command from the guard."
    if head in ("sh", "bash", "zsh", "dash") and "-c" in argv and depth < 3:
        idx = argv.index("-c")
        if idx + 1 < len(argv):
            return check_command(argv[idx + 1], cwd, depth + 1)
        return None, ""

    if head in HARD_WRITERS and any(".githooks" in a for a in argv[1:]):
        return "deny", "Do not remove or disable .githooks."
    if PROTECTED_PATH.search(seg) and (head in WRITERS or PROTECTED_REDIRECT.search(seg)):
        return "ask", "This changes hooks, CI, or agent settings. Do not weaken a check to make a change pass."

    if head == "git":
        return check_git(argv, cwd)

    if head == "gh":
        rest = argv[1:]
        if rest[:2] == ["pr", "merge"]:
            if "--admin" in rest:
                return "deny", "gh pr merge --admin bypasses branch rules."
            return "ask", "Merging to main publishes a release."
        if rest[:1] == ["release"]:
            return "ask", "Releases are published by the release workflow."
        if rest[:2] == ["repo", "delete"]:
            return "deny", "Deleting a repo is not allowed from the agent."
        if rest[:1] == ["api"]:
            method = "GET"
            for j, t in enumerate(rest):
                if t in ("-X", "--method") and j + 1 < len(rest):
                    method = rest[j + 1].upper()
            if method != "GET":
                return "ask", f"gh api {method} changes GitHub state."
        return None, ""
    return None, ""


def check_command(cmd, cwd, depth=0):
    worst = (None, "")
    for seg in split_segments(cmd):
        verdict = check_segment(seg, cwd, depth)
        if verdict[0] == "deny":
            return verdict
        if verdict[0] == "ask" and worst[0] is None:
            worst = verdict
    return worst


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # fail open: a broken guard must not block all work
    tool = data.get("tool_name", "Bash")
    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        path = (data.get("tool_input") or {}).get("file_path", "")
        if PROTECTED_PATH.search(path):
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": "vc-guard: this file enforces checks. Do not weaken a check to make a change pass.",
            }}))
        sys.exit(0)
    if tool != "Bash":
        sys.exit(0)
    cmd = (data.get("tool_input") or {}).get("command", "")
    verdict, reason = check_command(cmd, data.get("cwd"))
    if verdict == "deny":
        sys.stderr.write(f"vc-guard blocked this command. {reason}\n")
        sys.exit(2)
    if verdict == "ask":
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": f"vc-guard: {reason}",
        }}))
    sys.exit(0)


if __name__ == "__main__":
    main()
