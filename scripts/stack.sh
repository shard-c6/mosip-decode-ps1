#!/usr/bin/env bash
#
# Bring the conformance stack up or down, and wait until it actually answers.
#
#   scripts/stack.sh up verify [--tunnel]    suite + Inji Verify (+ ngrok in the stack)
#   scripts/stack.sh up certify              suite + Inji Certify (not yet available)
#   scripts/stack.sh up combined [--tunnel]  suite + both
#   scripts/stack.sh down                    stop everything; data volumes are kept
#   scripts/stack.sh status
#
# Settings: docker/.env (see docker/.env.example).

set -euo pipefail
cd "$(dirname "$0")/../docker"

COMPOSE=(docker compose)
SUITE_URL="https://localhost.emobix.co.uk:8443/api/currentuser"
VERIFY_URL="http://localhost:8080/v1/verify/did.json"

die() { echo "error: $*" >&2; exit 2; }

wait_for() {  # name url [insecure]
  local name=$1 url=$2 flag=${3:-} code
  for _ in $(seq 1 90); do
    code=$(curl -s $flag -o /dev/null -w '%{http_code}' --max-time 5 "$url" || true)
    if [ "$code" = 200 ]; then echo "  $name: up"; return 0; fi
    sleep 4
  done
  die "$name did not answer at $url within 6 minutes (last HTTP $code)"
}

profiles_for() {
  case "$1" in
    verify)   echo "--profile verify" ;;
    certify)  die "the certify profile is not available yet; see docker/docker-compose.yml" ;;
    combined) die "combined needs the certify profile, which is not available yet" ;;
    *)        die "unknown component '$1' (verify | certify | combined)" ;;
  esac
}

case "${1:-}" in
  up)
    [ -f .env ] || die "docker/.env not found; copy docker/.env.example and set PUBLIC_HOST"
    docker info >/dev/null 2>&1 || die "Docker is not running"
    component=${2:-verify}
    read -r -a profiles <<< "$(profiles_for "$component")"
    tunnel=false
    if [ "${3:-}" = "--tunnel" ]; then profiles+=(--profile tunnel); tunnel=true; fi

    setting() { grep -E "^$1=" .env | tail -1 | cut -d= -f2- ; }
    host=$(setting PUBLIC_HOST)
    case "$host" in
      ""|your-name.ngrok-free.dev) die "set PUBLIC_HOST in docker/.env to your ngrok domain" ;;
      http*|*/*) die "PUBLIC_HOST must be a bare hostname, without https:// or a path" ;;
    esac
    if $tunnel && [ -z "$(setting NGROK_AUTHTOKEN)" ]; then
      die "--tunnel needs NGROK_AUTHTOKEN in docker/.env (or run ngrok on the host instead)"
    fi

    "${COMPOSE[@]}" "${profiles[@]}" up -d
    echo "waiting for services:"
    wait_for "conformance suite" "$SUITE_URL" -k
    wait_for "Inji Verify (local)" "$VERIFY_URL"

    if $tunnel || curl -s -o /dev/null --max-time 5 "http://127.0.0.1:4040" ; then
      wait_for "Inji Verify (public, $host)" "https://$host/v1/verify/did.json"
    else
      echo "  note: no tunnel detected. Start one with --tunnel, or run on the host:"
      echo "        ngrok http --url=https://$host 3000"
    fi
    ;;
  down)
    "${COMPOSE[@]}" --profile verify --profile tunnel down
    ;;
  status)
    "${COMPOSE[@]}" --profile verify --profile tunnel ps
    ;;
  *)
    sed -n '3,12p' "$0"; exit 2 ;;
esac
