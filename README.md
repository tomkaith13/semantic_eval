# sentence-sim

A minimal pipeline that:

1. (Optionally) creates a remote chat "session" via an HTTP API (`/v1/sessions`).
2. Streams a question to a model/runtime (`/v1/run`) and captures Server‑Sent Event (SSE) style chunks.
3. Extracts the final textual response from the streamed events.
4. Computes a semantic similarity score between the model's answer and a curated ground‑truth answer using a Sentence Transformer model (`all-mpnet-base-v2`).

> If the required bearer token is not set, the network calls are skipped so you can still experiment locally with the similarity scoring component.

---

## ✨ Features

- Lightweight, pure-Python entry point (`main.py`).
- SSE streaming parsing (basic event field parsing: `event`, `id`, `data`).
- Pluggable semantic similarity scoring powered by `sentence-transformers`.
- Easy ground truth examples in `ground_truth/gt.py`.
- Environment-driven configuration (token via `.env`).
- Modern dependency management (PEP 621 + `pyproject.toml`).

---

## 🗂 Project Structure

```
main.py                  # Orchestrates session, run, parse, score
ground_truth/gt.py       # Holds list[dict] with question & answer
similarity_scorer/score.py # Loads transformer model & scores cosine sim
pyproject.toml           # Project metadata & dependencies
README.md                # This file
```

---

## ✅ Requirements

- Python 3.13 (specified in `pyproject.toml`). Earlier versions may work but are not guaranteed.
- Internet access on first run (downloads the `all-mpnet-base-v2` model from Hugging Face).
- (Optional) A running backend exposing:
  - `POST http://localhost:8080/v1/sessions`
  - `POST http://localhost:8080/v1/run` (supports `X-Stream: true` for SSE-like streaming)
- A bearer token for the above API (set as `BEARER_TOKEN` in environment or `.env`).

---

## 🚀 Quick Start

### 1. Clone
```bash
git clone <your-fork-or-repo-url> sentence-sim
cd sentence-sim
```

### 2. (Option A) Install with uv (recommended if you have it)
```bash
uv sync
```
This will create/refresh a virtual environment and install dependencies from `pyproject.toml` + `uv.lock`.

### 2. (Option B) Install with pip + venv
```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

### 3. Configure Environment
Create a `.env` file (or export in your shell):
```
BEARER_TOKEN=your_api_token_here
```
If omitted, the script will print a message and skip the API portion (the similarity scoring loop will also be skipped because no session is established).

### 4. Run
```bash
uv run main.py
```

First execution will download the transformer model (~400MB). Subsequent runs are cached under `~/.cache/torch/sentence_transformers`.

Expected (abbreviated) output:
```
Hello from sentence-sim!
[sessions] status=200
Created/queried session response snippet: {... 'id': '...'}
Example from GT: How would you submit a claim?
[run] using run id ...
[run] status=200
[run][event] {...}
Extracted text from last run event: '...model answer...'
****************************************************************************************************
Scoring similarity against ground truth answer...
Similarity score between \n Obtained answer: '...model answer...' \n\nAND\n\n Golden answer: 'You can submit a claim in several ways...' \n\nis\n\n0.8734
Computed similarity score: 0.8734
```

---

## 🧪 Using the Similarity Scorer Directly

You can import and reuse the scorer without calling the remote APIs:

```python
from similarity_scorer.score import score_similarity

score = score_similarity(
	"A cat sits on the rug.",
	"A feline is resting on a mat.",
)
print(score)  # Float between -1 and 1 (cosine similarity)
```

The function signature:
```python
def score_similarity(result_ans: str, golden_ans: str) -> float:
	...
```

---

## 📘 Ground Truth Dataset

File: `ground_truth/gt.py`

Format:
```python
ground_truth_samples = [
	{
		"question": "How would you submit a claim?",
		"answer": "You can submit a claim in several ways ...",
	},
	# Add more samples here
]
```

Add more Q/A pairs to expand evaluation coverage. Each iteration in `main.py`:
1. Sends the ground truth question to the remote model.
2. Parses the final streamed event for a text response.
3. Computes similarity between model response and the ground truth `answer`.

---

## 🔌 Networking & Streaming Notes

`main.py` uses two endpoints:

- `/v1/sessions` — Initializes or retrieves a session. Returns JSON expected to include an `id`.
- `/v1/run` — Streams events if header `X-Stream: true` is set. The code performs a lightweight SSE parse collecting blocks separated by blank lines, capturing `data:` lines.

Parsed events are stored in-memory; the last event's `data` field is JSON-decoded. The first textual part inside `message.parts[].text` is returned.

If the backend uses a different event schema, adjust `parse_last_run_event` accordingly.

---

## ⚠️ Edge Cases & Behavior

- Missing `BEARER_TOKEN`: Session + run skipped; no similarity scores printed.
- Empty / malformed streamed `data`: Graceful messages are logged, function returns `None`.
- Model download failure: `sentence-transformers` raises an exception (not currently caught) — you may want to wrap `score_similarity` in a try/except for production use.
- Large ground truth list: Each item triggers a separate `/v1/run` request; consider rate limits.

---

## 🧩 Extending

Ideas:
- Swap model: change the `SentenceTransformer("all-mpnet-base-v2")` line in `similarity_scorer/score.py` (e.g. `all-MiniLM-L6-v2` for faster inference).
- Batch scoring: Encode all ground truth answers once, cache embeddings, then compare against each model response.
- Persist results: Write each (question, model_answer, ground_truth_answer, similarity) row to a CSV for later analysis.
- Add CLI interface (e.g., `argparse`) to run a single ad-hoc question.

---

## 🛠 Development

Install dev dependencies (adds `ruff`):
```bash
uv sync --group dev  # or: pip install ruff
```

Lint / format check:
```bash
ruff check .
```

(Optional) Auto-fix:
```bash
ruff check . --fix
```

---

## 🔐 Environment Variables

| Variable       | Purpose                               | Required |
|----------------|----------------------------------------|----------|
| `BEARER_TOKEN` | Auth token for remote API calls        | No (skips network if absent) |

You can export it instead of using `.env`:
```bash
export BEARER_TOKEN=your_api_token_here
```

---

## ❓ Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| "BEARER_TOKEN not set; skipping API call." | Env var missing | Add to `.env` or export it |
| Hang on first run | Model download in progress | Wait; check network connectivity |
| Low similarity score | Semantic divergence or short answer | Inspect model answer; consider better prompting |
| `ModuleNotFoundError: sentence_transformers` | Dependency not installed | Re-run install step |

---

## 📄 License

Currently no explicit license is declared. Add one (e.g., MIT, Apache-2.0) in the repository root if you plan to distribute.

---

## 🙌 Contributing

1. Fork & clone.
2. Create a branch: `git checkout -b feature/my-improvement`.
3. Make changes + run lint checks.
4. Submit a PR with a concise description & sample output.

---

## 🧾 Example Minimal Similarity Script

If you only want the scoring capability, create a file like `quick_score.py`:
```python
from similarity_scorer.score import score_similarity

print(score_similarity(
	"Your LSA contribution is $42.",
	"42 dollars is your LSA contribution",
))
```
Run with:
```bash
python quick_score.py
```

---

Happy hacking! 🎯

