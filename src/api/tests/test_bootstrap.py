"""Guardrails that keep the bootstrap script and the deployment guide in step with the Bicep templates."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = (ROOT / "infra" / "scripts" / "bootstrap.ps1").read_text(encoding="utf-8-sig")
GUIDE = (ROOT / "docs" / "deployment.md").read_text(encoding="utf-8")
GUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


def bicep_files() -> list[Path]:
    return sorted((ROOT / "infra").rglob("*.bicep"))


def test_every_role_the_template_assigns_is_allowed_by_the_bootstrap_condition_and_documented() -> None:
    roles: set[str] = set()
    for file in bicep_files():
        roles |= set(re.findall(rf"RoleId\s*=\s*'({GUID})'", file.read_text(encoding="utf-8")))
    assert len(roles) == 7
    in_script = set(re.findall(rf"'({GUID})' = '", SCRIPT))
    assert roles == in_script, "bootstrap.ps1 must allow exactly the roles the template assigns"
    for role in roles:
        assert role in GUIDE, f"docs/deployment.md does not document role {role}"


def test_bootstrap_checks_the_model_capacity_the_template_requests() -> None:
    main = (ROOT / "infra" / "main.bicep").read_text(encoding="utf-8")
    requested = re.findall(r"name: '([a-z0-9.\-]+)'\s+model: '[^']+'\s+version: '[^']+'\s+skuName: 'GlobalStandard'\s+capacity: (\d+)", main)
    assert {name for name, _ in requested} == {"gpt-5.4-mini", "gpt-5.4", "gpt-5.6-sol", "text-embedding-3-large"}
    in_script = dict(re.findall(r"Usage = 'OpenAI\.GlobalStandard\.([a-z0-9.\-]+)'; Capacity = (\d+)", SCRIPT))
    assert dict(requested) == in_script, "bootstrap.ps1 quota table must match agentModelDeployments and the other model parameters"
    for name, capacity in requested:
        assert f"{capacity}K" in GUIDE or name in GUIDE


def test_bootstrap_creates_both_github_subject_formats_and_never_embeds_an_environment() -> None:
    assert "repo:${Repository}:environment:$EnvironmentName" in SCRIPT
    assert "repo:$owner@$($repositoryIds.ownerId)/$name@$($repositoryIds.id):environment:$EnvironmentName" in SCRIPT
    assert not re.search(rf"(?<!-)\b{GUID}\b", SCRIPT.replace(re.search(rf"\$AssignableRoles = .*?\n}}", SCRIPT, re.S).group(0), "")), \
        "bootstrap.ps1 must not contain tenant, subscription or client IDs"


def test_guide_covers_the_whole_path_from_clone_to_teardown() -> None:
    for heading in ("## Deploy your own copy", "## Cost", "## Tear down", "## Troubleshooting", "## GitHub environment and deployment identity"):
        assert heading in GUIDE
    for expected in ("bootstrap.ps1", "setup-auth.ps1", "AZURE_AUTH_CLIENT_ID", "az cognitiveservices account purge", "Change visibility"):
        assert expected in GUIDE
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "bootstrap.ps1" in readme and "docs/deployment.md" in readme


def test_next_steps_do_not_suggest_azd_down_for_a_workflow_deployment() -> None:
    assert "azd down" not in SCRIPT
