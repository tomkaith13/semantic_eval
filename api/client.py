import os
import json
from typing import Any, Dict, List
from uuid import uuid4
import requests

__all__ = ["create_session", "run_message"]


def _build_url(path: str) -> str:
    """Construct a full URL from API_BASE_URL and a path starting with '/'."""
    base = os.getenv("API_BASE_URL", "http://localhost:8080").strip().rstrip("/")
    if not base:
        base = "http://localhost:8080"  # safety fallback
    if not path.startswith("/"):
        path = "/" + path
    return f"{base}{path}"


SESSIONS_URL = _build_url("/v1/sessions")
RUN_URL = _build_url("/v1/run")


def create_session(payload: Dict[str, Any] | None = None) -> Dict[str, Any] | None:
    """Call the sessions API.

    Returns parsed JSON (dict) or None on failure / missing token.
    """
    token = os.getenv("BEARER_TOKEN", "").strip()
    if not token:
        print("[sessions] BEARER_TOKEN not set; skipping API call.")
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    data: Dict[str, Any] = payload or {}

    try:
        resp = requests.post(SESSIONS_URL, headers=headers, json=data, timeout=10)
        print(f"[sessions] status={resp.status_code}")
        if resp.headers.get("Content-Type", "").startswith("application/json"):
            try:
                body = resp.json()
            except json.JSONDecodeError:
                print("[sessions] Failed to decode JSON response")
                body = {"raw": resp.text[:500]}
        else:
            body = {"raw": resp.text[:500]}

        if not resp.ok:
            print("[sessions] Non-2xx response:", body)
        return body
    except requests.RequestException as exc:
        print(f"[sessions] Request failed: {exc}")
        return None


def run_message(
    message: str,
    session_id: str,
    run_id: str | None = None,
    stream: bool = True,
    timeout: int = 30,
) -> List[Dict[str, Any]] | None:
    """Call the /v1/run endpoint.

    Returns list of streamed events (if stream=True) or dict / None.
    """
    token = os.getenv("BEARER_TOKEN", "").strip()
    if not token:
        print("[run] BEARER_TOKEN not set; skipping API call.")
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    if stream:
        headers["X-Stream"] = "true"

    payload: Dict[str, Any] = {
        "session_id": session_id,
        "message": message,
    }
    if run_id:
        payload["id"] = run_id
    else:
        run_id = str(uuid4())
        payload["id"] = run_id

    print(f"[run] using run id {run_id}")

    try:
        resp = requests.post(
            RUN_URL,
            headers=headers,
            json=payload,
            timeout=timeout,
            stream=stream,
        )
        print(f"[run] status={resp.status_code}")
        if not resp.ok:
            print("[run] Non-2xx status; body preview:", resp.text[:300])
        if stream:
            events: list[Dict[str, Any]] = []
            current: Dict[str, Any] = {}

            def finalize_current():
                nonlocal current
                if not current:
                    return
                preview = current.get("data")
                if preview == "[DONE]":
                    print("[run][event] [DONE]")
                    return
                try:
                    preview_json = json.loads(preview) if preview else None
                except json.JSONDecodeError:
                    preview_json = None
                if not preview_json:
                    return
                preview_str = str(preview_json)
                print(f"[run][event] {preview_str[:90]} ...")
                events.append(current)
                current = {}

            for raw_line in resp.iter_lines(decode_unicode=True):
                if raw_line is None:
                    continue
                line = raw_line.rstrip("\n")
                if not line:
                    finalize_current()
                    continue
                if line.startswith(":"):
                    continue
                if ":" in line:
                    field, value = line.split(":", 1)
                    current[field.strip()] = value.lstrip()
                else:
                    current["data"] = (current.get("data", "") + "\n" + line).strip()
            finalize_current()
            return events
        else:
            try:
                return [resp.json()]
            except json.JSONDecodeError:
                return [{"raw": resp.text[:500]}]
    except requests.RequestException as exc:
        print(f"[run] Request failed: {exc}")
        return None
