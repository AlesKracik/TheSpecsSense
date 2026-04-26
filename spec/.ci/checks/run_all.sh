#!/usr/bin/env bash
# Run every CI check. Exits non-zero on first failure (set -e), then continues
# logically by collecting all results so the user sees the full picture.
#
# Usage:
#   bash spec/.ci/checks/run_all.sh

set -u
cd "$(dirname "$0")/../.."   # cd into spec/

PY="${PYTHON:-python3}"
fail=0

run() {
    local label="$1"; shift
    echo
    echo "=== $label ==="
    if "$@"; then
        :
    else
        fail=1
    fi
}

run "schema validation"           "$PY" .ci/checks/validate_schemas.py
run "referential integrity"       "$PY" .ci/checks/check_referential_integrity.py
run "_note convention"            "$PY" .ci/checks/check_notes.py
run "round-2 completeness"        "$PY" .ci/checks/check_round2_completeness.py

if command -v quint >/dev/null 2>&1; then
    if [ -f round-5/invariants.qnt ]; then
        run "quint typecheck"     quint typecheck round-5/invariants.qnt
        # `quint verify` is heavier; gate behind an env var to keep CI fast.
        if [ "${QUINT_VERIFY:-0}" = "1" ]; then
            run "quint verify (allInvariants)" quint verify --invariant=allInvariants round-5/invariants.qnt
        else
            echo
            echo "INFO — set QUINT_VERIFY=1 to run 'quint verify' on the invariants."
        fi
    fi
else
    echo
    echo "INFO — quint not installed; skipping formal-invariant checks. See https://quint-lang.org."
fi

echo
if [ $fail -eq 0 ]; then
    echo "ALL CHECKS PASSED."
else
    echo "ONE OR MORE CHECKS FAILED. See output above."
fi
exit $fail
