import os
import sqlite3
import time
import requests
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

load_dotenv("/app/.env", override=True)

app = FastAPI()

templates_dir = Path("app/templates")
templates_dir.mkdir(exist_ok=True, parents=True)

html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EvoNet-Core Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root { --primary: #3498db; --secondary: #2c3e50; --success: #27ae60; --warning: #f39c12; --danger: #e74c3c; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #f5f7fa; color: #333; }
        .header { background: linear-gradient(135deg, var(--secondary), #1a2530); color: white; padding: 1rem 2rem; position: sticky; top: 0; z-index: 100; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { font-size: 1.8rem; }
        .container { max-width: 1400px; margin: 2rem auto; padding: 0 1rem; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
        .card { background: white; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); padding: 1.5rem; }
        .card-title { font-size: 1.2rem; font-weight: 600; color: var(--secondary); margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid #eee; }
        .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .stat-card { background: linear-gradient(135deg, var(--primary), #2980b9); color: white; padding: 1.5rem; border-radius: 10px; text-align: center; }
        .stat-number { font-size: 2.5rem; font-weight: 700; margin: 0.5rem 0; }
        .stat-label { font-size: 1rem; opacity: 0.9; }
        .chart-container { height: 300px; position: relative; }
        .badge { display: inline-block; padding: 0.25rem 0.5rem; border-radius: 12px; font-size: 0.8rem; font-weight: 500; }
        .badge-success { background: rgba(39,174,96,0.1); color: var(--success); }
        .badge-warning { background: rgba(243,156,18,0.1); color: var(--warning); }
        .badge-danger { background: rgba(231,76,60,0.1); color: var(--danger); }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-weight: 600; color: var(--secondary); }
        .progress-bar { height: 12px; background: #e0e0e0; border-radius: 6px; overflow: hidden; margin: 0.5rem 0; }
        .progress-fill { height: 100%; border-radius: 6px; background: linear-gradient(90deg, var(--success), #2ecc71); transition: width 0.3s; }
        .refresh-btn { background: var(--primary); color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; }
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } .stat-grid { grid-template-columns: 1fr 1fr; } }
    </style>
</head>
<body>
    <div class="header">
        <div><h1>EvoNet-Core Dashboard</h1><p>Autonomous AI Security Agent</p></div>
        <button class="refresh-btn" onclick="loadData()">Refresh</button>
    </div>
    <div class="container">
        <div class="stat-grid">
            <div class="stat-card"><div class="stat-number" id="total_cves">-</div><div class="stat-label">CVEs Tracked</div></div>
            <div class="stat-card"><div class="stat-number" id="defense_skills">-</div><div class="stat-label">Defense Skills</div></div>
            <div class="stat-card"><div class="stat-number" id="threat_intel">-</div><div class="stat-label">Threat Intel</div></div>
            <div class="stat-card"><div class="stat-number" id="patches">-</div><div class="stat-label">Patches</div></div>
        </div>
        <div class="grid">
            <div class="card">
                <div class="card-title">Recent Activities</div>
                <table><thead><tr><th>Time</th><th>Action</th><th>Status</th></tr></thead><tbody id="activities-body"></tbody></table>
            </div>
            <div class="card">
                <div class="card-title">System Health</div>
                <div>CPU: <span id="cpu">-</span>%</div>
                <div class="progress-bar"><div class="progress-fill" id="cpu-bar" style="width:0%"></div></div>
                <div>Memory: <span id="mem">-</span>%</div>
                <div class="progress-bar"><div class="progress-fill" id="mem-bar" style="width:0%"></div></div>
                <div>Disk: <span id="disk">-</span>%</div>
                <div class="progress-bar"><div class="progress-fill" id="disk-bar" style="width:0%"></div></div>
            </div>
        </div>
        <div class="grid">
            <div class="card">
                <div class="card-title">Vulnerability Types</div>
                <div class="chart-container"><canvas id="vuln-chart"></canvas></div>
            </div>
            <div class="card">
                <div class="card-title">Activity Timeline</div>
                <div class="chart-container"><canvas id="timeline-chart"></canvas></div>
            </div>
        </div>
    </div>
    <script>
        let vulnChart, timelineChart;
        function initCharts() {
            vulnChart = new Chart(document.getElementById('vuln-chart'), {
                type: 'doughnut',
                data: { labels: ['SQL Injection','XSS','Buffer Overflow','Command Injection','Path Traversal'], datasets: [{ data: [30,25,20,15,10], backgroundColor: ['#3498db','#2ecc71','#f39c12','#e74c3c','#9b59b6'] }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
            });
            timelineChart = new Chart(document.getElementById('timeline-chart'), {
                type: 'line',
                data: { labels: [], datasets: [{ label: 'Processed', data: [], borderColor: '#3498db', tension: 0.4, fill: true, backgroundColor: 'rgba(52,152,219,0.1)' }] },
                options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } }
            });
        }
        async function loadData() {
            try {
                const stats = await (await fetch('/api/stats')).json();
                document.getElementById('total_cves').textContent = stats.total_cves;
                document.getElementById('defense_skills').textContent = stats.defense_skills;
                document.getElementById('threat_intel').textContent = stats.threat_intel;
                document.getElementById('patches').textContent = stats.patches;
                const sys = await (await fetch('/api/system')).json();
                document.getElementById('cpu').textContent = sys.cpu_percent;
                document.getElementById('cpu-bar').style.width = sys.cpu_percent + '%';
                document.getElementById('mem').textContent = sys.memory_percent;
                document.getElementById('mem-bar').style.width = sys.memory_percent + '%';
                document.getElementById('disk').textContent = sys.disk_percent.toFixed(1);
                document.getElementById('disk-bar').style.width = sys.disk_percent + '%';
                const acts = await (await fetch('/api/activities')).json();
                const tbody = document.getElementById('activities-body');
                tbody.innerHTML = '';
                acts.forEach(a => { tbody.innerHTML += `<tr><td>${a.timestamp}</td><td>${a.action}</td><td><span class="badge badge-${a.status_class}">${a.status}</span></td></tr>`; });
            } catch(e) { console.error('Load error:', e); }
        }
        document.addEventListener('DOMContentLoaded', () => { initCharts(); loadData(); setInterval(loadData, 30000); });
    </script>
</body>
</html>"""

template_file = templates_dir / "dashboard.html"
template_file.write_text(html_template)
templates = Jinja2Templates(directory="app/templates")


def get_pinecone_stats():
    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index = pc.Index("evonet-memory")
        stats = index.describe_index_stats()
        ns = stats.get("namespaces", {})
        return {
            "total_cves": ns.get("security_knowledge_clean", {}).get("vector_count", 0),
            "defense_skills": ns.get("learned_skills", {}).get("vector_count", 0),
            "threat_intel": ns.get("threat_intel_raw", {}).get("vector_count", 0),
            "patches": ns.get("patches", {}).get("vector_count", 0),
        }
    except Exception:
        return {"total_cves": 0, "defense_skills": 0, "threat_intel": 0, "patches": 0}


def get_system_metrics():
    import psutil
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
    }


def init_db():
    conn = sqlite3.connect("app/dashboard.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY, timestamp TEXT, action TEXT, details TEXT, status TEXT, status_class TEXT
    )""")
    conn.commit()
    conn.close()


init_db()


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/api/stats")
async def api_stats():
    return get_pinecone_stats()


@app.get("/api/system")
async def api_system():
    return get_system_metrics()


@app.get("/api/activities")
async def api_activities():
    try:
        conn = sqlite3.connect("app/dashboard.db")
        c = conn.cursor()
        c.execute("SELECT timestamp, action, status, status_class FROM activities ORDER BY id DESC LIMIT 20")
        rows = c.fetchall()
        conn.close()
        return [{"timestamp": r[0], "action": r[1], "status": r[2], "status_class": r[3]} for r in rows]
    except Exception:
        return []


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
