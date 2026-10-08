# ClaimShield Nexus — SIU Workspace (Frontend)

React 19 + Vite + Tailwind 4 dashboard. It reads live data from the FastAPI backend
(`/api/v1/dashboard`, `/graph`, `/cases`, `/copilot`) and falls back to built-in demo data
if the API is offline (the header shows "Demo data (API offline)").

```bash
npm install
npm run dev      # http://localhost:5173  (proxies /api -> http://localhost:8000)
npm run build
```

Set `VITE_API_URL` to call a backend on another origin, or `VITE_PROXY_TARGET` to change the dev proxy.
