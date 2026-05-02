"""Neo4j-backed `GraphRepository`.

We model:
- Entities  → `:Entity { id, kind, name, parent, labels, metadata, source, created_at, updated_at }`
- Relationships → typed edges with `[:REL_<TYPE>]` plus a generic `[:RELATIONSHIP]` for indexable queries.
- Fragments → `:Fragment { id, title, body, format, subjects, relations, tags, coverage, provenance }`
- Presets   → `:Preset { id, name, owner, ... }`

Fragment-to-entity anchoring is materialised as `(Fragment)-[:ANCHORS_ENTITY]->(Entity)` so
`fragments_by_subject` is a cheap lookup. Relation anchors materialise as
`(Fragment)-[:ANCHORS_REL]->(:RelationshipNode)` because Neo4j edges aren't
queryable by ID directly without an APOC dependency.

The repository complies with the same Protocol the in-memory repo does, so
the parity test exercises both behind a single fixture.
"""

import json
from datetime import UTC, datetime

try:
    from neo4j import Driver, GraphDatabase  # type: ignore
except ImportError:  # pragma: no cover
    GraphDatabase = None  # type: ignore
    Driver = None  # type: ignore

from ..core import DocFragment, Entity, Relationship, ViewPreset
from ..core.enums import ALLOWED_PARENT_KINDS, Mode, Protocol
from .repository import (
    EntityNotFoundError,
    FragmentNotFoundError,
    PresetNotFoundError,
    RelationshipNotFoundError,
    RepositoryError,
    Transaction,
)


def _to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _from_iso(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _entity_to_record(entity: Entity) -> dict:
    return {
        "id": entity.id,
        "kind": entity.kind.value,
        "name": entity.name,
        "parent": entity.parent,
        "labels": list(entity.labels),
        "metadata": json.dumps(entity.metadata),
        "source": entity.source.model_dump_json() if entity.source else None,
        "created_at": _to_iso(entity.created_at),
        "updated_at": _to_iso(entity.updated_at),
    }


def _record_to_entity(rec: dict) -> Entity:
    payload = {
        "id": rec["id"],
        "kind": rec["kind"],
        "name": rec["name"],
        "parent": rec.get("parent"),
        "labels": list(rec.get("labels") or []),
        "metadata": json.loads(rec.get("metadata") or "{}"),
        "created_at": _from_iso(rec.get("created_at")) or datetime.now(UTC),
        "updated_at": _from_iso(rec.get("updated_at")) or datetime.now(UTC),
    }
    if rec.get("source"):
        payload["source"] = json.loads(rec["source"])
    return Entity.model_validate(payload)


def _rel_to_record(rel: Relationship) -> dict:
    return {
        "id": rel.id,
        "source": rel.source,
        "target": rel.target,
        "type": rel.type.value,
        "protocol": str(rel.protocol) if rel.protocol else None,
        "mode": rel.mode.value if rel.mode else None,
        "metadata": json.dumps(rel.metadata),
        "source_ref": rel.source_ref.model_dump_json() if rel.source_ref else None,
        "created_at": _to_iso(rel.created_at),
        "updated_at": _to_iso(rel.updated_at),
    }


def _record_to_rel(rec: dict) -> Relationship:
    payload = {
        "id": rec["id"],
        "source": rec["source"],
        "target": rec["target"],
        "type": rec["type"],
        "metadata": json.loads(rec.get("metadata") or "{}"),
        "created_at": _from_iso(rec.get("created_at")) or datetime.now(UTC),
        "updated_at": _from_iso(rec.get("updated_at")) or datetime.now(UTC),
    }
    if rec.get("protocol"):
        try:
            payload["protocol"] = Protocol(rec["protocol"])
        except ValueError:
            payload["protocol"] = rec["protocol"]
    if rec.get("mode"):
        payload["mode"] = Mode(rec["mode"])
    if rec.get("source_ref"):
        payload["source_ref"] = json.loads(rec["source_ref"])
    return Relationship.model_validate(payload)


def _fragment_to_record(fragment: DocFragment) -> dict:
    return {
        "id": fragment.id,
        "doc_id": fragment.doc_id,
        "title": fragment.title,
        "body": fragment.body,
        "format": fragment.format,
        "subjects": [s.entity for s in fragment.subjects],
        "relations": [r.rel for r in fragment.relations],
        "tags": list(fragment.tags),
        "coverage": fragment.coverage.model_dump_json(),
        "provenance": fragment.provenance.model_dump_json(),
    }


def _record_to_fragment(rec: dict) -> DocFragment:
    payload = {
        "id": rec["id"],
        "doc_id": rec.get("doc_id"),
        "title": rec["title"],
        "body": rec["body"],
        "format": rec.get("format", "markdown"),
        "subjects": [{"entity": s} for s in rec.get("subjects") or []],
        "relations": [{"rel": r} for r in rec.get("relations") or []],
        "tags": list(rec.get("tags") or []),
        "coverage": json.loads(rec["coverage"]),
        "provenance": json.loads(rec["provenance"]),
    }
    return DocFragment.model_validate(payload)


def _preset_to_record(preset: ViewPreset) -> dict:
    return {
        "id": preset.id,
        "name": preset.name,
        "owner": preset.owner,
        "shared_with": list(preset.shared_with),
        "focus": preset.focus,
        "zoom": preset.zoom,
        "lenses": list(preset.lenses),
        "radius": preset.radius,
        "filters": preset.filters.model_dump_json(),
        "created_at": _to_iso(preset.created_at),
        "updated_at": _to_iso(preset.updated_at),
    }


def _record_to_preset(rec: dict) -> ViewPreset:
    payload = {
        "id": rec["id"],
        "name": rec["name"],
        "owner": rec["owner"],
        "shared_with": list(rec.get("shared_with") or []),
        "focus": rec["focus"],
        "zoom": rec["zoom"],
        "lenses": list(rec.get("lenses") or []),
        "radius": rec["radius"],
        "filters": json.loads(rec["filters"]),
        "created_at": _from_iso(rec.get("created_at")) or datetime.now(UTC),
        "updated_at": _from_iso(rec.get("updated_at")) or datetime.now(UTC),
    }
    return ViewPreset.model_validate(payload)


# --- Transaction implementation ---------------------------------------------


class _Neo4jTransaction(Transaction):
    def __init__(self, repo: "Neo4jGraphRepository") -> None:
        self._repo = repo
        self._session = repo.driver.session(database=repo.database)
        self._tx = self._session.begin_transaction()
        self._committed = False

    def __enter__(self) -> "_Neo4jTransaction":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc is not None:
            self.rollback()
            return False
        if not self._committed:
            self.commit()
        return False

    def commit(self) -> None:
        self._tx.commit()
        self._session.close()
        self._committed = True

    def rollback(self) -> None:
        if not self._committed:
            try:
                self._tx.rollback()
            finally:
                self._session.close()
                self._committed = True

    def run(self, *args, **kwargs):
        return self._tx.run(*args, **kwargs)


# --- Repository -------------------------------------------------------------


class Neo4jGraphRepository:
    def __init__(
        self,
        *,
        uri: str,
        user: str,
        password: str,
        database: str = "neo4j",
    ) -> None:
        if GraphDatabase is None:
            raise RepositoryError("neo4j driver is not installed")
        self.driver: Driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database
        self._initialized = False

    def close(self) -> None:
        self.driver.close()

    def initialize(self) -> None:
        if self._initialized:
            return
        with self.driver.session(database=self.database) as session:
            session.run(
                "CREATE CONSTRAINT entity_id IF NOT EXISTS "
                "FOR (e:Entity) REQUIRE e.id IS UNIQUE"
            )
            session.run(
                "CREATE CONSTRAINT relationship_node_id IF NOT EXISTS "
                "FOR (r:RelationshipNode) REQUIRE r.id IS UNIQUE"
            )
            session.run(
                "CREATE CONSTRAINT fragment_id IF NOT EXISTS "
                "FOR (f:Fragment) REQUIRE f.id IS UNIQUE"
            )
            session.run(
                "CREATE CONSTRAINT preset_id IF NOT EXISTS "
                "FOR (p:Preset) REQUIRE p.id IS UNIQUE"
            )
            session.run("CREATE INDEX entity_kind IF NOT EXISTS FOR (e:Entity) ON (e.kind)")
            session.run("CREATE INDEX fragment_tags IF NOT EXISTS FOR (f:Fragment) ON (f.tags)")
        self._initialized = True

    def transaction(self) -> Transaction:
        return _Neo4jTransaction(self)

    # --- Entities -----------------------------------------------------

    def upsert_entity(self, entity: Entity) -> Entity:
        if entity.parent is not None:
            try:
                parent = self.get_entity(entity.parent)
            except EntityNotFoundError as e:
                raise RepositoryError(
                    f"entity {entity.id!r} parent {entity.parent!r} does not exist"
                ) from e
            allowed = ALLOWED_PARENT_KINDS.get(entity.kind, frozenset())
            if parent.kind not in allowed:
                raise RepositoryError(
                    f"entity {entity.id!r} (kind={entity.kind.value}) cannot have parent of kind "
                    f"{parent.kind.value!r}"
                )

        record = _entity_to_record(entity)
        with self.driver.session(database=self.database) as session:
            session.run(
                """
                MERGE (e:Entity { id: $id })
                ON CREATE SET e.created_at = $created_at
                SET e.kind = $kind,
                    e.name = $name,
                    e.parent = $parent,
                    e.labels = $labels,
                    e.metadata = $metadata,
                    e.source = $source,
                    e.updated_at = $updated_at
                """,
                **record,
            )
        return entity

    def get_entity(self, entity_id: str) -> Entity:
        with self.driver.session(database=self.database) as session:
            r = session.run(
                "MATCH (e:Entity { id: $id }) RETURN e", id=entity_id
            ).single()
        if r is None:
            raise EntityNotFoundError(entity_id)
        return _record_to_entity(dict(r["e"]))

    def has_entity(self, entity_id: str) -> bool:
        with self.driver.session(database=self.database) as session:
            r = session.run(
                "MATCH (e:Entity { id: $id }) RETURN count(e) AS n", id=entity_id
            ).single()
        return bool(r and r["n"] > 0)

    def list_entities(self) -> list[Entity]:
        with self.driver.session(database=self.database) as session:
            recs = session.run("MATCH (e:Entity) RETURN e").data()
        return [_record_to_entity(dict(r["e"])) for r in recs]

    def delete_entity(self, entity_id: str) -> None:
        if not self.has_entity(entity_id):
            raise EntityNotFoundError(entity_id)
        with self.driver.session(database=self.database) as session:
            session.run(
                """
                MATCH (e:Entity { id: $id })
                OPTIONAL MATCH (rn:RelationshipNode)
                  WHERE rn.source = $id OR rn.target = $id
                DETACH DELETE e, rn
                """,
                id=entity_id,
            )

    # --- Relationships -------------------------------------------------

    def upsert_relationship(self, rel: Relationship) -> Relationship:
        if not self.has_entity(rel.source):
            raise RepositoryError(f"relationship source {rel.source!r} does not exist")
        if not self.has_entity(rel.target):
            raise RepositoryError(f"relationship target {rel.target!r} does not exist")
        rec = _rel_to_record(rel)
        with self.driver.session(database=self.database) as session:
            session.run(
                """
                MATCH (s:Entity { id: $source }), (t:Entity { id: $target })
                MERGE (rn:RelationshipNode { id: $id })
                ON CREATE SET rn.created_at = $created_at
                SET rn.source = $source,
                    rn.target = $target,
                    rn.type = $type,
                    rn.protocol = $protocol,
                    rn.mode = $mode,
                    rn.metadata = $metadata,
                    rn.source_ref = $source_ref,
                    rn.updated_at = $updated_at
                MERGE (s)-[:CONNECTS { id: $id }]->(t)
                """,
                **rec,
            )
        return rel

    def get_relationship(self, rel_id: str) -> Relationship:
        with self.driver.session(database=self.database) as session:
            r = session.run(
                "MATCH (rn:RelationshipNode { id: $id }) RETURN rn", id=rel_id
            ).single()
        if r is None:
            raise RelationshipNotFoundError(rel_id)
        return _record_to_rel(dict(r["rn"]))

    def has_relationship(self, rel_id: str) -> bool:
        with self.driver.session(database=self.database) as session:
            r = session.run(
                "MATCH (rn:RelationshipNode { id: $id }) RETURN count(rn) AS n",
                id=rel_id,
            ).single()
        return bool(r and r["n"] > 0)

    def list_relationships(self) -> list[Relationship]:
        with self.driver.session(database=self.database) as session:
            recs = session.run("MATCH (rn:RelationshipNode) RETURN rn").data()
        return [_record_to_rel(dict(r["rn"])) for r in recs]

    def delete_relationship(self, rel_id: str) -> None:
        if not self.has_relationship(rel_id):
            raise RelationshipNotFoundError(rel_id)
        with self.driver.session(database=self.database) as session:
            session.run(
                """
                MATCH (rn:RelationshipNode { id: $id }) DETACH DELETE rn
                """,
                id=rel_id,
            )
            session.run(
                "MATCH ()-[c:CONNECTS { id: $id }]->() DELETE c", id=rel_id
            )

    def edges_of(
        self, entity_id: str, *, direction: str = "both"
    ) -> list[Relationship]:
        if not self.has_entity(entity_id):
            raise EntityNotFoundError(entity_id)
        if direction == "outgoing":
            cypher = "MATCH (rn:RelationshipNode) WHERE rn.source = $id RETURN rn"
        elif direction == "incoming":
            cypher = "MATCH (rn:RelationshipNode) WHERE rn.target = $id RETURN rn"
        else:
            cypher = (
                "MATCH (rn:RelationshipNode) "
                "WHERE rn.source = $id OR rn.target = $id RETURN rn"
            )
        with self.driver.session(database=self.database) as session:
            recs = session.run(cypher, id=entity_id).data()
        return [_record_to_rel(dict(r["rn"])) for r in recs]

    def children_of(self, entity_id: str) -> list[Entity]:
        with self.driver.session(database=self.database) as session:
            recs = session.run(
                "MATCH (e:Entity { parent: $id }) RETURN e", id=entity_id
            ).data()
        return [_record_to_entity(dict(r["e"])) for r in recs]

    # --- Fragments ----------------------------------------------------

    def upsert_fragment(self, fragment: DocFragment) -> DocFragment:
        for s in fragment.subjects:
            if not self.has_entity(s.entity):
                raise RepositoryError(
                    f"fragment {fragment.id} references missing entity {s.entity}"
                )
        for r in fragment.relations:
            if not self.has_relationship(r.rel):
                raise RepositoryError(
                    f"fragment {fragment.id} references missing relationship {r.rel}"
                )
        rec = _fragment_to_record(fragment)
        with self.driver.session(database=self.database) as session:
            session.run(
                """
                MERGE (f:Fragment { id: $id })
                SET f.doc_id = $doc_id,
                    f.title = $title,
                    f.body = $body,
                    f.format = $format,
                    f.subjects = $subjects,
                    f.relations = $relations,
                    f.tags = $tags,
                    f.coverage = $coverage,
                    f.provenance = $provenance
                """,
                **rec,
            )
            # Re-link anchors
            session.run(
                "MATCH (f:Fragment { id: $id })-[a:ANCHORS_ENTITY]->() DELETE a",
                id=fragment.id,
            )
            session.run(
                "MATCH (f:Fragment { id: $id })-[a:ANCHORS_REL]->() DELETE a",
                id=fragment.id,
            )
            for s in fragment.subjects:
                session.run(
                    """
                    MATCH (f:Fragment { id: $fid }), (e:Entity { id: $eid })
                    MERGE (f)-[:ANCHORS_ENTITY]->(e)
                    """,
                    fid=fragment.id,
                    eid=s.entity,
                )
            for r in fragment.relations:
                session.run(
                    """
                    MATCH (f:Fragment { id: $fid }), (rn:RelationshipNode { id: $rid })
                    MERGE (f)-[:ANCHORS_REL]->(rn)
                    """,
                    fid=fragment.id,
                    rid=r.rel,
                )
        return fragment

    def get_fragment(self, fragment_id: str) -> DocFragment:
        with self.driver.session(database=self.database) as session:
            r = session.run(
                "MATCH (f:Fragment { id: $id }) RETURN f", id=fragment_id
            ).single()
        if r is None:
            raise FragmentNotFoundError(fragment_id)
        return _record_to_fragment(dict(r["f"]))

    def has_fragment(self, fragment_id: str) -> bool:
        with self.driver.session(database=self.database) as session:
            r = session.run(
                "MATCH (f:Fragment { id: $id }) RETURN count(f) AS n",
                id=fragment_id,
            ).single()
        return bool(r and r["n"] > 0)

    def list_fragments(self) -> list[DocFragment]:
        with self.driver.session(database=self.database) as session:
            recs = session.run("MATCH (f:Fragment) RETURN f").data()
        return [_record_to_fragment(dict(r["f"])) for r in recs]

    def fragments_by_subject(self, entity_id: str) -> list[DocFragment]:
        with self.driver.session(database=self.database) as session:
            recs = session.run(
                """
                MATCH (f:Fragment)-[:ANCHORS_ENTITY]->(:Entity { id: $id })
                RETURN f
                """,
                id=entity_id,
            ).data()
        return [_record_to_fragment(dict(r["f"])) for r in recs]

    def fragments_by_relation(self, rel_id: str) -> list[DocFragment]:
        with self.driver.session(database=self.database) as session:
            recs = session.run(
                """
                MATCH (f:Fragment)-[:ANCHORS_REL]->(:RelationshipNode { id: $id })
                RETURN f
                """,
                id=rel_id,
            ).data()
        return [_record_to_fragment(dict(r["f"])) for r in recs]

    def fragments_by_tag(self, tag: str) -> list[DocFragment]:
        with self.driver.session(database=self.database) as session:
            recs = session.run(
                "MATCH (f:Fragment) WHERE $tag IN f.tags RETURN f", tag=tag
            ).data()
        return [_record_to_fragment(dict(r["f"])) for r in recs]

    def delete_fragment(self, fragment_id: str) -> None:
        if not self.has_fragment(fragment_id):
            raise FragmentNotFoundError(fragment_id)
        with self.driver.session(database=self.database) as session:
            session.run(
                "MATCH (f:Fragment { id: $id }) DETACH DELETE f", id=fragment_id
            )

    # --- Presets -------------------------------------------------------

    def upsert_preset(self, preset: ViewPreset) -> ViewPreset:
        if not self.has_entity(preset.owner):
            raise RepositoryError(f"preset owner {preset.owner!r} does not exist")
        if not self.has_entity(preset.focus):
            raise RepositoryError(f"preset focus {preset.focus!r} does not exist")
        rec = _preset_to_record(preset)
        with self.driver.session(database=self.database) as session:
            session.run(
                """
                MERGE (p:Preset { id: $id })
                ON CREATE SET p.created_at = $created_at
                SET p.name = $name,
                    p.owner = $owner,
                    p.shared_with = $shared_with,
                    p.focus = $focus,
                    p.zoom = $zoom,
                    p.lenses = $lenses,
                    p.radius = $radius,
                    p.filters = $filters,
                    p.updated_at = $updated_at
                """,
                **rec,
            )
        return preset

    def get_preset(self, preset_id: str) -> ViewPreset:
        with self.driver.session(database=self.database) as session:
            r = session.run(
                "MATCH (p:Preset { id: $id }) RETURN p", id=preset_id
            ).single()
        if r is None:
            raise PresetNotFoundError(preset_id)
        return _record_to_preset(dict(r["p"]))

    def list_presets(self) -> list[ViewPreset]:
        with self.driver.session(database=self.database) as session:
            recs = session.run("MATCH (p:Preset) RETURN p").data()
        return [_record_to_preset(dict(r["p"])) for r in recs]

    def delete_preset(self, preset_id: str) -> None:
        with self.driver.session(database=self.database) as session:
            r = session.run(
                "MATCH (p:Preset { id: $id }) DETACH DELETE p RETURN count(p) AS n",
                id=preset_id,
            ).single()
        if not r or r["n"] == 0:
            raise PresetNotFoundError(preset_id)

    # --- Bulk ----------------------------------------------------------

    def upsert_entities(self, entities) -> None:
        for e in entities:
            self.upsert_entity(e)

    def upsert_relationships(self, rels) -> None:
        for r in rels:
            self.upsert_relationship(r)

    def upsert_fragments(self, frags) -> None:
        for f in frags:
            self.upsert_fragment(f)
