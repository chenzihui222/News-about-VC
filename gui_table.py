# -*- coding: utf-8 -*-
"""
VC投资热度追踪器 - GUI表格窗口
实时显示新闻标题表格
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import threading
import time
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vc_tracker.multi_crawler import MultiCrawler


class NewsTableWindow:
    """新闻表格窗口"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("VC投资热度追踪器 - 实时新闻列表")
        self.root.geometry("1200x700")
        self.root.minsize(1000, 600)
        
        self.multi_crawler = MultiCrawler()
        self.is_refreshing = False
        
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        """设置UI界面"""
        # 顶部控制栏
        control_frame = tk.Frame(self.root, padx=10, pady=10)
        control_frame.pack(fill=tk.X)
        
        # 标题
        title_label = tk.Label(
            control_frame, 
            text="📊 VC投资热度追踪器", 
            font=("Arial", 16, "bold")
        )
        title_label.pack(side=tk.LEFT)
        
        # 刷新按钮
        self.refresh_btn = tk.Button(
            control_frame,
            text="🔄 刷新数据",
            command=self.refresh_data,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=20,
            pady=5
        )
        self.refresh_btn.pack(side=tk.RIGHT, padx=5)
        
        # 自动刷新开关
        self.auto_refresh_var = tk.BooleanVar(value=False)
        self.auto_refresh_check = tk.Checkbutton(
            control_frame,
            text="自动刷新(5分钟)",
            variable=self.auto_refresh_var,
            command=self.toggle_auto_refresh
        )
        self.auto_refresh_check.pack(side=tk.RIGHT, padx=10)
        
        # 筛选框
        filter_frame = tk.Frame(self.root, padx=10, pady=5)
        filter_frame.pack(fill=tk.X)
        
        tk.Label(filter_frame, text="筛选来源:").pack(side=tk.LEFT)
        
        self.source_var = tk.StringVar(value="全部")
        self.source_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.source_var,
            values=["全部", "36kr", "a16z", "Y Combinator", "Hacker News"],
            state="readonly",
            width=15
        )
        self.source_combo.pack(side=tk.LEFT, padx=5)
        self.source_combo.bind("<<ComboboxSelected>>", self.filter_data)
        
        # 搜索框
        tk.Label(filter_frame, text="搜索:").pack(side=tk.LEFT, padx=(20, 0))
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(filter_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind("<Return>", self.filter_data)
        
        search_btn = tk.Button(filter_frame, text="🔍", command=self.filter_data)
        search_btn.pack(side=tk.LEFT)
        
        # 状态栏
        self.status_label = tk.Label(
            self.root,
            text="准备就绪",
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 创建表格
        self.create_table()
        
    def create_table(self):
        """创建表格"""
        # 创建框架
        table_frame = tk.Frame(self.root, padx=10, pady=5)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建树形表格
        columns = ("序号", "来源", "标题", "领域", "发布时间")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )
        
        # 设置列宽
        self.tree.heading("序号", text="序号")
        self.tree.column("序号", width=50, anchor="center")
        
        self.tree.heading("来源", text="来源")
        self.tree.column("来源", width=120, anchor="w")
        
        self.tree.heading("标题", text="标题")
        self.tree.column("标题", width=600, anchor="w")
        
        self.tree.heading("领域", text="领域")
        self.tree.column("领域", width=100, anchor="center")
        
        self.tree.heading("发布时间", text="发布时间")
        self.tree.column("发布时间", width=150, anchor="center")
        
        # 添加滚动条
        scrollbar_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        # 布局
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # 绑定双击事件
        self.tree.bind("<Double-1>", self.on_item_double_click)
        
    def load_data(self):
        """加载数据"""
        self.status_label.config(text="正在加载数据...")
        self.root.update()
        
        try:
            # 尝试从文件加载
            self.multi_crawler.load_data()
            
            if not self.multi_crawler.data:
                self.status_label.config(text="本地没有数据，正在抓取...")
                self.root.update()
                self.multi_crawler.crawl_all(max_items_per_site=20)
                self.multi_crawler.save_data()
            
            self.update_table()
            self.status_label.config(
                text=f"✅ 共加载 {len(self.multi_crawler.data)} 条新闻 | 最后更新: {datetime.now().strftime('%H:%M:%S')}"
            )
        except Exception as e:
            self.status_label.config(text=f"❌ 加载失败: {str(e)}")
            messagebox.showerror("错误", f"加载数据失败:\n{str(e)}")
    
    def update_table(self):
        """更新表格数据"""
        # 清空表格
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 获取筛选条件
        source_filter = self.source_var.get()
        search_keyword = self.search_var.get().lower()
        
        # 填充数据
        count = 0
        for idx, item in enumerate(self.multi_crawler.data, 1):
            # 来源筛选
            if source_filter != "全部" and item.source != source_filter:
                continue
            
            # 关键词搜索
            if search_keyword and search_keyword not in item.title.lower():
                continue
            
            count += 1
            
            # 截断标题
            title = item.title[:80] + "..." if len(item.title) > 80 else item.title
            
            # 格式化时间
            try:
                pub_time = datetime.fromisoformat(item.publish_time).strftime("%m-%d %H:%M")
            except:
                pub_time = "未知"
            
            self.tree.insert(
                "",
                tk.END,
                values=(count, item.source, title, item.sector, pub_time),
                tags=(item.url,)
            )
        
        # 设置行颜色（交替）
        for i, item in enumerate(self.tree.get_children()):
            if i % 2 == 0:
                self.tree.item(item, tags=("even",))
        
        self.tree.tag_configure("even", background="#f0f0f0")
    
    def refresh_data(self):
        """刷新数据"""
        if self.is_refreshing:
            return
        
        self.is_refreshing = True
        self.refresh_btn.config(state=tk.DISABLED, text="刷新中...")
        self.status_label.config(text="🔄 正在抓取数据，请稍候...")
        self.root.update()
        
        def do_refresh():
            try:
                self.multi_crawler.refresh(max_items_per_site=30)
                self.multi_crawler.save_data()
                
                self.root.after(0, self._refresh_complete)
            except Exception as e:
                self.root.after(0, lambda: self._refresh_error(str(e)))
        
        threading.Thread(target=do_refresh, daemon=True).start()
    
    def _refresh_complete(self):
        """刷新完成回调"""
        self.update_table()
        self.is_refreshing = False
        self.refresh_btn.config(state=tk.NORMAL, text="🔄 刷新数据")
        self.status_label.config(
            text=f"✅ 刷新完成！共 {len(self.multi_crawler.data)} 条新闻 | 更新时间: {datetime.now().strftime('%H:%M:%S')}"
        )
        messagebox.showinfo("完成", f"数据刷新成功！\n共获取 {len(self.multi_crawler.data)} 条新闻")
    
    def _refresh_error(self, error_msg):
        """刷新错误回调"""
        self.is_refreshing = False
        self.refresh_btn.config(state=tk.NORMAL, text="🔄 刷新数据")
        self.status_label.config(text=f"❌ 刷新失败: {error_msg}")
        messagebox.showerror("错误", f"刷新数据失败:\n{error_msg}")
    
    def filter_data(self, event=None):
        """筛选数据"""
        self.update_table()
        count = len(self.tree.get_children())
        self.status_label.config(text=f"筛选结果: {count} 条")
    
    def on_item_double_click(self, event):
        """双击打开链接"""
        selected_item = self.tree.selection()
        if selected_item:
            item = self.tree.item(selected_item[0])
            url = item["tags"][0] if item["tags"] else None
            
            if url and url.startswith("http"):
                import webbrowser
                webbrowser.open(url)
            else:
                messagebox.showinfo("提示", "该条目没有有效链接")
    
    def toggle_auto_refresh(self):
        """切换自动刷新"""
        if self.auto_refresh_var.get():
            self.schedule_refresh()
    
    def schedule_refresh(self):
        """计划自动刷新"""
        if self.auto_refresh_var.get():
            self.refresh_data()
            # 5分钟后再次刷新
            self.root.after(300000, self.schedule_refresh)


def main():
    """主函数"""
    root = tk.Tk()
    
    # 设置样式
    style = ttk.Style()
    style.theme_use("clam")
    
    # 设置字体
    default_font = ("Microsoft YaHei", 10)
    root.option_add("*Font", default_font)
    
    app = NewsTableWindow(root)
    
    # 居中窗口
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    
    root.mainloop()


if __name__ == "__main__":
    main()
