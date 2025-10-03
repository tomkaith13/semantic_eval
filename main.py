import os
import json
from typing import Any, Dict
from uuid import uuid4
from dotenv import load_dotenv
from ground_truth.gt import ground_truth_samples

import requests

from similarity_scorer.score import score_similarity

# Load environment variables from a .env file if present
load_dotenv()


def _build_url(path: str) -> str:
    """Construct a full URL from API_BASE_URL and a path starting with '/'.

    Falls back to http://localhost:8080 if API_BASE_URL not provided.
    Ensures no duplicate slashes.
    """
    base = os.getenv("API_BASE_URL", "http://localhost:8080").strip().rstrip("/")
    if not base:
        base = "http://localhost:8080"  # final safety fallback
    if not path.startswith("/"):
        path = "/" + path
    return f"{base}{path}"


SESSIONS_URL = _build_url("/v1/sessions")
RUN_URL = _build_url("/v1/run")


def create_session(payload: Dict[str, Any] | None = None) -> Dict[str, Any] | None:
    """Call the sessions API equivalent to provided curl.

    curl reference (domain now driven by API_BASE_URL env var):
    curl --location '${API_BASE_URL:-http://localhost:8080}/v1/sessions' \
         --header 'Content-Type: application/json' \
         --header 'Authorization: Bearer <TOKEN>' \
         --data '{}'
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
) -> Dict[str, Any] | list[Dict[str, Any]] | None:
    """Call the /v1/run endpoint replicating provided curl.

    curl reference (domain now driven by API_BASE_URL env var):
    curl --location '${API_BASE_URL:-http://localhost:8080}/v1/run' \\
         --header 'X-Stream: true' \\
         --header 'Content-Type: application/json' \\
         --header 'Authorization: Bearer <TOKEN>' \\
         --data '{"id":"<run_uuid>","session_id":"<session_uuid>","message":"..."}'
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
        # Auto-generate a GUID for this run distinct from the session_id
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
            # Proper SSE parsing: events separated by blank lines, with lines like:
            # event: <type>
            # id: <id>
            # data: {"json":true}
            events: list[Dict[str, Any]] = []
            current: Dict[str, Any] = {}

            def finalize_current():
                nonlocal current
                if not current:
                    return
                # Attempt JSON decode on data field if it's a JSON object/string

                preview = current.get("data")
                if preview == "[DONE]":
                    return

                preview_json = json.loads(preview) if preview else None
                if not preview_json:
                    return

                preview_str = str(preview_json)
                print(f"[run][event] {str(preview_str)[:90]} ...")
                events.append(current)
                current = {}

            for raw_line in resp.iter_lines(decode_unicode=True):
                if raw_line is None:
                    continue
                line = raw_line.rstrip("\n")
                if not line:  # Blank line ends an event
                    finalize_current()
                    continue
                if line.startswith(":"):  # Comment line in SSE; skip
                    continue
                if ":" in line:
                    field, value = line.split(":", 1)
                    current[field.strip()] = value.lstrip()
                else:
                    # Continuation line for data
                    current["data"] = (current.get("data", "") + "\n" + line).strip()

            # Final flush if stream ended without trailing blank line
            finalize_current()
            return events
        else:
            # Non-stream JSON
            try:
                return resp.json()
            except json.JSONDecodeError:
                return {"raw": resp.text[:500]}
    except requests.RequestException as exc:
        print(f"[run] Request failed: {exc}")
        return None


def parse_last_run_event(run_events: list[Dict[str, Any]] | None) -> None:
    """Parse and print details from the last run event in a factored helper.

    Extracts nested message.parts[].text if present.
    """
    if not run_events or not isinstance(run_events, list):
        print("No run events to parse.")
        return None
    last = run_events[-1]
    data = last.get("data")
    print("*" * 40)
    print(f"Last raw data: {data!r}")
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
    for idx, part in enumerate(parts):
        if isinstance(part, dict):
            txt = part.get("text")
            if isinstance(txt, str):
                # print(f"Part[{idx}] text: {txt}")
                return txt  # Return the first text found
            else:
                print(f"Part[{idx}] has no text field or not a string.")
                return None
        else:
            # print(f"Part[{idx}] is not a dict: {part!r}")
            return None


def main():
    print("Hello from sentence-sim!")
    print(f"Using API_BASE_URL: {os.getenv('API_BASE_URL', 'http://localhost:8080')}")

    # Call sessions API (will skip if SESSION_API_TOKEN is not set)
    session_resp = create_session()
    if session_resp is not None:
        print("Created/queried session response snippet:", str(session_resp)[:200])

    session_id = session_resp.get("id") if session_resp else None
    if not session_id:
        print("No session ID returned; skipping /run call.")
        return

    # Example run call

    for example in ground_truth_samples:
        question = example["question"]
        print("Example from GT:", question)

        run_events = run_message(
            message=question,
            session_id=session_id,
            run_id=None,  # Could supply a UUID string
            stream=True,
        )

        response = parse_last_run_event(run_events)
        print(f"Extracted text from last run event: {response!r}")

        # Demonstrate similarity scoring so the pipeline still produces a value
        print("*" * 100)
        print("Scoring similarity against ground truth answer...")
        score = score_similarity(
            response,
            example["answer"],
        )
        print(f"Computed similarity score: {score:.4f}")
        print("*" * 100)

    # Demonstrate similarity scoring so the pipeline still produces a value
    # score = score_similarity(
    #     "The contributions in your LSA is around $42.00",
    #     "42 dollars is your LSA contribution",
    # )
    # print(f"Computed similarity score: {score:.4f}")


if __name__ == "__main__":
    main()
