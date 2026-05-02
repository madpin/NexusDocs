"""CLI smoke tests via typer.testing.CliRunner."""

import json

from typer.testing import CliRunner

from nexusdocs.cli.main import app

runner = CliRunner()


def test_apply_render_search(payments_yaml) -> None:
    result = runner.invoke(
        app,
        [
            "--state",
            str(payments_yaml),
            "--json",
            "render",
            "team.payments",
            "--zoom",
            "15",
            "--lens",
            "product",
            "--lens",
            "onboarding",
        ],
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    fragments = {f["id"] for f in payload["fragments"]}
    assert "docfrag.payments-team-overview" in fragments


def test_search_command(payments_yaml) -> None:
    result = runner.invoke(
        app,
        ["--state", str(payments_yaml), "--json", "search", "kafka"],
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    ids = {h["id"] for h in payload["hits"]}
    assert any("kafka" in i for i in ids)


def test_apply_command(payments_yaml, tmp_path) -> None:
    new_yaml = tmp_path / "extra.yaml"
    new_yaml.write_text(
        "apiVersion: nexusdocs/v1\n"
        "kind: Entity\n"
        "spec:\n"
        "  id: service.cli-added\n"
        "  type: service\n"
        "  name: CLI Added\n"
    )
    result = runner.invoke(app, ["--json", "apply", str(new_yaml)])
    assert result.exit_code == 0, result.stdout
    body = json.loads(result.stdout)
    assert any(a["id"] == "service.cli-added" for a in body["applied"])


def test_render_focus_not_found(payments_yaml) -> None:
    result = runner.invoke(
        app,
        ["--state", str(payments_yaml), "render", "service.does-not-exist"],
    )
    assert result.exit_code != 0
    assert "not found" in result.stdout
