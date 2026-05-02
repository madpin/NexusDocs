"""Closed enums for kinds, types, lenses, protocols, modes, and source types."""

from enum import StrEnum


class Kind(StrEnum):
    """Entity kinds. See docs/entities/README.md."""

    company = "company"
    division = "division"
    tribe = "tribe"
    team = "team"
    person = "person"

    system = "system"
    service = "service"
    component = "component"
    cls = "class"
    function = "function"

    database = "database"
    kafka_cluster = "kafka_cluster"
    kafka_topic = "kafka_topic"
    api_endpoint = "api_endpoint"
    queue = "queue"
    cache = "cache"

    document = "document"
    doc_fragment = "doc_fragment"


# Allowed parent.kind for each entity kind. See docs/schemas/entity.md.
ALLOWED_PARENT_KINDS: dict[Kind, frozenset[Kind]] = {
    Kind.company: frozenset(),
    Kind.division: frozenset({Kind.company}),
    Kind.tribe: frozenset({Kind.division}),
    Kind.team: frozenset({Kind.tribe, Kind.division}),
    Kind.person: frozenset(),  # person uses member_of, not parent
    Kind.system: frozenset(),
    Kind.service: frozenset({Kind.system}),
    Kind.component: frozenset({Kind.service}),
    Kind.cls: frozenset({Kind.component, Kind.service}),
    Kind.function: frozenset({Kind.cls, Kind.component, Kind.service}),
    Kind.database: frozenset(),
    Kind.kafka_cluster: frozenset(),
    Kind.kafka_topic: frozenset({Kind.kafka_cluster}),
    Kind.api_endpoint: frozenset({Kind.service}),
    Kind.queue: frozenset(),
    Kind.cache: frozenset(),
    Kind.document: frozenset(),
    Kind.doc_fragment: frozenset(),
}


class RelationshipType(StrEnum):
    """Relationship types. See docs/relationships/README.md."""

    # Organizational
    belongs_to = "belongs_to"
    owns = "owns"
    leads = "leads"
    member_of = "member_of"
    reports_to = "reports_to"

    # Technical
    depends_on = "depends_on"
    calls_api = "calls_api"
    provides_api = "provides_api"
    extends = "extends"
    implements = "implements"

    # Data flow
    publishes_to = "publishes_to"
    consumes_from = "consumes_from"
    reads_from = "reads_from"
    writes_to = "writes_to"
    streams_to = "streams_to"

    # Documentation
    describes = "describes"
    references = "references"
    supersedes = "supersedes"


# Categorize relationship types for queries / lens hints.
ORGANIZATIONAL_TYPES = frozenset(
    {
        RelationshipType.belongs_to,
        RelationshipType.owns,
        RelationshipType.leads,
        RelationshipType.member_of,
        RelationshipType.reports_to,
    }
)

TECHNICAL_TYPES = frozenset(
    {
        RelationshipType.depends_on,
        RelationshipType.calls_api,
        RelationshipType.provides_api,
        RelationshipType.extends,
        RelationshipType.implements,
    }
)

DATA_FLOW_TYPES = frozenset(
    {
        RelationshipType.publishes_to,
        RelationshipType.consumes_from,
        RelationshipType.reads_from,
        RelationshipType.writes_to,
        RelationshipType.streams_to,
    }
)

DOCUMENTATION_TYPES = frozenset(
    {
        RelationshipType.describes,
        RelationshipType.references,
        RelationshipType.supersedes,
    }
)


class Lens(StrEnum):
    """Built-in lenses. Organizations may add custom strings; this enum lists the defaults."""

    product = "product"
    technical = "technical"
    operations = "operations"
    debug = "debug"
    client = "client"
    onboarding = "onboarding"


class Protocol(StrEnum):
    """Wire protocols / storage engines. Open enum stored as string."""

    rest = "rest"
    grpc = "grpc"
    graphql = "graphql"
    websocket = "websocket"

    kafka = "kafka"
    pubsub = "pubsub"
    sqs = "sqs"
    sns = "sns"
    rabbitmq = "rabbitmq"
    nats = "nats"

    postgres = "postgres"
    mysql = "mysql"
    mongodb = "mongodb"
    dynamodb = "dynamodb"
    redis = "redis"
    memcached = "memcached"
    s3 = "s3"
    bigtable = "bigtable"
    cassandra = "cassandra"


class Mode(StrEnum):
    """Edge timing semantics."""

    sync = "sync"
    async_ = "async"
    batch = "batch"


class SourceType(StrEnum):
    """Provenance source types."""

    readme = "readme"
    adr = "adr"
    runbook = "runbook"
    ticket = "ticket"
    api_spec = "api_spec"
    config_file = "config_file"
    confluence = "confluence"
    backstage = "backstage"
    openapi = "openapi"
    proto = "proto"
    llm_generated = "llm_generated"
    manual = "manual"


class Granularity(StrEnum):
    """Author intent for fragment subject scale."""

    company = "company"
    division = "division"
    team = "team"
    system = "system"
    service = "service"
    component = "component"
    code = "code"


class GeneratedBy(StrEnum):
    human = "human"
    llm = "llm"
    hybrid = "hybrid"
