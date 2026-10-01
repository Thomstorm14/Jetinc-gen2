import asyncio
import json
from aiohttp import web

class HaloCommandHubServer:
    def __init__(self, ledger_file: str = "ledger_v1.jsonl"):
        self.ledger_file = ledger_file

    def _get_latest_telemetry(self):
        """Reads the latest BUS_CYCLE_COMPLETE event from the Trident Ledger."""
        try:
            with open(self.ledger_file, "r", encoding="utf-8-sig") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    if not line.strip():
                        continue
                    entry = json.loads(line.strip())
                    if entry.get("event_type") == "BUS_CYCLE_COMPLETE":
                        return entry.get("payload", {}).get("telemetry", {})
        except FileNotFoundError:
            pass
        return {}

    async def handle_telemetry(self, request):
        """Returns JSON state snapshot for the 3D Operator / Halo Command Center."""
        telemetry = self._get_latest_telemetry()
        return web.json_response({
            "system": "JETtrix Async Prime ID Neural Bus",
            "active_nodes": len(telemetry),
            "telemetry": telemetry
        })

    async def handle_dashboard(self, request):
        """HTML/JS Live Terminal Operator View."""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>JETtrix Halo Command Center</title>
    <style>
        body { background-color: #0b0f19; color: #00f0ff; font-family: monospace; padding: 20px; }
        h1 { border-bottom: 2px solid #00f0ff; padding-bottom: 10px; }
        .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-top: 20px; }
        .card { background: #111827; border: 1fr solid #1f2937; padding: 15px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,240,255,0.1); }
        .status { font-weight: bold; padding: 4px 8px; border-radius: 4px; display: inline-block; }
        .GREEN { background: #065f46; color: #34d399; }
        .YELLOW { background: #78350f; color: #fbbf24; }
        .RED { background: #7f1d1d; color: #f87171; }
    </style>
</head>
<body>
    <h1>HALO COMMAND CENTER // JETtrix Neural Bus Operator</h1>
    <div id="operator-grid" class="grid">Loading telemetry...</div>
    <script>
        async function fetchTelemetry() {
            try {
                const res = await fetch('/api/telemetry');
                const data = await res.json();
                const grid = document.getElementById('operator-grid');
                grid.innerHTML = '';
                
                for (const [prime_id, info] of Object.entries(data.telemetry)) {
                    const card = document.createElement('div');
                    card.className = 'card';
                    card.innerHTML = `
                        <h3>${prime_id}</h3>
                        <p>Status: <span class="status ${info.status}">${info.status}</span></p>
                        <p>Endpoint: ${info.endpoint}</p>
                        <p>Model: ${info.model}</p>
                    `;
                    grid.appendChild(card);
                }
            } catch (err) {
                console.error(err);
            }
        }
        setInterval(fetchTelemetry, 2000);
        fetchTelemetry();
    </script>
</body>
</html>"""
        return web.Response(text=html, content_type='text/html')

if __name__ == "__main__":
    hub = HaloCommandHubServer()
    app = web.Application()
    app.router.add_get('/', hub.handle_dashboard)
    app.router.add_get('/api/telemetry', hub.handle_telemetry)
    print("\n[COMMAND HUB] Server online at http://localhost:8080")
    web.run_app(app, host="127.0.0.1", port=8080)
