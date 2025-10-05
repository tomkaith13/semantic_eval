import os
from dotenv import load_dotenv
from ground_truth.gt import ground_truth_samples
from similarity_scorer.score import score_similarity
from api import create_session, run_message, parse_last_run_event

# Load environment variables from a .env file if present
load_dotenv()

...


def run_examples() -> None:
    """Iterate ground truth examples and score model responses."""
    for example in ground_truth_samples:
        session_resp = create_session()
        if session_resp is not None:
            print("Created/queried session response snippet:", str(session_resp)[:200])
        session_id = session_resp.get("id") if session_resp else None
        if not session_id:
            print("No session ID returned; skipping /run call.")
            return
        question = example["question"]
        print("Example from GT:", question)
        run_events = run_message(
            message=question,
            session_id=session_id,
            run_id=None,
            stream=True,
        )
        response = parse_last_run_event(run_events)
        print("*" * 100)
        print("Scoring similarity against ground truth answer...")
        score = score_similarity(response, example["answer"])
        print(f"Computed similarity score: {score:.4f}")
        print("*" * 100)


def main() -> None:
    print("Hello from sentence-sim!")
    print(f"Using API_BASE_URL: {os.getenv('API_BASE_URL', 'http://localhost:8080')}")
    run_examples()


if __name__ == "__main__":
    main()
