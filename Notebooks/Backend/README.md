# Reel Script Generator

Generate a 30-second reel script from a text prompt using **FastAPI** and **Gemini 2.5 Flash** (Google AI Studio).

## Prerequisites

- **Python 3.12+** (or latest stable)
- A **Gemini API key** from Google AI Studio (see below)

## How to get a Gemini API key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Sign in with your Google account.
3. Click **Get API key** (or **Create API key**).
4. Choose **Create API key in new project** (or pick an existing project).
5. Copy the key and keep it secret. You will use it as the `GEMINI_API_KEY` environment variable.

**Important:** Do not commit your API key to version control. Use a `.env` file (see below) and add `.env` to `.gitignore`.

## Setup

1. **Create a virtual environment (recommended):**

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set your API key:**

   Either export it in your shell:

   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```

   Or create a `.env` file in the project root (same folder as `requirements.txt`):

   ```env
   GEMINI_API_KEY=your-api-key-here
   ```

   Optional: to use a different model (default is `gemini-2.5-flash`):

   ```env
   GEMINI_MODEL=gemini-2.5-flash
   ```

## Run the API

From the project root (where `app/` and `requirements.txt` live):

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Or use the run script (same folder as this README):

```bash
./run_server.sh
```

- API: **http://127.0.0.1:8000**
- Interactive docs: **http://127.0.0.1:8000/docs**
- Health check: **http://127.0.0.1:8000/health**
- Alternative docs: **http://127.0.0.1:8000/redoc**

## Usage

**Endpoint:** `POST /generate-script`

**Request body:**

```json
{
  "prompt": "Create a reel about productivity tips for students"
}
```

**Response:**

```json
{
  "script": "[HOOK]\nYour opening line here...\n\n[BODY]\nMain content here..."
}
```

The script is plain text with `[HOOK]` and `[BODY]` sections, written for a 30-second reel.

**Example with curl:**

```bash
curl -X POST "http://127.0.0.1:8000/generate-script" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a reel about morning routines"}'
```

## Project structure

```
.
├── app/
│   ├── __init__.py
│   ├── config.py       # Settings (API key, model) from env
│   ├── gemini_client.py # Gemini 2.5 Flash script generation
│   └── main.py         # FastAPI app and /generate-script route
├── requirements.txt
└── README.md
```

## Environment variables

| Variable           | Required | Default              | Description                    |
|--------------------|----------|----------------------|--------------------------------|
| `GEMINI_API_KEY`   | Yes      | —                    | Gemini API key (Google AI Studio) |
| `GEMINI_MODEL`     | No       | `gemini-2.5-flash`   | Gemini model id               |

## Troubleshooting: "connect ECONNREFUSED 127.0.0.1:8000"

This means nothing is listening on port 8000. Try the following:

1. **Start the server in a terminal** (and leave it open):
   ```bash
   cd "/Users/cheshtagupta17/Data - Cheshta/Projects/Social Media Manager/Notebooks"
   ./run_server.sh
   ```
   Or: `python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`

2. **Check the terminal output.** You should see:
   ```text
   INFO:     Uvicorn running on http://127.0.0.1:8000
   ```
   If you see an error instead (e.g. `ModuleNotFoundError: No module named 'app'`), you're in the wrong folder—run from the folder that contains the `app` directory.

3. **Test in the browser.** Open http://127.0.0.1:8000/docs — if the Swagger page loads, the server is running. Then try Postman again.

4. **In Postman:** Use **POST** → **http://127.0.0.1:8000/generate-script** (or **http://localhost:8000/generate-script**). Turn off any proxy (Settings → Proxy → set to "No proxy" for localhost if needed).

5. **Port in use?** If you see "Address already in use", another process is using 8000. Either stop it or use a different port: `--port 8001`, then use http://127.0.0.1:8001 in Postman.
