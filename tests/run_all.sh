#!/bin/bash
# Run every check. Needs: git, python3, pyyaml (pip install pyyaml).
cd "$(dirname "$0")" || exit 1
rc=0
for t in test_guard.py test_install.py test_skills_and_e2e.py; do echo "== $t"; python3 $t || rc=1; done
echo "== test_hooks.sh"; bash test_hooks.sh 2>/dev/null || rc=1
[ $rc -eq 0 ] && echo "ALL GREEN" || echo "FAILURES"
exit $rc
