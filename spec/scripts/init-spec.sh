#!/usr/bin/env bash
# Initialize a Specs Sense spec/ subtree in a fresh project.
#
# Run this from the project root, AFTER copying the spec/ subtree from the
# template into your project (i.e., your project root contains spec/).
#
# Usage from project root:
#   bash spec/scripts/init-spec.sh
#
# What it does:
#   1. Verifies the expected layout is present.
#   2. Installs the Python dependencies for the CI checks.
#   3. Wires the CI checks into a pre-commit hook (if .git exists).
#   4. Tags the initial iteration as `pass-0`.
#   5. Bootstraps spec/passes/pass-1.md from the template, stamping metadata.
#
# What it does NOT do:
#   - Fill scope.md or glossary.md. Those are human-only inputs.
#   - Run any agent. spec/AGENTS.md drives the LLM interactively — open the
#     repo in your LLM driver of choice (Cursor, Claude Code, Codex, Aider,
#     etc.) and let it read spec/AGENTS.md to start.

set -euo pipefail

ROOT="$(pwd)"

echo "Initializing Specs Sense in $ROOT"
echo

# 1. Layout sanity check — every required path is under spec/
required=(
    "spec/AGENTS.md"
    "spec/scope.md"
    "spec/glossary.md"
    "spec/round-1/entities.json"
    "spec/round-5/invariants.qnt"
    "spec/.ci/schemas/_common.schema.json"
    "spec/.ci/checks/run_all.sh"
    "spec/agents/_README.md"
    "spec/skills/_README.md"
    "spec/skills/fetch-evidence.md"
    "spec/passes/_README.md"
    "spec/passes/pass-template.md"
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
    echo "Copy the spec/ subtree into this project before running init."
    exit 1
fi
echo "[1/5] Layout: OK"

# 2. Python deps for CI checks
if command -v python3 >/dev/null 2>&1; then
    echo "[2/5] Installing CI dependencies via pip..."
    python3 -m pip install --quiet -r spec/.ci/checks/requirements.txt
    echo "      Done."
else
    echo "[2/5] WARN: python3 not found. Install it and run:"
    echo "      pip install -r spec/.ci/checks/requirements.txt"
fi

# 3. Pre-commit hook
if [ -d "$ROOT/.git" ]; then
    HOOK="$ROOT/.git/hooks/pre-commit"
    if [ -f "$HOOK" ]; then
        echo "[3/5] Pre-commit hook already exists at $HOOK; not overwriting."
        echo "      To wire CI in manually, append:"
        echo "        bash spec/.ci/checks/run_all.sh"
    else
        cat > "$HOOK" <<'EOF'
#!/usr/bin/env bash
# Specs Sense — run CI checks before every commit ONLY when spec files
# changed. Code-only commits in mixed repos are not slowed down.
if git diff --cached --name-only | grep -qE '^spec/'; then
    exec bash spec/.ci/checks/run_all.sh
fi
exit 0
EOF
        chmod +x "$HOOK"
        echo "[3/5] Wrote pre-commit hook to $HOOK"
        echo "      (only fires when staged files include spec/ paths)"
    fi
else
    echo "[3/5] No .git directory; skipping hook install. Run 'git init' first if desired."
fi

# 4. Tag pass-0
if [ -d "$ROOT/.git" ]; then
    if git -C "$ROOT" rev-parse --verify HEAD >/dev/null 2>&1; then
        if git -C "$ROOT" rev-parse pass-0 >/dev/null 2>&1; then
            echo "[4/5] Tag 'pass-0' already exists; not overwriting."
        else
            git -C "$ROOT" tag pass-0 HEAD
            echo "[4/5] Tagged HEAD as 'pass-0'."
        fi
    else
        echo "[4/5] No commits yet; skipping pass-0 tag. Tag manually after first commit:"
        echo "      git tag pass-0"
    fi
else
    echo "[4/5] No .git directory; skipping pass-0 tag."
fi

# 5. Bootstrap spec/passes/pass-1.md from template, stamping metadata
PASS1="$ROOT/spec/passes/pass-1.md"
if [ -f "$PASS1" ]; then
    echo "[5/5] spec/passes/pass-1.md already exists; not overwriting."
else
    today="$(date -u +%Y-%m-%d)"
    scope_sha="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo "(no commit yet)")"

    cp "$ROOT/spec/passes/pass-template.md" "$PASS1"
    # Strip the DELETE-ME guidance blockquote (first paragraph after the H1)
    # and substitute {{N}} -> 1, {{YYYY-MM-DD}} -> today, etc.
    python3 - "$PASS1" "$today" "$scope_sha" <<'PYEOF' 2>/dev/null || true
import sys, re, pathlib
p = pathlib.Path(sys.argv[1]); today = sys.argv[2]; sha = sys.argv[3]
text = p.read_text(encoding="utf-8")
# Remove the DELETE-ME guidance blockquote (lines starting with "> " after H1 until blank)
text = re.sub(r"\n> \*\*DELETE-ME[^\n]*\n", "\n", text)
text = text.replace("{{N}}", "1")
text = text.replace("{{N+1}}", "2")
text = text.replace("{{YYYY-MM-DD}}", today)
text = text.replace("{{previous-pass-tag}}", "pass-0")
text = text.replace("{{commit-sha}}", sha)
text = text.replace("{{date or \"n/a — exploratory\"}}", "n/a — exploratory")
p.write_text(text, encoding="utf-8")
PYEOF
    echo "[5/5] Created spec/passes/pass-1.md (stamped: $today, baseline pass-0 @ $scope_sha)."
fi

echo
echo "Done. Next steps:"
echo "  1. Edit spec/scope.md — set Mode (greenfield | brownfield | mixed) and"
echo "     fill in/out scope, stakeholder panel, bounded constants, evidence sources."
echo "  2. Edit spec/glossary.md (or leave empty; the LLM will propose canonical terms)."
echo "  3. Open this repo in your LLM driver of choice (Cursor, Claude Code,"
echo "     OpenAI Codex, Aider, or any LLM you can point at spec/AGENTS.md). Examples:"
echo "       claude .         # Claude Code"
echo "       cursor .         # Cursor"
echo "       aider            # Aider"
echo "     Note: AGENTS.md auto-load conventions look at repo root by default;"
echo "     since this template puts AGENTS.md at spec/AGENTS.md, you may need to"
echo "     point your driver at it explicitly. See spec/README.md."
echo "  4. Tell it: \"Read spec/AGENTS.md and spec/passes/pass-1.md, then start Round 1 against spec/scope.md.\""
echo "  5. Approve / correct each proposed record interactively. The LLM updates"
echo "     spec/passes/pass-1.md as work progresses — that's where you skim 'where are we?'."
echo "  6. The LLM commits and opens PRs only with your explicit approval."
echo "  7. After each pass converges, the LLM asks before tagging:  git tag pass-N"
