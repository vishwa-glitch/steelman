# Steelman frontend

React + TypeScript (Vite).

```
npm install
npm run dev        # http://localhost:5173, expects the API on http://localhost:8000 (set VITE_API_URL to change)
npm run lint && npx tsc -b && npm test && npm run build
```

Browser checks (need Google Chrome and the dev server running):

```
# backend started with FAKE_LLM=1, so no AI calls are spent
node e2e/debate.mjs http://localhost:5173 /tmp/shots
# backend stopped
node e2e/offline.mjs http://localhost:5173 /tmp/shots
```
