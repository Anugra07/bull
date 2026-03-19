#!/bin/bash

set -euo pipefail

# Startup script for Bull - Carbon Offset Land Analyzer.
# Starts backend + frontend and validates runtime ML readiness.

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3000"
BACKEND_RELOAD="${BULL_BACKEND_RELOAD:-0}"
BACKEND_WAIT_SECONDS="${BULL_BACKEND_WAIT_SECONDS:-30}"
FRONTEND_WAIT_SECONDS="${BULL_FRONTEND_WAIT_SECONDS:-180}"

BACKEND_PID=""
FRONTEND_PID=""

stop_pid_tree() {
  local pid="$1"
  if [ -z "${pid:-}" ]; then
    return
  fi

  # Kill direct children first so reload/dev wrappers do not leave listeners behind.
  local children
  children="$(pgrep -P "$pid" 2>/dev/null || true)"
  if [ -n "$children" ]; then
    for child in $children; do
      stop_pid_tree "$child"
    done
  fi

  kill "$pid" 2>/dev/null || true
}

wait_for_port_release() {
  local port="$1"
  for _ in $(seq 1 20); do
    if ! lsof -ti "tcp:${port}" >/dev/null 2>&1; then
      return
    fi
    sleep 0.5
  done
}

ensure_port_available() {
  local port="$1"
  local label="$2"
  local pids
  pids="$(lsof -ti "tcp:${port}" 2>/dev/null || true)"
  if [ -z "$pids" ]; then
    return
  fi

  echo "$label port $port is already in use."
  echo "Attempting to stop existing listener(s): $pids"
  for pid in $pids; do
    stop_pid_tree "$pid"
  done
  wait_for_port_release "$port"

  if lsof -ti "tcp:${port}" >/dev/null 2>&1; then
    echo "Port $port is still busy. Stop the existing process and retry."
    exit 1
  fi
}

cleanup() {
  echo ""
  echo "Stopping servers..."
  if [ -n "${BACKEND_PID:-}" ]; then
    stop_pid_tree "$BACKEND_PID"
  fi
  if [ -n "${FRONTEND_PID:-}" ]; then
    stop_pid_tree "$FRONTEND_PID"
  fi
  echo "Servers stopped."
  exit 0
}

trap cleanup INT TERM

echo "Starting Bull - Carbon Offset Land Analyzer..."
echo ""

if [ ! -x "$BACKEND_DIR/.venv/bin/uvicorn" ]; then
  echo "Missing backend venv or uvicorn at $BACKEND_DIR/.venv/bin/uvicorn"
  exit 1
fi

if [ ! -d "$BACKEND_DIR/ml/models" ]; then
  echo "Missing model directory at $BACKEND_DIR/ml/models"
  exit 1
fi

ensure_port_available 8000 "Backend"
ensure_port_available 3000 "Frontend"

echo "Starting backend server..."
cd "$BACKEND_DIR"
if [ "$BACKEND_RELOAD" = "1" ]; then
  echo "Backend reload mode: enabled"
  "$BACKEND_DIR/.venv/bin/uvicorn" app.main:app \
    --reload \
    --reload-dir "$BACKEND_DIR/app" \
    --reload-dir "$BACKEND_DIR/scripts" \
    --reload-dir "$BACKEND_DIR/ml" \
    --reload-exclude ".venv/**" \
    --reload-exclude "__pycache__/**" \
    --reload-exclude "*.pyc" \
    --port 8000 &
else
  echo "Backend reload mode: disabled"
  "$BACKEND_DIR/.venv/bin/uvicorn" app.main:app --port 8000 &
fi
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

echo "Waiting for backend health..."
for _ in $(seq 1 "$BACKEND_WAIT_SECONDS"); do
  if curl --max-time 3 -fsS "$BACKEND_URL/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! curl --max-time 3 -fsS "$BACKEND_URL/health" >/dev/null 2>&1; then
  echo "Backend did not become healthy at $BACKEND_URL"
  cleanup
fi

echo ""
echo "Starting frontend server..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

echo "Waiting for frontend..."
for _ in $(seq 1 "$FRONTEND_WAIT_SECONDS"); do
  if curl --max-time 5 -fsS "$FRONTEND_URL" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! curl --max-time 5 -fsS "$FRONTEND_URL" >/dev/null 2>&1; then
  echo "Frontend did not become healthy at $FRONTEND_URL"
  cleanup
fi

echo ""
echo "Both servers started."
echo "Frontend: $FRONTEND_URL"
echo "Backend:  $BACKEND_URL"
echo "API Docs: $BACKEND_URL/docs"
echo ""
echo "Checking ML runtime status..."
ML_STATUS="$(curl --max-time 20 -fsS "$BACKEND_URL/ml/status" || true)"
if [ -z "$ML_STATUS" ]; then
  echo "Warning: /ml/status did not return within 20s. Models may still be warming up."
else
  echo "$ML_STATUS"
  if ! echo "$ML_STATUS" | grep -q '"ready":true'; then
    echo "Warning: backend started, but one or more ML models are not ready."
  fi
fi
echo ""
echo "Press Ctrl+C to stop both servers."

wait
