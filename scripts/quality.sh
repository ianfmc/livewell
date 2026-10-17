#!/usr/bin/env bash
#
# LW-604 — targeted quality runner.
#
# Runs the REAL per-app tools that exist today and prints an honest summary.
# It does NOT install or invent tooling. Two pre-existing failure classes are
# baselined as KNOWN (non-blocking) so this gate flags only NEW regressions:
#
#   - API: 7 pre-existing pytest failures (tests/explain x4, tests/models x3)
#   - WEB: 8 pre-existing eslint errors (react-refresh / set-state-in-effect /
#          no-explicit-any) + 4 warnings
#
# Baselines are recorded from the real run on 2026-10-16. When a baseline is
# fixed (see the proposed follow-up tasks in docs/session-handoff-2026-10-16.md),
# lower the corresponding KNOWN_* number so the gate tightens.
#
# Exit code: 0 if results match-or-beat the baselines; 1 if a NEW regression
# appears (more failures than baselined, or a passing suite starts failing).
#
# Usage:  ./scripts/quality.sh            # run everything
#         ./scripts/quality.sh api        # API only
#         ./scripts/quality.sh web        # web only
#
# NOTE: not wired to a PostFileSave hook (too frequent); run manually or on a
# Stop/CI event. See .kiro/hooks for optional later wiring.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT/apps/api"
WEB_DIR="$ROOT/apps/web"

# --- known pre-existing failure baselines (real run 2026-10-16) --------------
KNOWN_API_PYTEST_FAILS=7     # tests/explain/test_router.py x4, tests/models/test_train.py x3
KNOWN_WEB_LINT_ERRORS=0      # LW-7001 fixed the 8 pre-existing errors (2026-10-17)

new_regression=0
summary=()

say() { printf '%s\n' "$*"; }
hr()  { printf -- '----------------------------------------------------------\n'; }

run_api() {
  hr; say "API — uv run pytest (apps/api)"; hr
  if ! command -v uv >/dev/null 2>&1; then
    summary+=("API pytest        : SKIPPED (uv not found)"); return
  fi
  local out fails
  out="$(cd "$API_DIR" && AWS_DEFAULT_REGION=us-west-1 uv run pytest -q 2>&1)"
  printf '%s\n' "$out" | tail -3
  # parse "N failed" from the summary line. Avoid `| head` early-close under
  # pipefail (SIGPIPE on upstream grep can blank the result); use sed + tail.
  fails="$(printf '%s\n' "$out" | grep -oE '[0-9]+ failed' | sed -E 's/ failed//' | tail -1)"
  fails="${fails:-0}"
  if [ "$fails" -gt "$KNOWN_API_PYTEST_FAILS" ]; then
    summary+=("API pytest        : NEW REGRESSION — $fails failed (baseline $KNOWN_API_PYTEST_FAILS)")
    new_regression=1
  elif [ "$fails" -eq "$KNOWN_API_PYTEST_FAILS" ]; then
    summary+=("API pytest        : OK — $fails pre-existing failures (baselined, non-blocking)")
  else
    summary+=("API pytest        : IMPROVED — $fails failed (baseline $KNOWN_API_PYTEST_FAILS; lower KNOWN_API_PYTEST_FAILS)")
  fi
}

run_web() {
  if ! command -v npm >/dev/null 2>&1; then
    summary+=("WEB               : SKIPPED (npm not found)"); return
  fi

  hr; say "WEB — npm run lint (apps/web)"; hr
  local lint_out lint_errs
  lint_out="$(cd "$WEB_DIR" && npm run lint 2>&1)"
  printf '%s\n' "$lint_out" | grep -E 'problems|error|warning' | tail -4
  # Parse errors from the authoritative summary line only: "N problems (E errors, W warnings)".
  # Do NOT grep bare "N error" — the "0 errors ... fixable" hint line would mislead.
  lint_errs="$(printf '%s\n' "$lint_out" | grep -oE '\([0-9]+ error' | grep -oE '[0-9]+' | tail -1)"
  lint_errs="${lint_errs:-0}"
  if [ "$lint_errs" -gt "$KNOWN_WEB_LINT_ERRORS" ]; then
    summary+=("WEB eslint        : NEW REGRESSION — $lint_errs errors (baseline $KNOWN_WEB_LINT_ERRORS)")
    new_regression=1
  elif [ "$lint_errs" -eq "$KNOWN_WEB_LINT_ERRORS" ]; then
    summary+=("WEB eslint        : OK — $lint_errs pre-existing errors (baselined, non-blocking)")
  else
    summary+=("WEB eslint        : IMPROVED — $lint_errs errors (baseline $KNOWN_WEB_LINT_ERRORS; lower KNOWN_WEB_LINT_ERRORS)")
  fi

  hr; say "WEB — npm run build  (tsc typecheck + build)"; hr
  if (cd "$WEB_DIR" && npm run build >/tmp/lw604_web_build.log 2>&1); then
    summary+=("WEB typecheck/build: OK")
  else
    tail -5 /tmp/lw604_web_build.log
    summary+=("WEB typecheck/build: NEW REGRESSION — build/tsc failed")
    new_regression=1
  fi

  hr; say "WEB — npm run test -- --run  (vitest)"; hr
  if (cd "$WEB_DIR" && npm run test -- --run >/tmp/lw604_web_test.log 2>&1); then
    tail -3 /tmp/lw604_web_test.log
    summary+=("WEB vitest        : OK")
  else
    tail -8 /tmp/lw604_web_test.log
    summary+=("WEB vitest        : NEW REGRESSION — vitest failed")
    new_regression=1
  fi
}

target="${1:-all}"
case "$target" in
  api) run_api ;;
  web) run_web ;;
  all) run_api; run_web ;;
  *) say "usage: $0 [api|web|all]"; exit 2 ;;
esac

hr; say "QUALITY SUMMARY"; hr
for line in "${summary[@]}"; do say "  $line"; done
hr
# NOTE (LW-604): the API has no formatter (ruff/black) or typechecker (mypy)
# installed. Those are a proposed follow-up task, intentionally NOT added here.
say "  API format/typecheck: ABSENT — proposed follow-up (ruff + mypy), not run"
hr

if [ "$new_regression" -ne 0 ]; then
  say "RESULT: NEW REGRESSION detected — fix before shipping."
  exit 1
fi
say "RESULT: OK — no new regressions beyond recorded baselines."
exit 0
