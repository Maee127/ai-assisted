"""Tests for the one-interaction classification command."""

import json
from unittest.mock import Mock, patch

import pytest

from lead_pipeline.domain.enums import ClassificationLabel
from lead_pipeline.domain.identifiers import InstagramEventId
from lead_pipeline.persistence.exceptions import InteractionNotFoundError
from lead_pipeline.worker.cli import main


def build_runtime() -> Mock:
    runtime = Mock()
    result = Mock()
    result.outcome.final_result.label = ClassificationLabel.SALES_LEAD
    result.outcome.was_escalated = True
    result.outcome.is_unresolved = False
    runtime.job.execute.return_value = result
    return runtime


def test_command_classifies_event_and_prints_safe_summary(
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime = build_runtime()

    with patch(
        "lead_pipeline.worker.cli.create_classification_runtime",
        return_value=runtime,
    ):
        exit_code = main(["event-1"])

    assert exit_code == 0
    runtime.job.execute.assert_called_once_with(
        InstagramEventId("event-1"),
    )
    runtime.engine.dispose.assert_called_once_with()

    captured = capsys.readouterr()
    assert json.loads(captured.out) == {
        "is_unresolved": False,
        "label": "SALES_LEAD",
        "status": "COMPLETED",
        "was_escalated": True,
    }
    assert captured.err == ""
    assert "event-1" not in captured.out


def test_missing_event_returns_safe_not_found_status(
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime = build_runtime()
    runtime.job.execute.side_effect = InteractionNotFoundError(
        "interaction was not found"
    )

    with patch(
        "lead_pipeline.worker.cli.create_classification_runtime",
        return_value=runtime,
    ):
        exit_code = main(["private-event-id"])

    assert exit_code == 2
    runtime.engine.dispose.assert_called_once_with()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "interaction was not found\n"
    assert "private-event-id" not in captured.err


def test_unexpected_failure_propagates_after_resources_are_closed() -> None:
    runtime = build_runtime()
    runtime.job.execute.side_effect = RuntimeError("provider unavailable")

    with (
        patch(
            "lead_pipeline.worker.cli.create_classification_runtime",
            return_value=runtime,
        ),
        pytest.raises(
            RuntimeError,
            match="provider unavailable",
        ),
    ):
        main(["event-1"])

    runtime.engine.dispose.assert_called_once_with()
