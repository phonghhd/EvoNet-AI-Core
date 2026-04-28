from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime, timedelta
import sqlite3
import pandas as pd

app = FastAPI()

# Create templates directory and files
templates_dir = Path("app/templates")
templates_dir.mkdir(exist_ok=True, parents=True)

# Create a more advanced HTML template with charts
html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Evonet-core Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --primary: #3498db;
            --secondary: #2c3e50;
            --success: #27ae60;
            --warning: #f39c12;
            --danger: #e74c3c;
            --light: #f8f9fa;
            --dark: #343a40;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }
        
        .header {
            background: linear-gradient(135deg, var(--secondary), #1a2530);
            color: white;
            padding: 1rem 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .header h1 {
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }
        
        .header p {
            opacity: 0.9;
        }
        
        .container {
            max-width: 1400px;
            margin: 2rem auto;
            padding: 0 1rem;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            padding: 1.5rem;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #eee;
        }
        
        .card-title {
            font-size: 1.2rem;
            font-weight: 600;
            color: var(--secondary);
        }
        
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        
        .stat-card {
            background: linear-gradient(135deg, var(--primary), #2980b9);
            color: white;
            padding: 1.5rem;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 10px rgba(52, 152, 219, 0.3);
        }
        
        .stat-number {
            font-size: 2.5rem;
            font-weight: 700;
            margin: 0.5rem 0;
        }
        
        .stat-label {
            font-size: 1rem;
            opacity: 0.9;
        }
        
        .chart-container {
            height: 300px;
            margin: 1rem 0;
            position: relative;
        }
        
        .table-container {
            overflow-x: auto;
        }
        
        .table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }
        
        .table th, .table td {
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        
        .table th {
            background-color: #f8f9fa;
            font-weight: 600;
            color: var(--secondary);
        }
        
        .table tr:hover {
            background-color: #f8f9fa;
        }
        
        .progress-container {
            margin: 1rem 0;
        }
        
        .progress-bar {
            height: 12px;
            background-color: #e0e0e0;
            border-radius: 6px;
            overflow: hidden;
            margin: 0.5rem 0;
        }
        
        .progress-fill {
            height: 100%;
            border-radius: 6px;
            transition: width 0.3s ease;
        }
        
        .progress-success {
            background: linear-gradient(90deg, var(--success), #2ecc71);
        }
        
        .progress-warning {
            background: linear-gradient(90deg, var(--warning), #f1c40f);
        }
        
        .timestamp {
            color: #7f8c8d;
            font-size: 0.85rem;
            font-weight: 500;
        }
        
        .badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 500;
        }
        
        .badge-success {
            background-color: rgba(39, 174, 96, 0.1);
            color: var(--success);
        }
        
        .badge-warning {
            background-color: rgba(243, 156, 18, 0.1);
            color: var(--warning);
        }
        
        .badge-danger {
            background-color: rgba(231, 76, 60, 0.1);
            color: var(--danger);
        }
        
        .refresh-btn {
            background: var(--primary);
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            transition: background 0.3s ease;
        }
        
        .refresh-btn:hover {
            background: #2980b9;
        }
        
        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }
            
            .stat-grid {
                grid-template-columns: 1fr 1fr;
            }
            
            .header h1 {
                font-size: 1.5rem;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Evonet-core Dashboard</h1>
        <p>Hệ thống AI tự học và tiến hóa bảo mật - Thống kê thời gian thực</p>
        <button class="refresh-btn" onclick="refreshData()">🔄 Làm mới dữ liệu</button>
    </div>
    
    <div class="container">
        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-number" id="total_cves">0</div>
                <div class="stat-label">Lỗ hổng CVE</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="defense_skills">0</div>
                <div class="stat-label">Kỹ năng phòng thủ</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="threat_intel">0</div>
                <div class="stat-label">Thông tin đe dọa</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="patches">0</div>
                <div class="stat-label">Bản vá</div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">Hoạt động gần đây</div>
                </div>
                <div class="table-container">
                    <table class="table" id="activities-table">
                        <thead>
                            <tr>
                                <th>Thời gian</th>
                                <th>Hoạt động</th>
                                <th>Trạng thái</th>
                            </tr>
                        </thead>
                        <tbody>
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <div class="card-title">Tiến trình học tập</div>
                </div>
                <div class="progress-container">
                    <div>Hoàn thành:</div>
                    <div class="progress-bar">
                        <div class="progress-fill progress-success" id="learning-progress" style="width: 0%"></div>
                    </div>
                    <div id="learning-percent">0%</div>
                </div>
                <div class="progress-container">
                    <div>Độ chính xác:</div>
                    <div class="progress-bar">
                        <div class="progress-fill progress-warning" id="accuracy-progress" style="width: 0%"></div>
                    </div>
                    <div id="accuracy-percent">0%</div>
                </div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">Phân tích hiệu suất theo thời gian</div>
                </div>
                <div class="chart-container">
                    <canvas id="performance-chart"></canvas>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <div class="card-title">Phân bố loại lỗ hổng</div>
                </div>
                <div class="chart-container">
                    <canvas id="vulnerability-chart"></canvas>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Chart instances
        let performanceChart = null;
        let vulnerabilityChart = null;
        
        // Initialize charts
        function initCharts() {
            const performanceCtx = document.getElementById('performance-chart').getContext('2d');
            performanceChart = new Chart(performanceCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Số mục xử lý',
                        data: [],
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        tension: 0.4,
                        fill: true
                    }, {
                        label: 'Tỷ lệ thành công (%)',
                        data: [],
                        borderColor: '#27ae60',
                        backgroundColor: 'rgba(39, 174, 96, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
            
            const vulnerabilityCtx = document.getElementById('vulnerability-chart').getContext('2d');
            vulnerabilityChart = new Chart(vulnerabilityCtx, {
                type: 'doughnut',
                data: {
                    labels: ['SQL Injection', 'XSS', 'Buffer Overflow', 'Command Injection', 'Path Traversal'],
                    datasets: [{
                        data: [30, 25, 20, 15, 10],
                        backgroundColor: [
                            '#3498db',
                            '#2ecc71',
                            '#f39c12',
                            '#e74c3c',
                            '#9b59b6'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        }
        
        // Load data from API
        async function loadData() {
            try {
                // Load stats
                const statsResponse = await fetch('/api/stats');
                const stats = await statsResponse.json();
                
                document.getElementById('total_cves').textContent = stats.total_cves;
                document.getElementById('defense_skills').textContent = stats.defense_skills;
                document.getElementById('threat_intel').textContent = stats.threat_intel;
                document.getElementById('patches').textContent = stats.patches;
                
                // Update progress bars
                document.getElementById('learning-progress').style.width = stats.learning_progress + '%';
                document.getElementById('learning-percent').textContent = stats.learning_progress + '%';
                
                document.getElementById('accuracy-progress').style.width = stats.success_rate + '%';
                document.getElementById('accuracy-percent').textContent = stats.success_rate + '%';
                
                // Load activities
                const activitiesResponse = await fetch('/api/activities');
                const activities = await activitiesResponse.json();
                
                const tbody = document.querySelector('#activities-table tbody');
                tbody.innerHTML = '';
                
                activities.forEach(activity => {
                    const row = tbody.insertRow();
                    row.innerHTML = `
                        <td class="timestamp">${activity.timestamp}</td>
                        <td>${activity.action}</td>
                        <td><span class="badge badge-${activity.status_class}">${activity.status}</span></td>
                    `;
                });
                
                // Update charts with mock data
                if (performanceChart) {
                    const hours = [];
                    const processed = [];
                    const success = [];
                    
                    for (let i = 23; i >= 0; i--) {
                        const hour = new Date(Date.now() - i * 60 * 60 * 1000).getHours();
                        hours.push(hour + ':00');
                        processed.push(Math.floor(Math.random() * 50) + 10);
                        success.push(Math.floor(Math.random() * 30) + 70);
                    }
                    
                    performanceChart.data.labels = hours;
                    performanceChart.data.datasets[0].data = processed;
                    performanceChart.data.datasets[1].data = success;
                    performanceChart.update();
                }
                
            } catch (error) {
                console.error('Error loading data:', error);
            }
        }
        
        // Refresh data function
        function refreshData() {
            loadData();
        }
        
        // Initialize when page loads
        document.addEventListener('DOMContentLoaded', function() {
            initCharts();
            loadData();
            
            // Auto-refresh every 30 seconds
            setInterval(loadData, 30000);
        });
    </script>
</body>
</html>
"""

# Write the template file
template_file = templates_dir / "dashboard.html"
template_file.write_text(html_template)

# Initialize templates
templates = Jinja2Templates(directory="app/templates")

# Initialize database for storing dashboard data
def init_db():
    conn = sqlite3.connect("app/dashboard.db")
    cursor = conn.cursor()
    
    # Create tables for dashboard data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dashboard_stats (
            id INTEGER PRIMARY KEY,
            total_cves INTEGER,
            defense_skills INTEGER,
            threat_intel INTEGER,
            patches INTEGER,
            learning_progress REAL,
            processed_items INTEGER,
            success_rate REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            action TEXT,
            details TEXT,
            status TEXT,
            status_class TEXT
        )
    """)
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Mock data for demonstration
def get_dashboard_stats():
    """Get dashboard statistics"""
    # In a real implementation, this would query your actual data sources
    return {
        "total_cves": 1247,
        "defense_skills": 892,
        "threat_intel": 563,
        "patches": 234,
        "learning_progress": 78.5,
        "processed_items": 142,
        "success_rate": 94.2
    }

def get_recent_activities():
    """Get recent activities for dashboard"""
    # In a real implementation, this would query your activity log
    return [
        {
            "timestamp": "2023-06-15 14:30:22",
            "action": "Thu thập CVE mới",
            "details": "Đã thu thập 3 lỗ hổng mới từ NVD",
            "status": "Thành công",
            "status_class": "success"
        },
        {
            "timestamp": "2023-06-15 13:45:17",
            "action": "Tự học & tiến hóa",
            "details": "Đã tạo 2 kỹ năng phòng thủ mới",
            "status": "Thành công",
            "status_class": "success"
        },
        {
            "timestamp": "2023-06-15 12:20:05",
            "action": "Tự động vá lỗi",
            "details": "Đã tạo PR vá lỗi cho main.py",
            "status": "Thành công",
            "status_class": "success"
        },
        {
            "timestamp": "2023-06-15 11:05:43",
            "action": "Thu thập thông tin đe dọa",
            "details": "Đã thu thập 12 mẫu thông tin mới",
            "status": "Thành công",
            "status_class": "success"
        },
        {
            "timestamp": "2023-06-15 10:30:11",
            "action": "Kiểm tra chất lượng",
            "details": "Đã hoàn tất kiểm tra tự động",
            "status": "Thành công",
            "status_class": "success"
        }
    ]

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request
    })

@app.get("/api/stats")
async def api_stats():
    """API endpoint for dashboard statistics"""
    return get_dashboard_stats()

@app.get("/api/activities")
async def api_activities():
    """API endpoint for recent activities"""
    return get_recent_activities()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/metrics")
async def metrics():
    """System metrics endpoint"""
    # In a real implementation, this would return actual system metrics
    return {
        "uptime": "1h 23m",
        "memory_usage": "45%",
        "cpu_usage": "23%",
        "active_connections": 12,
        "total_requests": 1247
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)