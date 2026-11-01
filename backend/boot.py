"""Single-process deploy entry point: migrate, optionally seed, serve API and React."""

import os
import subprocess
import sys
import uvicorn


def main():
    subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], check=True)
    if os.environ.get('SEED_DEMO', '').lower() == 'true':
        from backend.seed import seed

        seed()
    uvicorn.run(
        'backend.main:app', host='0.0.0.0', port=int(os.environ.get('PORT', '8000')), workers=1
    )


if __name__ == '__main__':
    main()
