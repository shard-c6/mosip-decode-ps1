#!/usr/bin/env bash
#
# The whole thing in one command: bring the stack up, run conformance, write the result and
# the consolidated report, and shut the stack down again.
#
#   ./run-full-stack-conformance.sh --component verify
#   ./run-full-stack-conformance.sh --component certify
#   ./run-full-stack-conformance.sh --combined
#
# Options, after the component:
#   --tunnel     also start ngrok inside the stack (needs NGROK_AUTHTOKEN in docker/.env);
#                leave it out when an ngrok agent already serves PUBLIC_HOST on this machine
#   --keep-up    leave the stack running afterwards (default: shut it down)
#   --out DIR    where to write results (default: results/)
#
# Writes DIR/conformance.json (the result, read by the api-testrig classes and CI) and
# DIR/report/ (report.md, report.html, badge.svg). Exit status is the gate's verdict:
# 0 nothing regressed, 1 a regression or harness error, 2 a setup problem.
#
# This is scripts/stack.sh followed by run-conformance.sh. Use those two directly when the
# stack is already up.

set -euo pipefail
cd "$(dirname "$0")"

usage() { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }

case "${1:-}" in
  --component) [ -n "${2:-}" ] || usage; component=$2; runner_args=(--component "$2"); shift 2 ;;
  --combined)  component=combined; runner_args=(--combined); shift ;;
  *)           usage ;;
esac
case "$component" in verify|certify|combined) ;; *) usage ;; esac

tunnel=() keep_up=false out=results
while [ $# -gt 0 ]; do
  case "$1" in
    --tunnel)  tunnel=(--tunnel) ;;
    --keep-up) keep_up=true ;;
    --out)     [ -n "${2:-}" ] || usage; out=$2; shift ;;
    *)         usage ;;
  esac
  shift
done

if [ "$keep_up" = false ]; then
  trap 'echo; echo "Stopping the stack (--keep-up to leave it running)"; scripts/stack.sh down >/dev/null 2>&1 || true' EXIT
fi

scripts/stack.sh up "$component" ${tunnel[@]+"${tunnel[@]}"}

# The gate's exit status is this script's exit status; don't let `set -e` swallow it.
status=0
./run-conformance.sh "${runner_args[@]}" --output "$out/conformance.json" --report "$out/report" || status=$?
echo "Result: $out/conformance.json   Report: $out/report/report.html"
exit "$status"
