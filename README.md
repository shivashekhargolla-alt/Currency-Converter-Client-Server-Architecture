# 💱 Currency Converter — Client/Server Architecture

A currency converter built with a real **client-server split**: a FastAPI
backend that owns all data/business logic, and a Streamlit frontend that
only renders UI and talks to the backend over HTTP — never to the external
exchange rate API directly.

![CI](https://github.com/<your-username>/<your-repo>/actions/workflows/ci.yml/badge.svg)

## Architecture

```
currency_converter/
├── server/                FastAPI backend
│   ├── main.py             — endpoints, caching, currency/country/flag enrichment
│   └── requirements.txt
├── client/                 Streamlit frontend
│   ├── app.py               — UI, dropdowns, swap button, result card
│   ├── .streamlit/config.toml
│   └── requirements.txt
├── .github/workflows/ci.yml   Lint + import check on every push
├── render.yaml              One-click backend deploy config for Render
├── LICENSE
└── README.md
```

**Why split it?** The server is a standalone, reusable API — any client
(this Streamlit app, a future mobile app, a CLI tool) can consume the same
`/api/rates` and `/api/convert` endpoints without duplicating logic. Swapping
the underlying data provider only ever requires changing the server.

## Features

- Live exchange rates for 150+ currencies (open.er-api.com)
- Server-side caching (1 hour) to avoid hammering the upstream API
- Currency name, country, and flag emoji enrichment via `pycountry`
- Swap button, dark themed UI, expandable full-rates table
- Interactive auto-generated API docs (`/docs`) via FastAPI

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/rates` | All currencies with code, name, country, flag, rate |
| GET | `/api/convert?from=USD&to=INR&amount=100` | Convert an amount between two currencies |
| GET | `/api/health` | Health check |
| GET | `/docs` | Swagger UI |

## Running locally

**1. Start the server:**
```bash
cd server
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Visit `http://localhost:8000/docs` to try it directly.

**2. Start the client** (in a separate terminal):
```bash
cd client
pip install -r requirements.txt
streamlit run app.py
```
Visit the URL Streamlit prints (usually `http://localhost:8501`).

## Deploying

**Backend (Render — free tier):**
1. Push this repo to GitHub (see below).
2. In Render, choose **New → Blueprint**, point it at your repo — `render.yaml`
   configures everything automatically.
3. Note the deployed URL, e.g. `https://currency-converter-api.onrender.com`.

**Frontend (Streamlit Community Cloud — free):**
1. Go to [share.streamlit.io](https://share.streamlit.io), connect your GitHub repo.
2. Set the app's main file path to `client/app.py`.
3. In the app's **Settings → Secrets**, add:
   ```toml
   SERVER_URL = "https://currency-converter-api.onrender.com"
   ```
4. Deploy — the client will now call your live backend instead of localhost.

## Tech stack

- **Backend:** FastAPI, Pydantic, Uvicorn, `requests`, `pycountry`
- **Frontend:** Streamlit, `pandas`
- **CI:** GitHub Actions (lint + import check)
- **Deploy:** Render (backend), Streamlit Community Cloud (frontend)

## Possible next steps

- Add authentication / API key on the server's own endpoints
- Persist cache in Redis instead of an in-memory dict (survives restarts, scales across instances)
- Historical rate chart (line graph over the last N days)
- Unit tests with `pytest` for conversion logic and edge cases

## License

MIT — see [LICENSE](LICENSE).
