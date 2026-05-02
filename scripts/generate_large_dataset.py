#!/usr/bin/env python3
"""Generate a large, deterministic NexusDocs YAML dataset for performance testing.

Layout (sized to stress the view engine without melting your laptop):

  *    1 company        (acme)
  *    5 divisions      (payments / platform / identity / commerce / data)
  *  100 teams          (20 per division)
  * 1000 people         (10 per team) — with manager / reports_to chains
  *    5 systems        (one per division)
  *  100 services       (one per team, parented under the division's system)
  *    5 kafka clusters (one per division)
  *  100 kafka topics   (one per service)
  *  100 databases
  *  100 caches
  *  100 queues
  *  100 api endpoints  (one per service, parented under the service)

Plus a generous helping of relationships:
  * `member_of` for every person → team
  * `leads`     for the team manager → team
  * `reports_to` chains inside every team
  * `owns`      for every team → service
  * `provides_api`/`calls_api` cross-service traffic
  * `writes_to`/`reads_from` for services ↔ databases / caches
  * `publishes_to`/`consumes_from` for services ↔ queues / kafka topics

Run from the repo root:
    python scripts/generate_large_dataset.py > examples/large-acme-corp.yaml

The output is a multi-document YAML stream identical in shape to the
hand-curated `examples/payments-sample.yaml` so it can be applied via the
seed container, the API, or the CLI without modification.
"""
from __future__ import annotations

import argparse
import random
import sys
from collections.abc import Iterator
from typing import Any


# ---------------------------------------------------------------------------
# Configuration — tweak these knobs if you want a smaller / bigger graph.
# ---------------------------------------------------------------------------

NUM_DIVISIONS = 5
NUM_TEAMS = 100
NUM_PEOPLE = 1000
NUM_SERVICES = 100
NUM_DATABASES = 100
NUM_CACHES = 100
NUM_QUEUES = 100
NUM_KAFKA_TOPICS = 100
NUM_API_ENDPOINTS = 100

DIVISION_NAMES = ["payments", "platform", "identity", "commerce", "data"]
SYSTEM_LABELS = {
    "payments": "Billing Platform",
    "platform": "Internal Platform",
    "identity": "Identity & Access",
    "commerce": "Commerce Suite",
    "data": "Data Platform",
}
DEPARTMENT_THEMES = ["billing", "ledger", "fraud", "tax", "checkout", "search",
                     "catalog", "warehouse", "logistics", "auth", "tenant",
                     "audit", "ml", "analytics", "stream", "metrics", "alerts",
                     "ui", "mobile", "api"]

FIRST_NAMES = ["Alex", "Sam", "Jordan", "Taylor", "Casey", "Morgan", "Riley",
               "Avery", "Quinn", "Cameron", "Drew", "Reese", "Harper", "Skyler",
               "Rowan", "Sage", "Emerson", "Finley", "Hayden", "Kai"]
LAST_NAMES = ["Pinto", "Nguyen", "Patel", "Garcia", "Smith", "Singh", "Brown",
              "Kim", "Davis", "Khan", "Lopez", "Martin", "Jones", "Sato",
              "Walker", "Wright", "Wood", "Hill", "Adams", "Cole"]

PROTOCOLS_REST = ["rest", "grpc", "graphql"]
DB_PROTOCOLS = ["postgres", "mysql", "mongodb", "dynamodb", "cassandra"]
CACHE_PROTOCOLS = ["redis", "memcached"]
QUEUE_PROTOCOLS = ["sqs", "rabbitmq", "nats", "pubsub"]


# ---------------------------------------------------------------------------
# Tiny YAML emitter — we hand-roll the relevant subset so the script has
# *no runtime dependencies* (so you can run it inside or outside a venv).
# ---------------------------------------------------------------------------

def _emit_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    needs_quotes = (
        text == ""
        or any(ch in text for ch in ":#@`{}[],&*?|<>=!%\n")
        or text.lower() in {"yes", "no", "true", "false", "null", "~"}
        or text.startswith(("-", " ", "?", ":", "!", "&"))
        or text != text.strip()
    )
    if needs_quotes:
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return text


def _emit(value: Any, indent: int = 0) -> Iterator[str]:
    pad = "  " * indent
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(v, dict) and v:
                yield f"{pad}{k}:\n"
                yield from _emit(v, indent + 1)
            elif isinstance(v, list) and v:
                yield f"{pad}{k}:\n"
                for item in v:
                    if isinstance(item, dict):
                        first = True
                        for inner_k, inner_v in item.items():
                            prefix = "- " if first else "  "
                            first = False
                            if isinstance(inner_v, (dict, list)) and inner_v:
                                yield f"{pad}  {prefix}{inner_k}:\n"
                                yield from _emit(inner_v, indent + 2)
                            else:
                                yield f"{pad}  {prefix}{inner_k}: {_emit_scalar(inner_v)}\n"
                    else:
                        yield f"{pad}  - {_emit_scalar(item)}\n"
            elif isinstance(v, list):
                yield f"{pad}{k}: []\n"
            elif isinstance(v, dict):
                yield f"{pad}{k}: {{}}\n"
            else:
                yield f"{pad}{k}: {_emit_scalar(v)}\n"
    else:
        yield f"{pad}{_emit_scalar(value)}\n"


def yaml_doc(spec: dict, *, kind: str) -> str:
    out = ["apiVersion: nexusdocs/v1\n", f"kind: {kind}\n", "spec:\n"]
    out.extend(_emit(spec, indent=1))
    return "".join(out)


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def generate(rng: random.Random) -> Iterator[str]:
    yield "# AUTO-GENERATED by scripts/generate_large_dataset.py — do not hand-edit.\n"
    yield "# Run `python scripts/generate_large_dataset.py > examples/large-acme-corp.yaml`\n"
    yield "# to regenerate.\n"

    company_id = "company.acme"
    yield "---\n"
    yield yaml_doc(
        {
            "id": company_id,
            "type": "company",
            "name": "Acme Corp",
            "metadata": {"headquarters": "Austin, TX", "domain": "acme.com"},
        },
        kind="Entity",
    )

    # Divisions ---------------------------------------------------------------
    division_ids: list[str] = []
    for name in DIVISION_NAMES[:NUM_DIVISIONS]:
        did = f"division.{name}"
        division_ids.append(did)
        yield "---\n"
        yield yaml_doc(
            {
                "id": did,
                "type": "division",
                "name": name.title() + " Division",
                "parent": company_id,
            },
            kind="Entity",
        )

    # Systems (one per division) ---------------------------------------------
    system_ids: list[str] = []
    for div_name in DIVISION_NAMES[:NUM_DIVISIONS]:
        sid = f"system.{div_name}"
        system_ids.append(sid)
        yield "---\n"
        yield yaml_doc(
            {
                "id": sid,
                "type": "system",
                "name": SYSTEM_LABELS[div_name],
                "labels": ["tier-1"],
            },
            kind="Entity",
        )

    # Kafka clusters (one per division) --------------------------------------
    kafka_ids: list[str] = []
    for div_name in DIVISION_NAMES[:NUM_DIVISIONS]:
        kid = f"kafka_cluster.{div_name}"
        kafka_ids.append(kid)
        yield "---\n"
        yield yaml_doc(
            {
                "id": kid,
                "type": "kafka_cluster",
                "name": f"{div_name.title()} Kafka",
                "labels": ["kafka", "shared"],
                "metadata": {"region": "us-east-1", "broker_count": 9},
            },
            kind="Entity",
        )

    # Teams (20 per division) ------------------------------------------------
    teams_per_division = NUM_TEAMS // NUM_DIVISIONS
    team_ids: list[str] = []
    team_to_division: dict[str, str] = {}
    for d_idx, div_name in enumerate(DIVISION_NAMES[:NUM_DIVISIONS]):
        for t_idx in range(teams_per_division):
            theme = DEPARTMENT_THEMES[t_idx % len(DEPARTMENT_THEMES)]
            tid = f"team.{div_name}-{theme}-{t_idx:02d}"
            team_ids.append(tid)
            team_to_division[tid] = f"division.{div_name}"
            yield "---\n"
            yield yaml_doc(
                {
                    "id": tid,
                    "type": "team",
                    "name": f"{div_name.title()} · {theme.title()} {t_idx:02d}",
                    "parent": f"division.{div_name}",
                    "metadata": {
                        "slack_channel": f"#team-{div_name}-{theme}-{t_idx:02d}",
                        "on_call_rotation": f"pagerduty:{div_name}-{theme}-{t_idx:02d}",
                    },
                },
                kind="Entity",
            )

    # People (10 per team) ---------------------------------------------------
    people_per_team = NUM_PEOPLE // NUM_TEAMS
    person_ids: list[str] = []
    team_to_people: dict[str, list[str]] = {tid: [] for tid in team_ids}
    person_idx = 0
    for tid in team_ids:
        for _ in range(people_per_team):
            first = FIRST_NAMES[person_idx % len(FIRST_NAMES)]
            last = LAST_NAMES[(person_idx // len(FIRST_NAMES)) % len(LAST_NAMES)]
            pid = f"person.p{person_idx:04d}-{first.lower()}-{last.lower()}"
            person_ids.append(pid)
            team_to_people[tid].append(pid)
            yield "---\n"
            yield yaml_doc(
                {
                    "id": pid,
                    "type": "person",
                    "name": f"{first} {last}",
                    "metadata": {
                        "role": "Engineer" if person_idx % 10 else "Engineering Manager",
                        "email": f"{first.lower()}.{last.lower()}{person_idx}@acme.com",
                    },
                },
                kind="Entity",
            )
            person_idx += 1

    # Services (one per team) ------------------------------------------------
    service_ids: list[str] = []
    team_to_service: dict[str, str] = {}
    for tid in team_ids:
        suffix = tid.removeprefix("team.")
        sid = f"service.{suffix}"
        service_ids.append(sid)
        team_to_service[tid] = sid
        div_name = team_to_division[tid].removeprefix("division.")
        yield "---\n"
        yield yaml_doc(
            {
                "id": sid,
                "type": "service",
                "name": f"{suffix} service",
                "parent": f"system.{div_name}",
                "labels": ["tier-2"],
                "metadata": {
                    "technology": rng.choice(["Go / Echo", "Node.js / Express", "Python / FastAPI", "Rust / Axum"]),
                    "repository": f"https://gitlab.com/acme/{suffix}",
                },
            },
            kind="Entity",
        )

    # API endpoints (one per service) ----------------------------------------
    endpoint_ids: list[str] = []
    service_to_endpoint: dict[str, str] = {}
    for idx, sid in enumerate(service_ids[:NUM_API_ENDPOINTS]):
        eid = f"endpoint.{sid.removeprefix('service.')}"
        endpoint_ids.append(eid)
        service_to_endpoint[sid] = eid
        yield "---\n"
        yield yaml_doc(
            {
                "id": eid,
                "type": "api_endpoint",
                "name": f"GET /api/v1/{sid.removeprefix('service.')}",
                "parent": sid,
                "metadata": {
                    "method": "GET",
                    "path": f"/api/v1/{sid.removeprefix('service.')}",
                    "auth": "oauth2" if idx % 3 == 0 else "service-token",
                    "rate_limit": f"{(idx % 5 + 1) * 100} req/s per consumer",
                },
            },
            kind="Entity",
        )

    # Databases --------------------------------------------------------------
    database_ids: list[str] = []
    for idx in range(NUM_DATABASES):
        engine = DB_PROTOCOLS[idx % len(DB_PROTOCOLS)]
        did = f"database.{engine}-{idx:03d}"
        database_ids.append(did)
        yield "---\n"
        yield yaml_doc(
            {
                "id": did,
                "type": "database",
                "name": f"{engine.title()} #{idx:03d}",
                "labels": [engine, "tier-2"],
                "metadata": {"engine": engine, "version": "15", "pii": idx % 7 == 0},
            },
            kind="Entity",
        )

    # Caches -----------------------------------------------------------------
    cache_ids: list[str] = []
    for idx in range(NUM_CACHES):
        engine = CACHE_PROTOCOLS[idx % len(CACHE_PROTOCOLS)]
        cid = f"cache.{engine}-{idx:03d}"
        cache_ids.append(cid)
        yield "---\n"
        yield yaml_doc(
            {
                "id": cid,
                "type": "cache",
                "name": f"{engine.title()} cache #{idx:03d}",
                "labels": [engine, "cache"],
                "metadata": {"engine": engine, "ttl_seconds": 60 * (idx % 30 + 1)},
            },
            kind="Entity",
        )

    # Queues -----------------------------------------------------------------
    queue_ids: list[str] = []
    for idx in range(NUM_QUEUES):
        proto = QUEUE_PROTOCOLS[idx % len(QUEUE_PROTOCOLS)]
        qid = f"queue.{proto}-{idx:03d}"
        queue_ids.append(qid)
        yield "---\n"
        yield yaml_doc(
            {
                "id": qid,
                "type": "queue",
                "name": f"{proto} queue #{idx:03d}",
                "labels": [proto, "queue"],
                "metadata": {"engine": proto, "max_in_flight": 1024},
            },
            kind="Entity",
        )

    # Kafka topics (one per service) -----------------------------------------
    topic_ids: list[str] = []
    for idx in range(NUM_KAFKA_TOPICS):
        cluster = kafka_ids[idx % len(kafka_ids)]
        suffix = cluster.removeprefix("kafka_cluster.")
        tid = f"topic.{suffix}-events-{idx:03d}"
        topic_ids.append(tid)
        yield "---\n"
        yield yaml_doc(
            {
                "id": tid,
                "type": "kafka_topic",
                "name": f"{suffix}.events.{idx:03d}",
                "parent": cluster,
                "labels": ["kafka"],
                "metadata": {"partitions": 12, "retention_days": 7},
            },
            kind="Entity",
        )

    # ─── Relationships ──────────────────────────────────────────────────────

    # member_of + leads + reports_to (one manager per team, others report to them)
    rel_idx = 0
    for tid, members in team_to_people.items():
        if not members:
            continue
        manager = members[0]
        # Manager leads the team and is a member.
        yield "---\n"
        yield yaml_doc(
            {
                "id": f"rel.r{rel_idx:05d}-leads",
                "source": manager,
                "target": tid,
                "type": "leads",
            },
            kind="Relationship",
        )
        rel_idx += 1
        for pid in members:
            yield "---\n"
            yield yaml_doc(
                {
                    "id": f"rel.r{rel_idx:05d}-member",
                    "source": pid,
                    "target": tid,
                    "type": "member_of",
                },
                kind="Relationship",
            )
            rel_idx += 1
        for pid in members[1:]:
            yield "---\n"
            yield yaml_doc(
                {
                    "id": f"rel.r{rel_idx:05d}-reports",
                    "source": pid,
                    "target": manager,
                    "type": "reports_to",
                },
                kind="Relationship",
            )
            rel_idx += 1

    # team owns service
    for tid, sid in team_to_service.items():
        yield "---\n"
        yield yaml_doc(
            {
                "id": f"rel.r{rel_idx:05d}-owns",
                "source": tid,
                "target": sid,
                "type": "owns",
            },
            kind="Relationship",
        )
        rel_idx += 1

    # service provides_api endpoint
    for sid, eid in service_to_endpoint.items():
        yield "---\n"
        yield yaml_doc(
            {
                "id": f"rel.r{rel_idx:05d}-provides",
                "source": sid,
                "target": eid,
                "type": "provides_api",
                "protocol": "rest",
            },
            kind="Relationship",
        )
        rel_idx += 1

    # service calls_api 1-2 other endpoints
    for sid in service_ids:
        for _ in range(rng.randint(1, 2)):
            target_endpoint = rng.choice(endpoint_ids)
            if target_endpoint == service_to_endpoint.get(sid):
                continue
            yield "---\n"
            yield yaml_doc(
                {
                    "id": f"rel.r{rel_idx:05d}-calls",
                    "source": sid,
                    "target": target_endpoint,
                    "type": "calls_api",
                    "protocol": rng.choice(PROTOCOLS_REST),
                    "mode": "sync",
                    "metadata": {"timeout_ms": 3000, "circuit_breaker": True},
                },
                kind="Relationship",
            )
            rel_idx += 1

    # service writes_to / reads_from a database
    for idx, sid in enumerate(service_ids):
        db = database_ids[idx % len(database_ids)]
        yield "---\n"
        yield yaml_doc(
            {
                "id": f"rel.r{rel_idx:05d}-writes-db",
                "source": sid,
                "target": db,
                "type": "writes_to",
                "protocol": database_ids[idx % len(database_ids)].split(".")[1].split("-")[0],
                "mode": "sync",
            },
            kind="Relationship",
        )
        rel_idx += 1

    # service reads_from a cache
    for idx, sid in enumerate(service_ids):
        cache = cache_ids[idx % len(cache_ids)]
        yield "---\n"
        yield yaml_doc(
            {
                "id": f"rel.r{rel_idx:05d}-reads-cache",
                "source": sid,
                "target": cache,
                "type": "reads_from",
                "protocol": cache.split(".")[1].split("-")[0],
                "mode": "sync",
            },
            kind="Relationship",
        )
        rel_idx += 1

    # service publishes_to a queue
    for idx, sid in enumerate(service_ids):
        q = queue_ids[idx % len(queue_ids)]
        yield "---\n"
        yield yaml_doc(
            {
                "id": f"rel.r{rel_idx:05d}-publishes-queue",
                "source": sid,
                "target": q,
                "type": "publishes_to",
                "protocol": q.split(".")[1].split("-")[0],
                "mode": "async",
            },
            kind="Relationship",
        )
        rel_idx += 1

    # service publishes_to a kafka topic
    for idx, sid in enumerate(service_ids):
        topic = topic_ids[idx % len(topic_ids)]
        yield "---\n"
        yield yaml_doc(
            {
                "id": f"rel.r{rel_idx:05d}-publishes-topic",
                "source": sid,
                "target": topic,
                "type": "publishes_to",
                "protocol": "kafka",
                "mode": "async",
            },
            kind="Relationship",
        )
        rel_idx += 1

    # A few cross-service depends_on edges to give the topology score work
    for sid in rng.sample(service_ids, k=min(len(service_ids), 60)):
        partner = rng.choice(service_ids)
        if partner == sid:
            continue
        yield "---\n"
        yield yaml_doc(
            {
                "id": f"rel.r{rel_idx:05d}-depends",
                "source": sid,
                "target": partner,
                "type": "depends_on",
            },
            kind="Relationship",
        )
        rel_idx += 1

    # A few "thematic" doc fragments so the view engine has something to assemble.
    sample_service = service_ids[0]
    yield "---\n"
    yield yaml_doc(
        {
            "id": "docfrag.acme-readme",
            "title": "Acme Engineering — README",
            "body": (
                "Acme Corp organises its engineering org into "
                f"{NUM_DIVISIONS} divisions, {NUM_TEAMS} teams and "
                f"{len(person_ids)} engineers.\n\nEvery team owns exactly one "
                "production service and a small set of supporting datastores."
            ),
            "subjects": [{"entity": company_id}],
            "tags": ["onboarding", "overview"],
            "coverage": {
                "zoom_min": 0,
                "zoom_max": 25,
                "lenses": ["product", "onboarding"],
                "granularity": "company",
                "lift_on": {"path_match": True},
                "lift_by": 5,
            },
            "provenance": {
                "source_type": "manual",
                "generated_by": "human",
                "confidence": 1.0,
                "reviewed": True,
            },
        },
        kind="DocFragment",
    )
    yield "---\n"
    yield yaml_doc(
        {
            "id": "docfrag.sample-service-runbook",
            "title": f"{sample_service} — runbook",
            "body": (
                "This service is part of the synthetic Acme dataset used to "
                "stress the view engine. Pager: see the team's `on_call_rotation`."
            ),
            "subjects": [{"entity": sample_service}],
            "tags": ["runbook", "operations"],
            "coverage": {
                "zoom_min": 30,
                "zoom_max": 90,
                "lenses": ["technical", "operations", "debug"],
                "granularity": "service",
                "lift_on": {"path_match": True},
                "lift_by": 10,
            },
            "provenance": {
                "source_type": "runbook",
                "generated_by": "human",
                "confidence": 1.0,
                "reviewed": True,
            },
        },
        kind="DocFragment",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic output (default: 42).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="-",
        help="Output path (`-` for stdout).",
    )
    args = parser.parse_args()
    rng = random.Random(args.seed)

    if args.output == "-":
        for chunk in generate(rng):
            sys.stdout.write(chunk)
    else:
        with open(args.output, "w", encoding="utf-8") as fh:
            for chunk in generate(rng):
                fh.write(chunk)


if __name__ == "__main__":
    main()
