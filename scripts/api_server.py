#!/usr/bin/env python3
"""
VC雷达 API服务器
提供数据刷新接口，点击刷新按钮时重新爬取最新数据
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import threading
from datetime import datetime
import time

# CORS headers
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json'
}

class APIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # 简化日志输出
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")
    
    def do_OPTIONS(self):
        self.send_response(200)
        for key, value in CORS_HEADERS.items():
            self.send_header(key, value)
        self.end_headers()
    
    def do_GET(self):
        if self.path == '/api/refresh':
            self.handle_refresh()
        elif self.path == '/api/status':
            self.handle_status()
        else:
            self.send_error(404)
    
    def handle_refresh(self):
        """处理刷新请求 - 重新爬取数据"""
        print("\n" + "="*60)
        print("🔄 收到刷新请求，开始重新爬取数据...")
        print("="*60)
        
        try:
            # 运行数据刷新脚本
            script_path = os.path.join(os.path.dirname(__file__), 'refresh_data.py')
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode == 0:
                # 读取更新后的数据
                data_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'data.json')
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                response = {
                    'success': True,
                    'message': f'成功刷新，共获取 {len(data)} 条新闻',
                    'count': len(data),
                    'timestamp': datetime.now().isoformat()
                }
                print(f"✅ 刷新完成: {len(data)} 条新闻")
            else:
                response = {
                    'success': False,
                    'message': '刷新失败: ' + result.stderr,
                    'timestamp': datetime.now().isoformat()
                }
                print(f"❌ 刷新失败: {result.stderr}")
            
            self.send_response(200)
            for key, value in CORS_HEADERS.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"❌ 错误: {e}")
            self.send_response(500)
            for key, value in CORS_HEADERS.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'message': str(e)
            }).encode())
    
    def handle_status(self):
        """返回当前数据状态"""
        try:
            data_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'data.json')
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 统计各来源数量
            source_counts = {}
            for item in data:
                source = item.get('source', 'Unknown')
                source_counts[source] = source_counts.get(source, 0) + 1
            
            response = {
                'success': True,
                'total': len(data),
                'sources': source_counts,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            response = {
                'success': False,
                'message': str(e)
            }
        
        self.send_response(200)
        for key, value in CORS_HEADERS.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

def run_server(port=8081):
    """启动API服务器"""
    server = HTTPServer(('localhost', port), APIHandler)
    print(f"\n🚀 VC雷达 API服务器已启动")
    print(f"   地址: http://localhost:{port}")
    print(f"   刷新接口: http://localhost:{port}/api/refresh")
    print(f"\n📋 使用说明:")
    print(f"   1. 保持此窗口运行")
    print(f"   2. 在浏览器打开 http://localhost:8080")
    print(f"   3. 点击刷新按钮即可实时抓取最新数据")
    print(f"\n按 Ctrl+C 停止服务器\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n👋 服务器已停止")
        server.shutdown()

if __name__ == '__main__':
    run_server()
