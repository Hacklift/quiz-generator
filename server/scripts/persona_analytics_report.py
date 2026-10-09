"""Print signup and quiz-generation counts grouped by event-time persona."""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, time, timezone

from server.app.analytics.reporting import aggregate_persona_events
from server.app.db.core.connection import (
    get_auth_events_collection,
    get_product_events_collection,
)


def parse_date(value: str) -> datetime:
    try:
        return datetime.combine(datetime.strptime(value, "%Y-%m-%d").date(), time.min, timezone.utc)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected YYYY-MM-DD") from exc


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="date_from", type=parse_date, required=True)
    parser.add_argument("--to", dest="date_to", type=parse_date, required=True)
    parser.add_argument("--granularity", choices=("day", "week", "month"), default="day")
    args = parser.parse_args()
    if args.date_to <= args.date_from:
        parser.error("--to must be after --from (the end date is exclusive)")

    date_filter = {"$gte": args.date_from, "$lt": args.date_to}
    auth_events = await get_auth_events_collection().find(
        {
            "event_type": "register",
            "status": "success",
            "created_at": date_filter,
        }
    ).to_list(length=None)
    product_events = await get_product_events_collection().find(
        {"event_type": "quiz_generated", "created_at": date_filter}
    ).to_list(length=None)
    print(json.dumps(aggregate_persona_events(auth_events, product_events, args.granularity), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
