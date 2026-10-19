"""Offline guardrails for how the portals are protected: an ingress IP allow list, no Entra app registration."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def read(*parts: str) -> str:
    return (ROOT.joinpath(*parts)).read_text(encoding="utf-8")


def test_container_app_ingress_fails_closed_when_no_range_is_allowed() -> None:
    module = read("infra", "modules", "container-app.bicep")
    assert "ipSecurityRestrictions: external ? ipSecurityRestrictions : null" in module
    # An empty restriction list would open the app to the internet, so a placeholder range stands in.
    assert "empty(allowedIpRanges) ? [ '192.0.2.1/32' ] : allowedIpRanges" in module
    assert "action: 'Allow'" in module


def test_both_portals_use_the_allow_list_and_switch_the_old_auth_off() -> None:
    main = read("infra", "main.bicep")
    module = read("infra", "modules", "container-app.bicep")
    assert main.count("allowedIpRanges: allowedIpRangeList") == 2
    assert main.count("disableBuiltInAuth: true") == 2
    assert "enabled: false" in module
    assert "identityProviders" not in module


def test_no_entra_app_registration_is_configured() -> None:
    assert not (ROOT / "infra" / "scripts" / "setup-auth.ps1").exists()
    params = read("infra", "main.parameters.json")
    assert "authClientId" not in params and "AZURE_AUTH_CLIENT_ID" not in params
    assert "${ALLOWED_IP_RANGES=}" in params
    assert "authClientId" not in read("infra", "main.bicep")


def test_allowed_addresses_are_not_committed() -> None:
    ipv4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}/(?:\d{1,2})\b")
    allowed_documentation_ranges = {"192.0.2.1/32", "203.0.113.7/32"}
    for path in [
        ROOT / "infra" / "main.parameters.json",
        ROOT / "infra" / "main.bicep",
        ROOT / "infra" / "modules" / "container-app.bicep",
        ROOT / ".github" / "workflows" / "deploy-dev.yml",
        ROOT / "docs" / "deployment.md",
    ]:
        found = {r for r in ipv4.findall(path.read_text(encoding="utf-8")) if not r.startswith("10.")} - allowed_documentation_ranges
        assert not found, f"{path.name} contains an IP range: {found}"


def test_smoke_test_checks_the_allow_list_and_always_removes_its_rule() -> None:
    workflow = read(".github", "workflows", "deploy-dev.yml")
    assert '"403"' in workflow
    assert "--rule-name ci-smoke" in workflow
    assert "Remove the temporary runner access rule" in workflow
    cleanup = workflow[workflow.index("Remove the temporary runner access rule"):]
    assert "if: always()" in cleanup.split("run:")[0]
