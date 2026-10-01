#!/usr/bin/env bash
# One-command setup for the Airflow 3 + Postgres starter stack.
#   ./setup.sh          start (or restart) the stack
#   ./setup.sh --clean  wipe containers + volumes, then start fresh
#   ./setup.sh --reset  return tutorial data to its starting state (added in the tutorial)
set -euo pipefail
cd "$(dirname "$0")"

MODE="${1:-}"

say()  { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
fail() { printf '\n\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

# 1. Docker
docker info >/dev/null 2>&1 || fail "Docker isn't running. Start Docker Desktop (or the docker service) and re-run."
docker compose version >/dev/null 2>&1 || fail "'docker compose' (v2) not found. Update Docker Desktop / install the compose plugin."

# 2. .env with generated secrets
if [[ ! -f .env ]]; then
  say "Creating .env from .env.example"
  cp .env.example .env
fi
gen_if_blank() {  # gen_if_blank VAR "command that prints a value"
  local var="$1" cmd="$2"
  if ! grep -Eq "^${var}=.+" .env; then
    local val; val="$(eval "$cmd")"
    if grep -Eq "^${var}=" .env; then
      sed -i.bak "s|^${var}=.*|${var}=${val}|" .env && rm -f .env.bak
    else
      printf '%s=%s\n' "$var" "$val" >> .env
    fi
    say "Generated ${var}"
  fi
}
gen_if_blank FERNET_KEY "openssl rand -base64 32 | tr '+/' '-_'"
gen_if_blank JWT_SECRET "openssl rand -hex 32"
if [[ "$(uname -s)" == "Linux" ]]; then
  gen_if_blank AIRFLOW_UID "id -u"
fi

# 3. --clean: full teardown
if [[ "$MODE" == "--clean" ]]; then
  say "Removing containers, volumes, and logs"
  docker compose down --volumes --remove-orphans
  rm -rf logs
fi

if [[ "$MODE" == "--reset" ]]; then
  [[ -n "$(docker compose ps -q 2>/dev/null)" ]] || fail "The stack isn't running. Run ./setup.sh first."
  exec tutorials/01-idempotent-loads/reset.sh
fi

# 4. Port check (only when nothing from this project is running yet)
port_in_use() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }
if [[ -z "$(docker compose ps -q 2>/dev/null)" ]]; then
  # shellcheck disable=SC1091
  set -a; source .env; set +a
  for pair in "AIRFLOW_PORT:${AIRFLOW_PORT:-8080}" "POSTGRES_PORT:${POSTGRES_PORT:-5433}"; do
    name="${pair%%:*}"; port="${pair##*:}"
    port_in_use "$port" && fail "Port $port is already in use. Set a different $name in .env and re-run."
  done
fi

# 5. Up, and wait for health checks
mkdir -p logs
say "Starting the stack (first run pulls images and migrates the database; a few minutes)"
docker compose up -d --wait

# 6. Done
set -a; source .env; set +a
say "Airflow is up: http://localhost:${AIRFLOW_PORT:-8080}  (login ${AIRFLOW_USER:-admin} / ${AIRFLOW_PASSWORD:-admin})"
echo "Postgres (warehouse db): localhost:${POSTGRES_PORT:-5433}, user airflow / airflow"
echo "Stop:  docker compose down      Wipe: ./setup.sh --clean"
