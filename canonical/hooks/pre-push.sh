
# The acceptance test has already caught two regressions that nothing else
# would have: an assumption that the repo was unprojected, and a target count
# baked in as a constant. Both were true when written and both went silently
# wrong when the world moved. It runs in ~300ms. Do not push past it.
_ms_root=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -n "$_ms_root" ] && [ -x "$_ms_root/tests/acceptance.py" ]; then
  if ! "$_ms_root/tests/acceptance.py" >/dev/null 2>&1; then
    echo >&2 "machine-state: acceptance test FAILED — push aborted."
    echo >&2 "  run tests/acceptance.py to see which assertion failed,"
    echo >&2 "  or 'git push --no-verify' if you genuinely mean to push anyway."
    exit 1
  fi
fi
