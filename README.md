# India Daily Trend Analyzer

A mobile-friendly Vue dashboard for daily NSE/BSE technical analysis, with a Python API for adjusted Yahoo Finance history. CSV import works as a market-data fallback. This deployment uses GitHub Pages for the static frontend and Render for the FastAPI backend; it requires no database.

## Technology

- Frontend: Vue 3, TypeScript, Vite, Lightweight Charts
- Backend: FastAPI, Uvicorn, yfinance
- Hosting: GitHub Pages (frontend) and Render free Web Service (backend)

The backend fetches daily market data from Yahoo Finance through `yfinance`. This unofficial source may rate-limit or change availability; no API credentials are currently required. No third-party API keys or secrets are used by the app.

## Local development

Requirements: Node.js 22+ (18+ should work) and Python 3.10+.

1. Install frontend dependencies:

   ```sh
   npm ci
   ```

2. Create a Python environment and install backend dependencies:

   ```sh
   python -m venv .venv
   ```

   Windows PowerShell:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r server\requirements.txt
   ```

   macOS/Linux:

   ```sh
   .venv/bin/python -m pip install -r server/requirements.txt
   ```

3. Start the API. From the project root:

   ```sh
   python -m uvicorn app:app --app-dir server --reload --host 0.0.0.0 --port 8000
   ```

   Or run `python server/app.py`; it reads `PORT` and defaults to `8000`.

4. In another terminal, start Vue:

   ```sh
   npm run dev
   ```

5. Open the Vite URL (normally `http://localhost:5173`). In development, requests to `/api` use the Vite proxy to `http://127.0.0.1:8000`.

To run tests and build locally:

```sh
npm test
npm run build
```

The Vite production build uses `/NUI/` as its base path so bundled assets load from the GitHub Pages project subpath. There is no Vue Router or client-side route fallback requirement.

## Environment variables

| Variable | Where | Required | Purpose |
| --- | --- | --- | --- |
| `VITE_API_BASE_URL` | GitHub Actions repository variable; optional in local development | Yes for production frontend builds | Public origin of the Render API, e.g. `https://your-service.onrender.com`. Do not append `/api`. This is a URL, not a secret. |
| `CORS_ORIGINS` | Render environment variable | Yes | Comma-separated explicit browser origins allowed to call the API. Set to `https://YOUR_USERNAME.github.io` (no `/NUI/` path). Localhost development origins are included by the backend. |
| `PORT` | Render-provided; optional locally | No manual Render setting | Port Uvicorn binds to. Local default is `8000`. |

Copy `.env.example` to `.env.local` only if you want a local environment file; local API requests still use the Vite proxy. `.env.production` contains a clearly marked placeholder and must not be used as a real backend address. GitHub Actions overrides it with the `VITE_API_BASE_URL` repository variable. Never put API credentials in frontend `VITE_` variables.

The current data provider (`yfinance`) does not use a private credential. If a future provider requires a key, add it only as a Render environment secret and read it in the backend; do not put it in this repository or frontend.

## Deploy the backend to Render

1. Push this project to a GitHub repository.
2. In Render, choose **New + → Blueprint** and connect the repository containing `render.yaml`.
3. Review the `nui-api` service. The Blueprint uses the `server` root directory, installs `server/requirements.txt`, runs Uvicorn on `0.0.0.0:$PORT`, selects the free plan, and configures `/api/health` as its health check.
4. When prompted for `CORS_ORIGINS`, enter the exact GitHub Pages origin, for example `https://YOUR_USERNAME.github.io`. Replace the placeholder with your actual username. Do not include `/NUI/`.
5. Deploy the Blueprint and wait for the service to become healthy. Record its origin, such as `https://your-service.onrender.com`; do not include a path or trailing `/api`.
6. Confirm `https://your-service.onrender.com/api/health` returns `{"status":"ok"}`.

Render's free service may sleep when idle and take time to wake on the next request.

## Deploy the frontend to GitHub Pages

1. Push the project to the `main` branch of your GitHub repository.
2. In the repository, open **Settings → Secrets and variables → Actions → Variables → New repository variable**.
   - Name: `VITE_API_BASE_URL`
   - Value: the deployed Render service origin, e.g. `https://your-service.onrender.com`
3. Open **Settings → Pages** and set the publishing source to **GitHub Actions**.
4. Open **Actions** and run **Deploy frontend to GitHub Pages**, or push a change to `main`. The workflow runs `npm ci`, the tests, `npm run build`, uploads `dist`, and deploys it.
5. Once the workflow succeeds, the site is available at `https://YOUR_USERNAME.github.io/NUI/`.

For a project named `NUI`, the Vite base path is already configured as `/NUI/`. The backend URL is a GitHub repository variable, not a secret; CORS configuration is entered in Render. No GitHub or Render API credentials are required by the app.

## Redeploy after changes

- Frontend changes pushed to `main` automatically run the Pages workflow.
- Backend changes pushed to the connected repository are redeployed by Render according to its service settings.
- If the Render service URL changes, update the GitHub Actions `VITE_API_BASE_URL` variable and Render `CORS_ORIGINS`, then rerun the Pages workflow.
- For manual frontend redeployment, use **Actions → Deploy frontend to GitHub Pages → Run workflow**.

## Troubleshooting

- **Pages builds but API calls fail:** Verify the `VITE_API_BASE_URL` repository variable is the Render service origin, with HTTPS and no `/api` suffix. Re-run the workflow after changing it.
- **Browser reports a CORS error:** Set Render `CORS_ORIGINS` to the exact origin `https://YOUR_USERNAME.github.io` (no repository path or trailing slash). Check Render logs and redeploy/restart after updating the variable.
- **Health check fails:** Check the Render build/deploy logs and confirm `server/requirements.txt` installs successfully. The start command must bind to `0.0.0.0` and use Render's `$PORT`.
- **First request is slow or times out:** Free Render services can sleep when idle. Retry after the service wakes. Yahoo Finance can separately rate-limit or fail to return a symbol's data.
- **GitHub Pages returns 404:** Confirm Pages is configured to publish with GitHub Actions, the workflow completed, and the repository/project is named `NUI` to match the `/NUI/` asset base.
- **Local API calls fail:** Start the backend on port `8000`; the development proxy targets `http://127.0.0.1:8000`.

## Current features and limitations

- Search supported NSE symbols and retrieve split/dividend-adjusted daily candles with a 15-minute server cache.
- Select 3M, 6M, 1Y, 2Y, or 5Y lookback and Swing/Positional context.
- Calculate EMA 20/50/200, SMA 50, RSI, MACD, Bollinger Bands, ATR, ADX, Supertrend, volume average, and rolling support/resistance.
- Explain six scored signal factors in plain English and warn when Nifty's 50/200-day regime is bearish.
- Scan NIFTY 50, NIFTY 100, NIFTY Midcap 150, or the starter list with adjustable minimum-price and average-volume filters.
- Show the signal, confidence, chart overlays, volume, trade levels, and risk-based share sizing; save a local watchlist and upload CSV data.
- Signals are educational prototypes, not recommendations. Index constituents are snapshots and should be checked after index reshuffles. NSE holiday calendars/circuit-limit data and historical-cost backtesting are not implemented. Verify market data independently before use.

Signal factors (trend, momentum, volatility, volume, trend strength, and relative strength) each contribute -2 to +2. Their total maps to Strong Sell (<= -7), Sell (<= -3), Hold (-2 to 2), Buy (>= 3), or Strong Buy (>= 7). A bearish Nifty regime reduces a positive score by two points. Confidence is a simple score-strength display, not a probability.

**For educational purposes only. Not investment advice. Not SEBI-registered advice. Markets involve risk.**
