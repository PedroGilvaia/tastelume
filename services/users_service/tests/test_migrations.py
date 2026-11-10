import os
import subprocess
import sys
from pathlib import Path


def test_migration_matches_models(tmp_path):
    """A migração Alembic tem de produzir exatamente o esquema dos modelos."""
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from sqlalchemy import create_engine

    from app.database import Base

    db_file = tmp_path / "mig.db"
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_file}"}
    res = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=root, env=env,
                         capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    engine = create_engine(f"sqlite:///{db_file}")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == [], diff
