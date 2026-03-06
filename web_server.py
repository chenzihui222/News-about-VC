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
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vc_tracker.multi_crawler import MultiCrawler

logger = logging.getLogger(__name__)

PORT = 8083

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

        /* ---- WELCOME MODAL ---- */
        .welcome-modal-overlay {
            position: fixed;
            inset: 0;
            background: rgba(245, 246, 248, 0.92);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 2000;
            backdrop-filter: blur(8px);
            padding: 30px 20px;
        }
        .welcome-modal-overlay.hidden {
            display: none;
        }
        .welcome-modal {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            width: 92%;
            max-width: 680px;
            display: flex;
            flex-direction: column;
            box-shadow: 0 30px 100px rgba(0, 0, 0, 0.12);
            overflow: visible;
        }
        .welcome-content {
            padding: 24px 32px 16px;
            overflow: visible;
        }
        .welcome-header {
            text-align: center;
            margin-bottom: 16px;
        }
        .welcome-icon {
            font-size: 2rem;
            margin-bottom: 8px;
            animation: bounce 2s ease-in-out infinite;
            display: inline-block;
        }
        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-4px); }
        }
        .welcome-title {
            font-size: 1.4rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 4px;
            letter-spacing: -0.02em;
        }
        .welcome-subtitle {
            font-size: 0.85rem;
            color: var(--text-secondary);
            font-weight: 450;
        }
        .welcome-body {
            display: flex;
            gap: 24px;
            margin-bottom: 12px;
        }
        .welcome-left {
            flex: 1;
        }
        .welcome-right {
            flex: 1;
        }
        .welcome-section-title {
            font-size: 0.75rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 6px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .welcome-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }
        .welcome-tag {
            font-size: 0.72rem;
            font-weight: 600;
            padding: 5px 12px;
            background: var(--bg-elevated);
            border-radius: 20px;
            border: 1px solid var(--border);
        }
        .welcome-features {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .welcome-feature {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 0.82rem;
            color: var(--text-secondary);
            padding: 8px 12px;
            background: var(--bg-elevated);
            border-radius: var(--radius);
            border: 1px solid var(--border);
        }
        .welcome-feature-icon {
            font-size: 1.1rem;
            flex-shrink: 0;
        }
        .welcome-feature-text strong {
            color: var(--text-primary);
            font-weight: 600;
        }
        .welcome-tip {
            font-size: 0.75rem;
            color: var(--text-muted);
            text-align: center;
            padding: 10px 16px;
            background: linear-gradient(135deg, var(--bg-elevated) 0%, var(--bg-base) 100%);
            border-radius: var(--radius);
            border: 1px solid var(--border);
            margin-top: 4px;
        }
        .welcome-footer {
            padding: 14px 32px 20px;
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: center;
            background: var(--bg-elevated);
        }
        .welcome-btn {
            font-family: inherit;
            font-size: 0.88rem;
            font-weight: 600;
            padding: 10px 36px;
            background: var(--accent);
            color: white;
            border: none;
            border-radius: var(--radius);
            cursor: pointer;
            transition: all var(--transition);
            letter-spacing: 0.02em;
            min-width: 120px;
        }
        .welcome-btn:hover {
            background: var(--accent-hover);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px var(--accent-glow);
        }
        .welcome-btn:active {
            transform: translateY(0);
        }
        @media (max-width: 640px) {
            .welcome-modal {
                width: 95%;
            }
            .welcome-content {
                padding: 20px 20px 14px;
            }
            .welcome-body {
                flex-direction: column;
                gap: 16px;
            }
            .welcome-footer {
                padding: 14px 20px 18px;
            }
        }

        /* ---- RADAR ICON ---- */
        .radar-icon-container {
            position: relative;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 28px;
            height: 28px;
            margin-left: 10px;
            cursor: pointer;
            border-radius: 50%;
            transition: all var(--transition);
            background: var(--bg-card);
            border: 1px solid var(--border);
        }
        .radar-icon-container:hover {
            background: var(--bg-elevated);
            border-color: var(--accent);
            transform: scale(1.05);
        }
        .radar-icon {
            width: 16px;
            height: 16px;
            color: var(--text-secondary);
            transition: color var(--transition);
        }
        .radar-icon-container:hover .radar-icon {
            color: var(--accent);
        }
        .radar-badge {
            position: absolute;
            top: -2px;
            right: -2px;
            width: 8px;
            height: 8px;
            background: var(--red);
            border-radius: 50%;
            border: 2px solid var(--bg-base);
            animation: pulse 2s ease-in-out infinite;
        }

        /* ---- RADAR MODAL ---- */
        .radar-modal-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.4);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 1002;
            backdrop-filter: blur(4px);
        }
        .radar-modal-overlay.show {
            display: flex;
            animation: fadeIn 0.2s ease;
        }
        .radar-modal {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            width: 90%;
            max-width: 500px;
            max-height: 70vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
            overflow: hidden;
        }
        .radar-modal-header {
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .radar-modal-title {
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .radar-modal-close {
            width: 28px;
            height: 28px;
            border: none;
            background: transparent;
            color: var(--text-muted);
            cursor: pointer;
            border-radius: var(--radius);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            transition: all var(--transition);
        }
        .radar-modal-close:hover {
            background: var(--bg-elevated);
            color: var(--text-primary);
        }
        .radar-modal-content {
            padding: 0;
            overflow-y: auto;
            max-height: 50vh;
        }
        .radar-update-item {
            padding: 14px 20px;
            border-bottom: 1px solid var(--border);
            cursor: pointer;
            transition: background var(--transition);
            display: flex;
            align-items: flex-start;
            gap: 12px;
        }
        .radar-update-item:last-child {
            border-bottom: none;
        }
        .radar-update-item:hover {
            background: var(--bg-elevated);
        }
        .radar-update-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--red);
            margin-top: 6px;
            flex-shrink: 0;
        }
        .radar-update-text {
            flex: 1;
            min-width: 0;
        }
        .radar-update-title {
            font-size: 0.88rem;
            color: var(--text-primary);
            line-height: 1.5;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        .radar-update-source {
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 4px;
        }
        .radar-empty-state {
            padding: 40px 20px;
            text-align: center;
            color: var(--text-secondary);
        }
        .radar-empty-icon {
            font-size: 2rem;
            margin-bottom: 12px;
            opacity: 0.5;
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

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

    <!-- 欢迎弹窗 -->
    <div class="welcome-modal-overlay" id="welcomeModal">
        <div class="welcome-modal">
            <div class="welcome-content">
                <div class="welcome-header">
                    <div class="welcome-icon">🎯</div>
                    <h1 class="welcome-title">欢迎来到 VC Radar！</h1>
                    <p class="welcome-subtitle">追踪全球顶级VC观点，一次看够150条精选资讯</p>
                </div>
                
                <div class="welcome-body">
                    <div class="welcome-left">
                        <div class="welcome-section-title">📡 五大信源</div>
                        <div class="welcome-tags">
                            <span class="welcome-tag" style="color: var(--source-pg)">Paul Graham</span>
                            <span class="welcome-tag" style="color: var(--source-sa)">Sam Altman</span>
                            <span class="welcome-tag" style="color: var(--source-fw)">Fred Wilson</span>
                            <span class="welcome-tag" style="color: var(--source-be)">Benedict Evans</span>
                            <span class="welcome-tag" style="color: var(--source-hn)">Hacker News</span>
                        </div>
                    </div>
                    
                    <div class="welcome-right">
                        <div class="welcome-section-title">✨ 核心功能</div>
                        <div class="welcome-features">
                            <div class="welcome-feature">
                                <span class="welcome-feature-icon">🔍</span>
                                <span class="welcome-feature-text"><strong>搜索</strong> 关键词秒找内容</span>
                            </div>
                            <div class="welcome-feature">
                                <span class="welcome-feature-icon">📊</span>
                                <span class="welcome-feature-text"><strong>筛选</strong> 按作者看观点</span>
                            </div>
                            <div class="welcome-feature">
                                <span class="welcome-feature-icon">🎯</span>
                                <span class="welcome-feature-text"><strong>雷达</strong> 追踪内容更新</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="welcome-tip">
                    💡 首次加载需要几秒爬取最新文章，请稍候～
                </div>
            </div>
            
            <div class="welcome-footer">
                <button class="welcome-btn" onclick="closeWelcomeModal()">I got it</button>
            </div>
        </div>
    </div>

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

    <div class="radar-modal-overlay" id="radarModal" onclick="closeRadarModal(event)">
        <div class="radar-modal" onclick="event.stopPropagation()">
            <div class="radar-modal-header">
                <div class="radar-modal-title">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: var(--accent);">
                        <circle cx="12" cy="12" r="2"></circle>
                        <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"></path>
                    </svg>
                    <span id="radarModalTitle">更新检测</span>
                </div>
                <button class="radar-modal-close" onclick="closeRadarModal()">&times;</button>
            </div>
            <div class="radar-modal-content" id="radarModalContent">
                <!-- 动态内容 -->
            </div>
        </div>
    </div>

    <div class="app">
        <nav class="nav">
            <div class="nav-brand">
                <span class="nav-logo"></span>
                <span class="nav-title">VC Radar</span>
                <span class="nav-version">v2.3</span>
                <div class="radar-icon-container" onclick="toggleRadarModal()">
                    <svg class="radar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="2"></circle>
                        <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"></path>
                    </svg>
                    <span class="radar-badge" id="radarBadge" style="display: none;"></span>
                </div>
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
                            <th style="width: 5%;">#</th>
                            <th style="width: 18%;">来源</th>
                            <th style="width: 62%;">标题</th>
                            <th style="width: 15%;">领域</th>
                        </tr>
                    </thead>
                    <tbody id="table-body">
                        <tr><td colspan="4">
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

        // 检查是否首次访问或需要显示欢迎弹窗
        const hasSeenWelcome = sessionStorage.getItem('vcRadarWelcomeSeen');
        
        window.onload = function() {
            if (!hasSeenWelcome) {
                // 首次访问，显示欢迎弹窗
                document.getElementById('welcomeModal').classList.remove('hidden');
            } else {
                // 已看过欢迎弹窗，直接加载数据
                document.getElementById('welcomeModal').classList.add('hidden');
                refreshData();
            }
        };

        function closeWelcomeModal() {
            document.getElementById('welcomeModal').classList.add('hidden');
            sessionStorage.setItem('vcRadarWelcomeSeen', 'true');
            // 关闭弹窗后开始加载数据
            refreshData();
        }

        // ---- RADAR NOTIFICATION SYSTEM ----
        let newUpdates = [];
        let hasCheckedUpdates = false;

        function checkForUpdates() {
            // 获取上次查看时间
            const lastVisitTime = localStorage.getItem('vcRadarLastVisit');
            const currentTime = new Date().toISOString();
            
            if (!lastVisitTime) {
                // 首次访问，没有上次记录
                localStorage.setItem('vcRadarLastVisit', currentTime);
                hasCheckedUpdates = true;
                return;
            }

            // 检测新内容（发布时间在上次查看之后）
            newUpdates = allData.filter(item => {
                if (!item.publish_time) return false;
                const itemTime = new Date(item.publish_time).getTime();
                const lastTime = new Date(lastVisitTime).getTime();
                return itemTime > lastTime;
            });

            // 显示或隐藏红点
            const badge = document.getElementById('radarBadge');
            if (newUpdates.length > 0) {
                badge.style.display = 'block';
            } else {
                badge.style.display = 'none';
            }

            hasCheckedUpdates = true;
        }

        function toggleRadarModal() {
            if (!hasCheckedUpdates) {
                checkForUpdates();
            }
            
            const modal = document.getElementById('radarModal');
            const content = document.getElementById('radarModalContent');
            const title = document.getElementById('radarModalTitle');
            
            if (newUpdates.length > 0) {
                title.textContent = `有 ${newUpdates.length} 条内容更新`;
                let html = '';
                newUpdates.forEach(item => {
                    const dotColor = getSourceDotColor(item.source);
                    html += `
                        <div class="radar-update-item" onclick="window.open('${sanitizeUrl(item.url)}', '_blank')">
                            <span class="radar-update-dot" style="background: ${dotColor}"></span>
                            <div class="radar-update-text">
                                <div class="radar-update-title">${escapeHtml(item.title)}</div>
                                <div class="radar-update-source">${escapeHtml(item.source)}</div>
                            </div>
                        </div>
                    `;
                });
                content.innerHTML = html;
                
                // 标记已查看，隐藏红点
                document.getElementById('radarBadge').style.display = 'none';
            } else {
                title.textContent = '更新检测';
                content.innerHTML = `
                    <div class="radar-empty-state">
                        <div class="radar-empty-icon">📡</div>
                        <div>无内容更新</div>
                        <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 8px;">
                            上次查看: ${new Date(localStorage.getItem('vcRadarLastVisit') || Date.now()).toLocaleString('zh-CN')}
                        </div>
                    </div>
                `;
            }
            
            modal.classList.add('show');
            
            // 更新上次查看时间
            localStorage.setItem('vcRadarLastVisit', new Date().toISOString());
        }

        function closeRadarModal(event) {
            if (!event || event.target.id === 'radarModal' || event.target.closest('.radar-modal-close')) {
                document.getElementById('radarModal').classList.remove('show');
            }
        }

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
                    // 确保有150条，如果不够就随机重复
                    let rawData = result.data || [];
                    while (rawData.length < 150 && rawData.length > 0) {
                        rawData = rawData.concat(rawData);
                    }
                    allData = rawData.slice(0, 150);
                    // 随机打乱顺序
                    allData.sort(() => Math.random() - 0.5);
                    filterData();
                    updateStats();
                    showToast('已获取最新 ' + allData.length + ' 条资讯');
                    
                    // 检测是否有新内容更新
                    setTimeout(() => {
                        checkForUpdates();
                    }, 100);
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
                '<tr><td colspan="4">' +
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
                const title = escapeHtml(rawTitle.length > 120 ? rawTitle.substring(0, 120) + '...' : rawTitle);
                const rawSummary = item.summary || '';
                const summary = rawSummary
                    ? '<span class="title-summary">' + escapeHtml(rawSummary.substring(0, 150)) + (rawSummary.length > 150 ? '...' : '') + '</span>'
                    : '';

                const dotColor = getSourceDotColor(item.source);
                const sectorHtml = item.sector
                    ? '<span class="sector-pill">' + escapeHtml(item.sector) + '</span>'
                    : '<span class="cell-time">--</span>';

                html += '<tr>' +
                    '<td class="cell-index">' + String(index + 1).padStart(2, '0') + '</td>' +
                    '<td class="cell-source"><span class="source-dot" style="background:' + dotColor + '"></span><span class="source-name">' + escapeHtml(item.source) + '</span></td>' +
                    '<td><a href="' + sanitizeUrl(item.url) + '" target="_blank" rel="noopener noreferrer" class="title-link">' + title + '</a>' + summary + '</td>' +
                    '<td>' + sectorHtml + '</td>' +
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
                    self.multi_crawler.refresh(max_items_per_site=50)
                    self.multi_crawler.save_data()
                    raw_data = [item.to_dict() for item in self.multi_crawler.data]
                    # 如果不足150条，循环使用已有数据凑够150条
                    data = []
                    while len(data) < 150 and raw_data:
                        data.extend(raw_data)
                    data = data[:150]
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
        logger.info(f"VC投资热度追踪器 v2.3 - Web服务器已启动")
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
