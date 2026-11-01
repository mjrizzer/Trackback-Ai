import os
import subprocess
import sys
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_and_downgrade(tmp_path):
    path = tmp_path / 'migration.db'
    environment = {**os.environ, 'DATABASE_URL': f'sqlite:///{path}'}
    result = subprocess.run(
        [sys.executable, '-m', 'alembic', 'upgrade', 'head'],
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    engine = create_engine(f'sqlite:///{path}')
    names = inspect(engine).get_table_names()
    assert 'batch_material_usage' in names and 'agent_tool_calls' in names
    assert len(names) == 21  # 20 domain tables plus Alembic version.
    engine.dispose()
    result = subprocess.run(
        [sys.executable, '-m', 'alembic', 'downgrade', 'base'],
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
