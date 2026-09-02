
# The acceptance test has already caught two regressions that nothing else
# would have: an assumption that the repo was unprojected, and a target count
# baked in as a constant. Both were true when written and both went silently
# wrong when the world moved. It runs in ~300ms. Do not push past it.
_ms_root=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -n "$_ms_root" ] && [ -x "$_ms_root/tests/acceptance.py" ]; then
  _ms_fail=""
  "$_ms_root/tests/acceptance.py" >/dev/null 2>&1 || _ms_fail="acceptance"
  if [ -x "$_ms_root/tests/cap.py" ]; then
    "$_ms_root/tests/cap.py" >/dev/null 2>&1 || _ms_fail="${_ms_fail:+$_ms_fail, }cap lifecycle"
  fi
  if [ -n "$_ms_fail" ]; then
    echo >&2 "machine-state: FAILED — push aborted ($_ms_fail)."
    echo >&2 "  run the failing test to see which assertion,"
    echo >&2 "  or 'git push --no-verify' if you genuinely mean to push anyway."
    exit 1
  fi
fi
