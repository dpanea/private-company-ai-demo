from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_deployment_assets_exist() -> None:
    expected = [
        ROOT / "Dockerfile",
        ROOT / "docker-compose.yml",
        ROOT / "deploy" / "vllm" / "docker-compose.yml",
        ROOT / "deploy" / "vllm" / "README.md",
        ROOT / "deploy" / "caddy" / "Caddyfile.example",
        ROOT / "deploy" / "caddy" / "README.md",
        ROOT / "scripts" / "docker_entrypoint.sh",
        ROOT / "scripts" / "deploy_hetzner.sh",
    ]
    for path in expected:
        assert path.is_file()


def test_docker_entrypoint_bootstraps_once() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    entrypoint = (ROOT / "scripts" / "docker_entrypoint.sh").read_text(encoding="utf-8")

    assert 'ENTRYPOINT ["scripts/docker_entrypoint.sh"]' in dockerfile
    assert "uv run company_ai migrate" in entrypoint
    assert "uv run company_ai bootstrap-demo" in entrypoint


def test_readme_documents_production_boundaries() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Demo Scope vs. Production Scope" in readme
    assert "Incremental and event-driven ingestion sync." in readme
    assert "Multi-tenant isolation." in readme
    assert "Sovereign Deployment With vLLM" in readme
