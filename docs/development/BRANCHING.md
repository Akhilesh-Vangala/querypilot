# Repository workflow

`main` contains verified shared work. Create a short-lived `feat/`, `fix/`, `docs/` or `chore/` branch from synchronized main and open a pull request. Required checks are **Backend and policy**, **Frontend build**, and **Containers and PostgreSQL**. Squash merge only after the exact head passes all required checks and review conversations are resolved. Administrator bypass, force pushes and main deletion are disallowed.

The solo-maintainer workflow requires zero independent approving reviews; add reviewers when there is an actual collaborator. Preserve the original history. Automatically delete merged task branches; synchronize local main and remove only the task-owned branch after verifying tree equivalence. No empty long-lived development/release branches. Tags require a scoped, verified release; a public synthetic demo is not a production certification.

Dependabot groups `react`, `react-dom`, `@types/react` and `@types/react-dom` together for both version and security updates. Review their peer requirements as one compatibility boundary, including runtime and development dependencies. Validate with `npm ci`, `npm ls --all` and `npm run build` in `frontend/`; do not bypass conflicts with `--force` or `--legacy-peer-deps`. Major upgrades still require the normal CI and browser checks.

Python dependency releases must keep `backend/requirements/runtime.in`, its hashed runtime/development locks, root `pyproject.toml` and `uv.lock` consistent for shared runtime packages. Dependabot's backend directory does not update the root Vercel manifest automatically. Review both environments before merging; a green backend check alone does not establish that Vercel will install the same versions.

Frontend package changes also change the source identity of the recorded demonstrations. Refresh the actual recordings and their manifests after validating the updated application. Keep the existing provenance checks; changing stored hashes without recapturing the demonstration does not establish that the recording shows the new runtime.

Supply an explicit, descriptive title when squash merging, for example `gh pr merge --squash --subject "docs(deps): document coordinated dependency releases"`. Keep automatic pull-request reference suffixes out of the resulting commit title. Required checks, conversation resolution and administrator enforcement still apply.
