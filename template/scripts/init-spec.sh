#!/usr/bin/env bash
# Initialize a Specs Sense spec/ directory in a fresh project.
#
# Run this from the project root, AFTER copying spec/, agents/, and scripts/
# into place from the template.
#
# What it does:
#   1. Verifies the expected layout is present.
#   2. Installs the Python dependencies for the CI checks.
#   3. Wires the CI checks into a pre-commit hook (if .git exists).
#   4. Tags the initial iteration as `pass-0`.
#
# What it does NOT do:
#   - Fill scope.md or glossary.md. Those are human-only inputs.
#   - Run any agent. The orchestrator is your job.

set -euo pipefail

ROOT="$(pwd)"

echo "Initializing Specs Sense in $ROOT"
echo

# 1. Layout sanity check
required=(
    "spec/scope.md"
    "spec/glossary.md"
    "spec/round-1/entities.json"
    "spec/round-5/invariants.qnt"
    "spec/.ci/schemas/_common.schema.json"
    "spec/.ci/checks/run_all.sh"
    "agents/_README.md"
    "skills/_README.md"
    "skills/fetch-evidence.md"
    "orchestrator/orchestrator.py"
    "orchestrator/config.example.yaml"
    "orchestrator/requirements.txt"
)
missing=()
for f in "${required[@]}"; do
    if [ ! -f "$ROOT/$f" ]; then
        missing+=("$f")
    fi
done
if [ ${#missing[@]} -gt 0 ]; then
    echo "ERROR: missing required template files:"
    printf '  %s\n' "${missing[@]}"
    echo
    echo "Copy the template/ directory into this project before running init."
    exit 1
fi
echo "[1/4] Layout: OK"

# 2. Python deps for CI checks AND the orchestrator
if command -v python3 >/dev/null 2>&1; then
    echo "[2/4] Installing CI + orchestrator dependencies via pip..."
    python3 -m pip install --quiet -r spec/.ci/checks/requirements.txt
    python3 -m pip install --quiet -r orchestrator/requirements.txt
    echo "      Done."
else
    echo "[2/4] WARN: python3 not found. Install it and run:"
    echo "      pip install -r spec/.ci/checks/requirements.txt"
    echo "      pip install -r orchestrator/requirements.txt"
fi

# 3. Pre-commit hook
if [ -d "$ROOT/.git" ]; then
    HOOK="$ROOT/.git/hooks/pre-commit"
    if [ -f "$HOOK" ]; then
        echo "[3/4] Pre-commit hook already exists at $HOOK; not overwriting."
        echo "      To wire CI in manually, append:"
        echo "        bash spec/.ci/checks/run_all.sh"
    else
        cat > "$HOOK" <<'EOF'
#!/usr/bin/env bash
# Specs Sense — run CI checks before every commit.
exec bash spec/.ci/checks/run_all.sh
EOF
        chmod +x "$HOOK"
        echo "[3/4] Wrote pre-commit hook to $HOOK"
    fi
else
    echo "[3/4] No .git directory; skipping hook install. Run 'git init' first if desired."
fi

# 4. Tag pass-0
if [ -d "$ROOT/.git" ]; then
    if git -C "$ROOT" rev-parse --verify HEAD >/dev/null 2>&1; then
        if git -C "$ROOT" rev-parse pass-0 >/dev/null 2>&1; then
            echo "[4/4] Tag 'pass-0' already exists; not overwriting."
        else
            git -C "$ROOT" tag pass-0 HEAD
            echo "[4/4] Tagged HEAD as 'pass-0'."
        fi
    else
        echo "[4/4] No commits yet; skipping pass-0 tag. Tag manually after first commit:"
        echo "      git tag pass-0"
    fi
else
    echo "[4/4] No .git directory; skipping pass-0 tag."
fi

echo
echo "Done. Next steps:"
echo "  1. Edit spec/scope.md (the most important input). Set Mode and (for brownfield/mixed) Evidence sources."
echo "  2. Edit spec/glossary.md (or leave empty and let agents propose terms)."
echo "  3. Configure the orchestrator:"
echo "       cp orchestrator/config.example.yaml orchestrator/config.yaml"
echo "       \$EDITOR orchestrator/config.yaml"
echo "       export ANTHROPIC_API_KEY=sk-ant-..."
echo "  4. Run the orchestrator:"
echo "       python3 orchestrator/orchestrator.py once    # one detect→dispatch pass"
echo "       python3 orchestrator/orchestrator.py run     # polling loop"
echo "  5. After each iteration converges, tag the new state:  git tag pass-N"
