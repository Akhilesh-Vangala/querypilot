"""A passing backend lock must not conceal a different deployed dependency."""

import importlib.util
from pathlib import Path

import pytest


SPEC = importlib.util.spec_from_file_location(
    "repository_check", Path(__file__).resolve().parents[3] / "scripts/checks/check_repository.py"
)
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


@pytest.fixture
def manifests(tmp_path):
    (tmp_path / "backend/requirements").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "example"\ndependencies = ["Some_Package[extra]==1.0"]\n'
    )
    (tmp_path / "uv.lock").write_text(
        '[[package]]\nname = "example"\ndependencies = [{name = "some-package"}]\n'
        '[[package]]\nname = "some-package"\nversion = "1.0"\n'
    )
    for name in ("runtime", "development"):
        (tmp_path / f"backend/requirements/{name}.txt").write_text("some-package==1.0\n")
    return tmp_path


def test_matching_runtime_test_and_vercel_versions(manifests):
    CHECK.check_dependency_parity(manifests)


def test_backend_only_update_cannot_pass_with_an_old_vercel_pin(manifests):
    for name in ("runtime", "development"):
        (manifests / f"backend/requirements/{name}.txt").write_text("some-package==2.0\n")
    with pytest.raises(AssertionError, match="Backend/Vercel version mismatch"):
        CHECK.check_dependency_parity(manifests)


def test_root_update_requires_a_matching_deployment_lock(manifests):
    path = manifests / "uv.lock"
    path.write_text(path.read_text().replace('version = "1.0"', 'version = "2.0"'))
    with pytest.raises(AssertionError, match="Stale deployment uv.lock"):
        CHECK.check_dependency_parity(manifests)


def test_test_environment_cannot_hide_a_different_runtime_version(manifests):
    (manifests / "backend/requirements/development.txt").write_text("some-package==2.0\n")
    with pytest.raises(AssertionError, match="Runtime/development version mismatch"):
        CHECK.check_dependency_parity(manifests)
