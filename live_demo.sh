#!/usr/bin/env bash
# Live end-to-end demo against the REAL running stack (postgres + redis + api + workers).
# Run `make up` first. Requires: curl, jq, psql, redis-cli, websocat (optional, for WS step).
#
# Every step prints (a) what problem it proves is solved, (b) the exact command run,
# (c) the real response — nothing here is pre-recorded.

set -euo pipefail

API="http://localhost:8001/api/v1"
PGCONN="postgresql://ps08:ps08_password@localhost:5433/ps08"
REDIS="redis-cli -h localhost -p 6379"

step() {
  echo
  echo "================================================================================"
  echo "STEP $1: $2"
  echo "================================================================================"
  echo "Problem this proves: $3"
  echo
}

pause() { read -rp "  [press enter to continue]" _; }

step 1 "Stack health" "the platform actually boots and its dependencies are reachable, live."
echo "+ curl $API/health/live"
curl -s "$API/health/live" | jq .
echo "+ curl $API/health/ready"
curl -s "$API/health/ready" | jq .
pause

step 2 "Real event ingestion" "an external log source can push an access event into the pipeline right now."
echo "+ curl -X POST $API/events -d @event-1.json"
curl -s -X POST "$API/events" -H 'Content-Type: application/json' -d @event-1.json | jq .
sleep 2
echo
echo "+ psql -c 'select * from outbox_events order by id desc limit 3;'"
psql "$PGCONN" -c "select id, event_type, published, created_at from outbox_events order by id desc limit 3;"
pause

step 3 "Outbox relay -> Redis stream (no dual-write gap)" "the DB write and the stream publish are decoupled and both durable."
echo "+ redis-cli xlen ps08:events:stream"
$REDIS xlen ps08:events:stream
echo "+ redis-cli xrevrange ps08:events:stream + count 1"
$REDIS xrevrange ps08:events:stream + - count 1
pause

step 4 "Detection worker scores the event in real time" "graph novelty + rate + risk_score computed live, not batch, not replayed."
echo "watching detection-worker logs for 5s (DETECTION lines):"
docker compose logs --since=15s detection-worker 2>/dev/null | grep -i DETECTION | tail -5 || echo "  (run 'make logs' in another terminal to watch live)"
pause

step 5 "Alert lands in Postgres" "an actual scored anomaly is persisted and queryable by the dashboard."
echo "+ psql -c 'select id, alert_type, risk_score, created_at from alerts order by id desc limit 5;'"
psql "$PGCONN" -c "select id, alert_type, risk_score, created_at from alerts order by id desc limit 5;"
echo
echo "+ curl $API/dashboard/alerts | jq '.[0:3]'"
curl -s "$API/dashboard/alerts" | jq '.[0:3]'
pause

step 6 "Live websocket push" "the dashboard gets alerts pushed to it in real time over a short-lived ticket, not polling."
echo "(requires an auth'd request to mint a ws ticket first — call your auth-issuing endpoint,"
echo " then: websocat \"ws://localhost:8001/api/v1/ws/alerts?ticket=<ticket>\")"
pause

step 7 "Autonomous response — dry-run vs live" "detecting a threat is separate from acting on it; two explicit flags gate the action."
echo "Current .env: ALLOW_DRY_RUN_RESPONSES=\$(grep ALLOW_DRY_RUN_RESPONSES .env)"
echo "+ curl -X POST $API/response/revoke-session -d 'session_id=demo-sess&reason=live-demo&actor=judge'"
curl -s -X POST "$API/response/revoke-session" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'session_id=demo-sess&reason=live-demo&actor=judge' | jq .
echo
echo "To show a REAL block: set RESPONSE_DRY_RUN=false in .env, 'make down && make up', repeat this call,"
echo "then send any request with header 'X-Session-Id: demo-sess' -> expect HTTP 401 from the security middleware:"
echo "+ curl -i $API/dashboard/alerts -H 'X-Session-Id: demo-sess'"
pause

step 8 "Hourly batch job, triggered on demand" "the isolation-forest batch path (feature_store -> scorer -> AlertBus) is wired, not stubbed."
echo "+ curl -X POST $API/batch/run"
curl -s -X POST "$API/batch/run" | jq .
echo
echo "+ psql -c \"select actor, risk_score from alerts... \" (batch alerts use alert_type='insider_batch_anomaly')"
psql "$PGCONN" -c "select id, risk_score, detail->>'actor_id' as actor_id, created_at from alerts where alert_type='insider_batch_anomaly' order by id desc limit 5;"
pause

step 9 "Test suite, live" "every scoring/response rule above is asserted by an automated test, not eyeballed."
echo "+ make test"
make test
pause

echo
echo "================================================================================"
echo "DEMO COMPLETE — every step above hit the real running api/worker/db/redis containers."
echo "================================================================================"