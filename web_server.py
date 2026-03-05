# -*- coding: utf-8 -*-
"""
VC投资热度追踪器 - Web服务器 v2.1
支持5个数据源：Paul Graham, Hacker News, Sam Altman, Fred Wilson, Benedict Evans
"""

import http.server
import socketserver
import json
import logging
import threading
import webbrowser
from datetime import datetime
import sys
import os
import subprocess
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vc_tracker.multi_crawler import MultiCrawler

logger = logging.getLogger(__name__)

PORT = 8081

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VC Radar</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,200..800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #f5f6f8;
            --bg-surface: #ffffff;
            --bg-card: #ffffff;
            --bg-elevated: #f0f1f4;
            --border: #e0e3e8;
            --border-hover: #c5cad3;
            --text-primary: #1a1e2c;
            --text-secondary: #5a6377;
            --text-muted: #929bb0;
            --accent: #f38020;
            --accent-hover: #e06e10;
            --accent-glow: rgba(243, 128, 32, 0.1);
            --green: #059669;
            --red: #dc2626;
            --blue: #2563eb;
            --source-pg: #059669;
            --source-hn: #ea580c;
            --source-sa: #7c3aed;
            --source-fw: #db2777;
            --source-be: #2563eb;
            --radius: 8px;
            --radius-lg: 12px;
            --transition: 150ms ease;
        }

        *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
        html { scroll-behavior: smooth; }

        body {
            font-family: 'Bricolage Grotesque', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
            background: var(--bg-base);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }

        .accent-bar {
            position: fixed;
            top: 0; left: 0; right: 0;
            height: 2px;
            background: var(--accent);
            z-index: 9999;
        }

        .app {
            max-width: 1400px;
            margin: 0 auto;
            padding: 26px 32px 32px;
        }

        /* ---- NAV ---- */
        .nav {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 0 24px;
            gap: 16px;
            flex-wrap: wrap;
        }

        .nav-brand {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .nav-logo {
            width: 10px; height: 10px;
            border-radius: 50%;
            background: var(--accent);
            box-shadow: 0 0 12px var(--accent-glow);
            animation: pulse 3s ease-in-out infinite;
        }

        .nav-title {
            font-size: 1.05rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .nav-version {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.65rem;
            color: var(--text-muted);
            background: var(--bg-card);
            padding: 2px 8px;
            border-radius: 4px;
            border: 1px solid var(--border);
        }

        .nav-controls {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }

        .nav-select, .nav-input {
            font-family: inherit;
            font-size: 0.82rem;
            padding: 7px 14px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            color: var(--text-primary);
            outline: none;
            transition: border-color var(--transition);
        }
        .nav-select { min-width: 130px; }
        .nav-input { min-width: 160px; }
        .nav-select:focus, .nav-input:focus { border-color: var(--accent); }
        .nav-select option { background: #fff; color: var(--text-primary); }

        .btn {
            font-family: inherit;
            font-size: 0.82rem;
            font-weight: 600;
            padding: 7px 18px;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            cursor: pointer;
            transition: all var(--transition);
            display: inline-flex;
            align-items: center;
            gap: 6px;
            white-space: nowrap;
        }

        .btn-ghost {
            background: transparent;
            color: var(--text-secondary);
        }
        .btn-ghost:hover {
            background: var(--bg-card);
            color: var(--text-primary);
            border-color: var(--border-hover);
        }

        .btn-accent {
            background: var(--accent);
            color: #fff;
            border-color: var(--accent);
        }
        .btn-accent:hover {
            background: var(--accent-hover);
            border-color: var(--accent-hover);
        }
        .btn-accent:disabled {
            opacity: 0.4;
            cursor: not-allowed;
        }

        /* ---- STATS ---- */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 10px;
            margin-bottom: 20px;
        }

        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 18px 16px;
            text-align: center;
            transition: all var(--transition);
            opacity: 0;
            transform: translateY(8px);
            animation: fadeUp 0.4s ease forwards;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }
        .stat-card:nth-child(1) { animation-delay: 0.04s; }
        .stat-card:nth-child(2) { animation-delay: 0.08s; }
        .stat-card:nth-child(3) { animation-delay: 0.12s; }
        .stat-card:nth-child(4) { animation-delay: 0.16s; }
        .stat-card:nth-child(5) { animation-delay: 0.20s; }
        .stat-card:nth-child(6) { animation-delay: 0.24s; }
        .stat-card:nth-child(7) { animation-delay: 0.28s; }
        .stat-card:hover {
            border-color: var(--border-hover);
            transform: translateY(-2px);
        }

        .stat-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.75rem;
            font-weight: 600;
            line-height: 1.2;
        }

        .stat-label {
            font-size: 0.7rem;
            color: var(--text-secondary);
            margin-top: 6px;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }

        .stat-dot {
            width: 6px; height: 6px;
            border-radius: 50%;
            display: inline-block;
        }

        /* ---- TABLE ---- */
        .table-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }

        table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }

        thead { position: sticky; top: 0; z-index: 10; }

        th {
            background: var(--bg-elevated);
            padding: 11px 16px;
            text-align: left;
            font-size: 0.68rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border);
            white-space: nowrap;
        }
        th:first-child { text-align: center; width: 48px; }

        td {
            padding: 13px 16px;
            border-bottom: 1px solid var(--border);
            vertical-align: middle;
        }

        tr { transition: background var(--transition); }
        tbody tr:hover { background: var(--bg-elevated); }
        tbody tr:hover td:first-child { box-shadow: inset 3px 0 0 var(--accent); }

        .cell-index {
            text-align: center;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        .cell-source { white-space: nowrap; }

        .source-dot {
            width: 7px; height: 7px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
            vertical-align: middle;
        }

        .source-name {
            font-size: 0.82rem;
            font-weight: 500;
            color: var(--text-secondary);
        }

        .title-link {
            color: var(--text-primary);
            text-decoration: none;
            font-weight: 450;
            line-height: 1.5;
            transition: color var(--transition);
        }
        .title-link:hover { color: var(--accent); }

        .title-summary {
            display: block;
            font-size: 0.78rem;
            color: var(--text-muted);
            margin-top: 3px;
            line-height: 1.4;
        }

        .sector-pill {
            display: inline-block;
            font-size: 0.68rem;
            font-weight: 600;
            padding: 2px 10px;
            border-radius: 20px;
            background: var(--accent-glow);
            color: var(--accent);
            letter-spacing: 0.02em;
        }

        .cell-time {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.78rem;
            color: var(--text-muted);
            white-space: nowrap;
        }

        /* ---- EMPTY STATE ---- */
        .empty-state {
            text-align: center;
            padding: 72px 20px;
        }
        .empty-radar {
            margin: 0 auto 20px;
            opacity: 0.25;
        }
        .empty-title {
            font-size: 0.95rem;
            color: var(--text-secondary);
            margin-bottom: 6px;
        }
        .empty-text {
            font-size: 0.82rem;
            color: var(--text-muted);
        }

        /* ---- LOADING ---- */
        .loading-overlay {
            position: fixed; inset: 0;
            background: rgba(245, 246, 248, 0.9);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 1000;
            backdrop-filter: blur(6px);
        }
        .loading-overlay.active { display: flex; }

        .loading-box { text-align: center; }

        .spinner {
            width: 36px; height: 36px;
            border: 3px solid var(--border);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 0.7s linear infinite;
            margin: 0 auto 18px;
        }

        .loading-text { font-size: 0.88rem; color: var(--text-secondary); }
        .loading-subtext { font-size: 0.78rem; color: var(--text-muted); margin-top: 4px; }

        /* ---- TOAST ---- */
        .toast {
            position: fixed;
            bottom: 24px; right: 24px;
            background: var(--bg-elevated);
            border: 1px solid var(--border);
            padding: 12px 18px;
            border-radius: var(--radius);
            display: none;
            align-items: center;
            gap: 10px;
            z-index: 1001;
            font-size: 0.82rem;
            max-width: 380px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        .toast.show { display: flex; animation: slideUp 0.3s ease; }
        .toast.success { border-left: 3px solid var(--green); }
        .toast.error { border-left: 3px solid var(--red); }
        .toast-icon { font-size: 0.9rem; }
        .toast-msg { color: var(--text-secondary); }

        /* ---- FOOTER ---- */
        .footer {
            padding: 20px 0;
            margin-top: 20px;
            text-align: center;
            font-size: 0.72rem;
            color: var(--text-muted);
            border-top: 1px solid var(--border);
            letter-spacing: 0.02em;
        }
        .footer span { color: var(--text-secondary); }

        /* ---- ANIMATIONS ---- */
        @keyframes fadeUp {
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        @keyframes slideUp {
            from { transform: translateY(16px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        @keyframes pulse {
            0%, 100% { box-shadow: 0 0 12px var(--accent-glow); }
            50% { box-shadow: 0 0 20px rgba(243, 128, 32, 0.3); }
        }

        /* ---- RESPONSIVE ---- */
        @media (max-width: 1024px) {
            .stats-grid { grid-template-columns: repeat(3, 1fr); }
        }
        @media (max-width: 768px) {
            .app { padding: 18px 16px; }
            .nav { flex-direction: column; align-items: flex-start; }
            .nav-controls { width: 100%; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .stat-value { font-size: 1.3rem; }
            th, td { padding: 10px 12px; }
        }
        @media (max-width: 480px) {
            .stats-grid { grid-template-columns: 1fr 1fr; }
            .nav-controls { flex-direction: column; }
            .nav-select, .nav-input { width: 100%; min-width: 0; }
        }
    </style>
</head>
<body>
    <div class="accent-bar"></div>

    <div class="loading-overlay" id="loadingOverlay">
        <div class="loading-box">
            <div class="spinner"></div>
            <div class="loading-text" id="loadingText">正在抓取数据...</div>
            <div class="loading-subtext">从 5 个数据源获取最新资讯</div>
        </div>
    </div>

    <div class="toast" id="toast">
        <span class="toast-icon" id="toastIcon"></span>
        <span class="toast-msg" id="toastMessage"></span>
    </div>

    <div class="app">
        <nav class="nav">
            <div class="nav-brand">
                <span class="nav-logo"></span>
                <span class="nav-title">VC Radar</span>
                <span class="nav-version">v2.2</span>
            </div>
            <div class="nav-controls">
                <select class="nav-select" id="source-filter" onchange="filterData()">
                    <option value="all">全部来源</option>
                    <option value="Paul Graham">Paul Graham</option>
                    <option value="Hacker News">Hacker News</option>
                    <option value="Sam Altman">Sam Altman</option>
                    <option value="Fred Wilson">Fred Wilson</option>
                    <option value="Benedict Evans">Benedict Evans</option>
                </select>
                <input class="nav-input" type="text" id="search-input" placeholder="搜索标题..." onkeyup="filterData()">
                <button class="btn btn-ghost" onclick="loadExistingData()">加载数据</button>
                <button class="btn btn-accent" id="refreshBtn" onclick="refreshData()">刷新</button>
            </div>
        </nav>

        <div class="stats-grid" id="statsBar">
            <div class="stat-card">
                <div class="stat-value" id="totalCount">0</div>
                <div class="stat-label">总计</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="pgCount">0</div>
                <div class="stat-label"><span class="stat-dot" style="background:var(--source-pg)"></span>Paul Graham</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="hnCount">0</div>
                <div class="stat-label"><span class="stat-dot" style="background:var(--source-hn)"></span>Hacker News</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="saCount">0</div>
                <div class="stat-label"><span class="stat-dot" style="background:var(--source-sa)"></span>Sam Altman</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="fwCount">0</div>
                <div class="stat-label"><span class="stat-dot" style="background:var(--source-fw)"></span>Fred Wilson</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="beCount">0</div>
                <div class="stat-label"><span class="stat-dot" style="background:var(--source-be)"></span>Benedict Evans</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="lastUpdate" style="font-size:0.95rem">--</div>
                <div class="stat-label">最后更新</div>
            </div>
        </div>

        <div class="table-card">
            <div class="table-wrapper">
                <table id="news-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>来源</th>
                            <th>标题</th>
                            <th>领域</th>
                            <th>时间</th>
                        </tr>
                    </thead>
                    <tbody id="table-body">
                        <tr><td colspan="5">
                            <div class="empty-state">
                                <svg class="empty-radar" width="52" height="52" viewBox="0 0 52 52" fill="none"><circle cx="26" cy="26" r="22" stroke="currentColor" stroke-width="1"/><circle cx="26" cy="26" r="14" stroke="currentColor" stroke-width="1"/><circle cx="26" cy="26" r="6" stroke="currentColor" stroke-width="1"/><circle cx="26" cy="26" r="2.5" fill="currentColor"/></svg>
                                <div class="empty-title">暂无数据</div>
                                <div class="empty-text">点击上方「刷新」获取最新资讯</div>
                            </div>
                        </td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <footer class="footer">
            Product By Chen Zihui
        </footer>
    </div>

    <script>
        let allData = [];
        let filteredData = [];

        function escapeHtml(str) {
            if (!str) return '';
            const div = document.createElement('div');
            div.appendChild(document.createTextNode(str));
            return div.innerHTML;
        }

        function sanitizeUrl(url) {
            if (!url) return '#';
            try {
                const parsed = new URL(url, window.location.origin);
                if (parsed.protocol === 'http:' || parsed.protocol === 'https:') return url;
            } catch(e) {}
            return '#';
        }

        function getSourceDotColor(source) {
            if (!source) return 'var(--accent)';
            if (source.includes('Paul')) return 'var(--source-pg)';
            if (source.includes('Hacker')) return 'var(--source-hn)';
            if (source.includes('Sam') || source.includes('Altman')) return 'var(--source-sa)';
            if (source.includes('Fred') || source.includes('Wilson')) return 'var(--source-fw)';
            if (source.includes('Benedict') || source.includes('Evans')) return 'var(--source-be)';
            return 'var(--accent)';
        }

        window.onload = function() { loadExistingData(); };

        function showLoading(message) {
            document.getElementById('loadingOverlay').classList.add('active');
            if (message) document.getElementById('loadingText').textContent = message;
        }
        function hideLoading() {
            document.getElementById('loadingOverlay').classList.remove('active');
        }

        function showToast(message, type) {
            type = type || 'success';
            const toast = document.getElementById('toast');
            const icon = document.getElementById('toastIcon');
            const msg = document.getElementById('toastMessage');
            toast.className = 'toast ' + type;
            icon.textContent = type === 'success' ? '\\u2713' : '\\u2717';
            msg.textContent = message;
            toast.classList.add('show');
            setTimeout(function() { toast.classList.remove('show'); }, 3500);
        }

        async function loadExistingData() {
            try {
                const response = await fetch('/api/data');
                const data = await response.json();
                if (data && data.length > 0) {
                    allData = data;
                    filterData();
                    updateStats();
                    showToast('已加载 ' + data.length + ' 条数据');
                } else {
                    showEmptyState();
                }
            } catch (error) {
                showEmptyState();
            }
        }

        async function refreshData() {
            const btn = document.getElementById('refreshBtn');
            btn.disabled = true;
            btn.textContent = '刷新中...';
            showLoading('正在抓取数据...');
            try {
                const response = await fetch('/api/refresh', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const result = await response.json();
                if (result.success) {
                    allData = result.data;
                    filterData();
                    updateStats();
                    showToast('抓取成功，共 ' + result.count + ' 条');
                } else {
                    showToast('抓取失败: ' + result.error, 'error');
                }
            } catch (error) {
                showToast('网络错误', 'error');
            } finally {
                hideLoading();
                btn.disabled = false;
                btn.textContent = '刷新';
            }
        }

        function showEmptyState() {
            document.getElementById('table-body').innerHTML =
                '<tr><td colspan="5">' +
                '<div class="empty-state">' +
                '<svg class="empty-radar" width="52" height="52" viewBox="0 0 52 52" fill="none"><circle cx="26" cy="26" r="22" stroke="currentColor" stroke-width="1"/><circle cx="26" cy="26" r="14" stroke="currentColor" stroke-width="1"/><circle cx="26" cy="26" r="6" stroke="currentColor" stroke-width="1"/><circle cx="26" cy="26" r="2.5" fill="currentColor"/></svg>' +
                '<div class="empty-title">暂无数据</div>' +
                '<div class="empty-text">点击上方「刷新」获取最新资讯</div>' +
                '</div></td></tr>';
        }

        function displayData(data) {
            const tbody = document.getElementById('table-body');
            if (data.length === 0) { showEmptyState(); return; }

            let html = '';
            data.forEach(function(item, index) {
                const rawTitle = item.title || '';
                const title = escapeHtml(rawTitle.length > 100 ? rawTitle.substring(0, 100) + '...' : rawTitle);
                const rawSummary = item.summary || '';
                const summary = rawSummary
                    ? '<span class="title-summary">' + escapeHtml(rawSummary.substring(0, 120)) + (rawSummary.length > 120 ? '...' : '') + '</span>'
                    : '';

                let timeDisplay = '--';
                if (item.publish_time) {
                    const date = new Date(item.publish_time);
                    if (!isNaN(date.getTime())) {
                        timeDisplay = date.toLocaleString('zh-CN', { month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit' });
                    }
                }

                const dotColor = getSourceDotColor(item.source);
                const sectorHtml = item.sector
                    ? '<span class="sector-pill">' + escapeHtml(item.sector) + '</span>'
                    : '<span class="cell-time">--</span>';

                html += '<tr>' +
                    '<td class="cell-index">' + String(index + 1).padStart(2, '0') + '</td>' +
                    '<td class="cell-source"><span class="source-dot" style="background:' + dotColor + '"></span><span class="source-name">' + escapeHtml(item.source) + '</span></td>' +
                    '<td><a href="' + sanitizeUrl(item.url) + '" target="_blank" rel="noopener noreferrer" class="title-link">' + title + '</a>' + summary + '</td>' +
                    '<td>' + sectorHtml + '</td>' +
                    '<td class="cell-time">' + timeDisplay + '</td>' +
                    '</tr>';
            });
            tbody.innerHTML = html;
        }

        function filterData() {
            const sourceFilter = document.getElementById('source-filter').value;
            const searchKeyword = document.getElementById('search-input').value.toLowerCase().trim();
            filteredData = allData;
            if (sourceFilter !== 'all') {
                filteredData = filteredData.filter(function(item) { return item.source === sourceFilter; });
            }
            if (searchKeyword) {
                filteredData = filteredData.filter(function(item) {
                    return item.title.toLowerCase().includes(searchKeyword) ||
                           (item.summary && item.summary.toLowerCase().includes(searchKeyword));
                });
            }
            displayData(filteredData);
            document.getElementById('totalCount').textContent = filteredData.length;
        }

        function updateStats() {
            const counts = { 'Paul Graham': 0, 'Hacker News': 0, 'Sam Altman': 0, 'Fred Wilson': 0, 'Benedict Evans': 0 };
            allData.forEach(function(item) {
                if (counts.hasOwnProperty(item.source)) counts[item.source]++;
            });
            document.getElementById('totalCount').textContent = allData.length;
            document.getElementById('pgCount').textContent = counts['Paul Graham'];
            document.getElementById('hnCount').textContent = counts['Hacker News'];
            document.getElementById('saCount').textContent = counts['Sam Altman'];
            document.getElementById('fwCount').textContent = counts['Fred Wilson'];
            document.getElementById('beCount').textContent = counts['Benedict Evans'];
            const now = new Date().toLocaleString('zh-CN', { month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit' });
            document.getElementById('lastUpdate').textContent = now;
        }
    </script>
</body>
</html>
"""


class VCRequestHandler(http.server.SimpleHTTPRequestHandler):
    """自定义请求处理器"""

    multi_crawler = MultiCrawler()
    _crawler_lock = threading.Lock()

    def do_GET(self):
        """处理GET请求"""
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))

        elif self.path == '/api/data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()

            with self._crawler_lock:
                self.multi_crawler.load_data()
                data = [item.to_dict() for item in self.multi_crawler.data]
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

        else:
            super().do_GET()

    def do_POST(self):
        """处理POST请求"""
        if self.path == '/api/refresh':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()

            try:
                logger.info("开始抓取数据...")
                with self._crawler_lock:
                    self.multi_crawler.refresh(max_items_per_site=30)
                    self.multi_crawler.save_data()
                    data = [item.to_dict() for item in self.multi_crawler.data]
                response = {
                    'success': True,
                    'count': len(data),
                    'data': data
                }
                logger.info(f"抓取完成，共 {len(data)} 条")
            except Exception as e:
                logger.error(f"抓取失败: {e}")
                response = {
                    'success': False,
                    'error': 'Data crawl failed. Check server logs.'
                }

            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))

        else:
            self.send_error(404)

    def log_message(self, format, *args):
        """覆盖日志方法"""
        logger.info(args[0])


def start_server():
    """启动服务器"""
    with socketserver.TCPServer(("", PORT), VCRequestHandler) as httpd:
        logger.info(f"VC投资热度追踪器 v2.1 - Web服务器已启动")
        logger.info(f"请在浏览器中访问: http://localhost:{PORT}")
        logger.info(f"按 Ctrl+C 停止服务器")

        # 自动打开浏览器
        threading.Timer(2.0, lambda: webbrowser.open(f'http://localhost:{PORT}')).start()

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("服务器已停止")


if __name__ == '__main__':
    start_server()
