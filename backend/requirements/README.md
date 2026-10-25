# Dependency locks

Runtime and development requirements live here. Install from the repository root with `python -m pip install -r backend/requirements/runtime.txt`; use development.txt for tests. Hashes and pinned versions are retained. Private configuration stays in the ignored root .env.

Update shared runtime dependencies in both `runtime.in` and the root `pyproject.toml`. Regenerate the hashed runtime/development requirements and root `uv.lock` together. The repository check rejects a root/backend version mismatch, an out-of-date Vercel lock, or development packages that differ from the runtime lock. A backend-only dependency pull request is not sufficient to update the deployed Vercel environment.
