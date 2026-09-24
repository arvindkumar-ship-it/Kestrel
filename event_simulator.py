#!/usr/bin/env python3
"""
Autonomous traffic simulator for the PS-08 platform.

Runs against the *already running* API (docker-compose up / uvicorn) and
generates realistic access events on its own:

  - N "normal" actors continuously access a shared pool of common resources
    at random low-rate intervals -> builds each actor's baseline.
  - Every so often, the injector picks a random actor and sends it on a
    burst of accesses to a new, sensitive resource -> insider-threat pattern.

No manual form typing. Just run it next to the dashboard and watch the
Alerts tab fire.

Usage:
    python event_simulator.py
    python event_simulator.py --api http://localhost:8010/api/v1 --actors 8
    python event_simulator.py --anomaly-min 15 --anomaly-max 30 --burst-size 6

Stop with Ctrl+C.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

COMMON_RESOURCES = [(f"common-doc-{i}", "document") for i in range(1, 16)]

SENSITIVE_RESOURCES = [
    ("payroll-database", "database"),
    ("hr-salary-export", "document"),
    ("customer-pii-db", "database"),
    ("source-code-repo", "repository"),
    ("finance-ledger", "database"),
    ("exec-comp-plan", "document"),
]

stop_event = threading.Event()
lock = threading.Lock()


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    with lock:
        print(f"[{ts}] {msg}", flush=True)


def post_event(api_base: str, actor_id: str, resource_id: str, resource_type: str) -> None:
    payload = {
        "actor_id": actor_id,
        "resource_id": resource_id,
        "resource_type": resource_type,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{api_base}/events",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
    except Exception as exc:  # noqa: BLE001 - never let a bad request kill the worker thread
        log(f"  !! event post failed for {actor_id} -> {resource_id}: {exc!r}")


def baseline_worker(api_base: str, actor_id: str, min_gap: float, max_gap: float) -> None:
    stop_event.wait(random.uniform(0, max_gap))  # jitter so all actors don't fire at t=0 together
    while not stop_event.is_set():
        resource_id, resource_type = random.choice(COMMON_RESOURCES)
        post_event(api_base, actor_id, resource_id, resource_type)
        log(f"baseline  {actor_id:<14} -> {resource_id}")
        stop_event.wait(random.uniform(min_gap, max_gap))


def anomaly_injector(
    api_base: str,
    actors: list[str],
    anomaly_min: float,
    anomaly_max: float,
    burst_size: int,
) -> None:
    while not stop_event.is_set():
        stop_event.wait(random.uniform(anomaly_min, anomaly_max))
        if stop_event.is_set():
            break
        actor_id = random.choice(actors)
        resource_id, resource_type = random.choice(SENSITIVE_RESOURCES)
        log(f"{'='*60}")
        log(f">>> INJECTING ANOMALY: {actor_id} -> {resource_id} x{burst_size}")
        log(f"{'='*60}")
        for _ in range(burst_size):
            post_event(api_base, actor_id, resource_id, resource_type)
            log(f"  anomaly   {actor_id:<14} -> {resource_id}")
            time.sleep(random.uniform(0.3, 0.8))
        log(">>> burst done — check Alerts tab now")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api", default="http://localhost:8000/api/v1", help="API base URL")
    parser.add_argument("--actors", type=int, default=6, help="number of normal actors")
    parser.add_argument("--baseline-min-gap", type=float, default=2.0, help="min seconds between baseline events per actor")
    parser.add_argument("--baseline-max-gap", type=float, default=6.0, help="max seconds between baseline events per actor")
    parser.add_argument("--anomaly-min", type=float, default=20.0, help="min seconds between anomaly injections")
    parser.add_argument("--anomaly-max", type=float, default=40.0, help="max seconds between anomaly injections")
    parser.add_argument("--burst-size", type=int, default=6, help="events per anomaly burst")
    args = parser.parse_args()

    actors = [f"employee-{i}" for i in range(1, args.actors + 1)]

    log(f"target api: {args.api}")
    log(f"actors: {', '.join(actors)}")
    log(f"anomaly every {args.anomaly_min}-{args.anomaly_max}s, burst size {args.burst_size}")
    log("starting... Ctrl+C to stop")

    threads = []
    for actor_id in actors:
        t = threading.Thread(
            target=baseline_worker,
            args=(args.api, actor_id, args.baseline_min_gap, args.baseline_max_gap),
            daemon=True,
        )
        t.start()
        threads.append(t)

    injector = threading.Thread(
        target=anomaly_injector,
        args=(args.api, actors, args.anomaly_min, args.anomaly_max, args.burst_size),
        daemon=True,
    )
    injector.start()
    threads.append(injector)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("stopping...")
        stop_event.set()
        for t in threads:
            t.join(timeout=2)
        log("stopped")
        sys.exit(0)


if __name__ == "__main__":
    main()