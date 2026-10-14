# Repository workflow

`main` contains verified shared work. Create a short-lived `feat/`, `fix/`, `docs/` or `chore/` branch from synchronized main and open a pull request. Required checks are **Backend and policy**, **Frontend build**, and **Containers and PostgreSQL**. Squash merge only after the exact head passes all required checks and review conversations are resolved. Administrator bypass, force pushes and main deletion are disallowed.

The solo-maintainer workflow requires zero independent approving reviews; add reviewers when there is an actual collaborator. Preserve the original history. Automatically delete merged task branches; synchronize local main and remove only the task-owned branch after verifying tree equivalence. No empty long-lived development/release branches. Tags require a scoped, verified release; a public synthetic demo is not a production certification.
