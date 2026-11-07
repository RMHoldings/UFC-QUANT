# UFCQuant Web MVP deployment

This archive now includes a static dashboard and a FastAPI adapter. They deploy as **two services**:

## 1. Deploy the Python API on Render

- Create a Render **Web Service** from this repository/archive after importing it to GitHub.
- Render Blueprint may read `render.yaml`; alternatively configure:
  - Build command: `pip install -r requirements.txt`
  - Start command: `uvicorn ufc_quant.api:app --host 0.0.0.0 --port $PORT`
- Set `CORS_ORIGINS` to the exact Netlify origin, e.g. `https://your-site.netlify.app` (no trailing slash). For a custom domain, include that origin too, comma-separated.
- Verify `https://<render-service>.onrender.com/api/health` returns JSON with status `ok`.

## 2. Deploy the static dashboard on Netlify

- Netlify build configuration is included in `netlify.toml`:
  - Build command: `python web/build.py`
  - Publish directory: `web/public`
- In Netlify Site configuration → Environment variables, set:
  - `UFCQUANT_API_URL` = the Render API base URL, e.g. `https://ufcquant-api.onrender.com`
- Trigger a fresh deploy. The build script inserts that API URL into the static HTML.
- Verify the dashboard API indicator says Online; click “Load upcoming card”.

## API routes

- `GET /api/health` — health/readiness indicator.
- `GET /api/events/upcoming` — fetches UFC.com event/card through the project's adapter, live and on-demand; may return 502 if upstream fails.
- `GET /api/demo-report` — creates an HTML report from the project's synthetic sample card. Clearly a demo, not a verified forecast.

## Scope and limitations

- This is a web UI/API wrapper around the existing UFCQuant Python CLI code, not a claim that the predictive model is empirically calibrated.
- The existing source adapter may fail when UFC.com blocks requests or changes markup. No fabricated fallback card is used.
- Do not expose credentials in frontend environment variables. Only the public API base URL belongs in the static build.
- Render free services can sleep; first request may be slow. A production scheduler and persistent database deployment are not configured by this web MVP.
