from sqlalchemy import create_engine, inspect

from app.models.lifecycle import (
    ProductionIncidentModel,
    ProductionObservationModel,
    RequirementTraceModel,
    ensure_lifecycle_tables,
)


def test_lifecycle_tables_bootstrap_is_idempotent():
    engine = create_engine("sqlite:///:memory:")
    ensure_lifecycle_tables(engine)
    ensure_lifecycle_tables(engine)

    names = set(inspect(engine).get_table_names())
    assert RequirementTraceModel.__tablename__ in names
    assert ProductionObservationModel.__tablename__ in names
    assert ProductionIncidentModel.__tablename__ in names


def test_lifecycle_table_schema_contains_revision_binding():
    assert RequirementTraceModel.__table__.c.source_sha is not None
    assert ProductionObservationModel.__table__.c.serving_sha is not None
    assert ProductionIncidentModel.__table__.c.source_sha is not None
