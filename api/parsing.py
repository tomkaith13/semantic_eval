import json
from typing import Optional, Any

__all__ = ["parse_last_run_event"]


def parse_last_run_event(run_events: list[dict[str, Any]] | None) -> Optional[str]:
    """Extract first text part from the last run event.

    Returns the extracted text or None.
    """
    if not run_events or not isinstance(run_events, list):
        print("No run events to parse.")
        return None
    last = run_events[-1]
    if not isinstance(last, dict):
        print("Last run event is not a dict.")
        return None
    data = last.get("data")
    print("*" * 40)
    if not isinstance(data, str):
        print("Data is not a string; cannot parse as JSON.")
        return None
    try:
        data_json = json.loads(data)
    except json.JSONDecodeError:
        print("Data is not valid JSON.")
        return None
    print(f"Parsed JSON keys: {list(data_json.keys())}")
    message_obj = data_json.get("message")
    if not isinstance(message_obj, dict):
        print("No 'message' object found.")
        return None
    parts = message_obj.get("parts", [])
    if not isinstance(parts, list):
        print("'message.parts' not a list.")
        return None
    for part in parts:
        if isinstance(part, dict):
            txt = part.get("text")
            if isinstance(txt, str):
                return txt
    return None
