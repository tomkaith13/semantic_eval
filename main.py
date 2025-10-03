import os
import json
from typing import Any, Dict
from dotenv import load_dotenv

import requests

from similarity_scorer.score import score_similarity


SESSIONS_URL = "http://localhost:8080/v1/sessions"
load_dotenv()  # Load environment variables from a .env file if present

def create_session(payload: Dict[str, Any] | None = None) -> Dict[str, Any] | None:
    """Call the sessions API equivalent to provided curl.

    curl reference:
    curl --location 'http://localhost:8080/v1/sessions' \
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


def main():
    print("Hello from sentence-sim!")

    # Call sessions API (will skip if SESSION_API_TOKEN is not set)
    session_resp = create_session()
    if session_resp is not None:
        print("Created/queried session response snippet:", str(session_resp)[:200])
    
    session_id =session_resp.get("id", None)
    if not session_id:
        print("No session ID returned; skipping /run call.")
        return
    
    

    # Placeholder: call /run endpoint next (not yet implemented)

    # score = score_similarity(
    #     "The contributions in your LSA is around $42.00",
    #     "42 dollars is your LSA contribution",
    # )
    # print(f"Computed similarity score: {score:.4f}")


if __name__ == "__main__":
    main()
