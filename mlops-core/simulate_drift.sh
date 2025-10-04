#!/usr/bin/env bash
set -euo pipefail

URL="${URL:-http://localhost:8080}"
PRED_ENDPOINT="${URL}/predict"
DRIFT_ENDPOINT="${URL}/drift"
HEALTH_ENDPOINT="${URL}/healthz"

echo "Checking health at ${HEALTH_ENDPOINT}..."
curl -sf "${HEALTH_ENDPOINT}" || { echo "Service not healthy"; exit 1; }

send_batch() {
  local payload="$1"
  curl -s -X POST "${PRED_ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d "${payload}" >/dev/null
}

# warm-up: send a few baseline (non-drift) requests
echo "Sending baseline traffic..."
BASE_PAYLOAD='{"instances": [[5.1, 3.5, 1.4, 0.2], [5.7, 3.0, 4.2, 1.2], [6.2, 3.4, 5.4, 2.3]]}'
for i in $(seq 1 5); do
  send_batch "${BASE_PAYLOAD}"
done

# drift: shift feature 0 by +3 and feature 2 by +2 (outside typical Iris ranges)
echo "Sending drifted traffic..."
DRIFT_PAYLOAD_1='{"instances": [[8.1, 3.5, 3.4, 0.2], [8.7, 3.0, 6.2, 1.2], [9.2, 3.4, 7.4, 2.3]]}'
for i in $(seq 1 4); do
  send_batch "${DRIFT_PAYLOAD_1}"
done

# more aggressive drift (scale features 0 and 2)
DRIFT_PAYLOAD_2='{"instances": [[10.2, 3.5, 2.8, 0.2], [11.4, 3.0, 8.4, 1.2], [12.4, 3.4, 10.8, 2.3]]}'
for i in $(seq 1 4); do
  send_batch "${DRIFT_PAYLOAD_2}"
done

# extreme/out-of-range values to trigger expectations
DRIFT_PAYLOAD_3='{"instances": [[-1, 10, 20, 5], [100, 100, 100, 100], [0, 0, 0, 0]]}'
for i in $(seq 1 2); do
  send_batch "${DRIFT_PAYLOAD_3}"
done

echo "Done."
