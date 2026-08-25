"""Command-line entry point for classifying one persisted interaction."""

import argparse
import json
import sys
from collections.abc import Sequence

from lead_pipeline.domain.enums import ProcessingStatus
from lead_pipeline.domain.identifiers import InstagramEventId
from lead_pipeline.persistence.exceptions import InteractionNotFoundError
from lead_pipeline.worker.runtime import create_classification_runtime


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Classify one persisted Instagram interaction.",
    )
    parser.add_argument(
        "event_id",
        help="Stable Instagram event identifier to classify.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """Classify one event and print only privacy-safe outcome metadata."""

    arguments = _build_parser().parse_args(argv)
    runtime = create_classification_runtime()

    try:
        try:
            result = runtime.job.execute(
                InstagramEventId(arguments.event_id),
            )
        except InteractionNotFoundError:
            print(
                "interaction was not found",
                file=sys.stderr,
            )
            return 2

        summary = {
            "is_unresolved": result.outcome.is_unresolved,
            "label": result.outcome.final_result.label.value,
            "status": ProcessingStatus.COMPLETED.value,
            "was_escalated": result.outcome.was_escalated,
        }
        print(
            json.dumps(
                summary,
                sort_keys=True,
            )
        )
        return 0
    finally:
        runtime.engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
