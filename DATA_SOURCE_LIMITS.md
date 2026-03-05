# 🔍 数据源限制说明

## 问题背景

您可能会发现 **Product Hunt** 和 **IT桔子** 抓取不到数据或只能获取提示信息。这是正常现象，原因如下：

---

## 📱 Product Hunt - JavaScript动态渲染

### 为什么抓取困难？

```
❌ 技术限制
├── 使用React/Vue等现代前端框架
├── 内容通过JavaScript动态加载
├── 静态HTML中无实际产品数据
└── 需要浏览器执行JS才能获取内容

✅ 正常访问
└── 浏览器会自动执行JS，正常显示
```

### 解决方案

#### 方案1: 使用浏览器直接访问（推荐）
```
访问: https://www.producthunt.com/
优点: 体验最佳，功能完整
缺点: 无法自动抓取
```

#### 方案2: 使用RSS订阅
```
RSS地址: https://www.producthunt.com/feed
优点: 可以获取最新产品
缺点: 信息有限，格式固定
```

#### 方案3: 使用Headless浏览器（高级）
```python
# 需要安装selenium或playwright
pip install selenium

# 或使用playwright（推荐）
pip install playwright
playwright install

# 然后修改爬虫使用浏览器驱动
```

### 代码改进

当前代码已添加:
1. ✅ 尝试通过RSS获取数据
2. ✅ 失败时显示友好提示
3. ✅ 提供直接访问链接

---

## 🇨🇳 IT桔子 - 反爬虫机制

### 为什么抓取困难？

```
❌ 访问限制
├── 需要登录账号才能查看完整数据
├── 严格的IP访问频率限制
├── User-Agent检测
├── 验证码保护
└── API需要认证密钥

✅ 正常访问
└── 登录账号后，网站功能完整
```

### 解决方案

#### 方案1: 使用浏览器直接访问（推荐）
```
访问: https://www.itjuzi.com/investevent
步骤:
1. 注册并登录IT桔子账号
2. 访问投资事件页面
3. 查看最新投融资数据
优点: 数据最全最准确
缺点: 需要手动操作
```

#### 方案2: 使用IT桔子API（需要授权）
```python
# IT桔子提供商业API接口
# 需要联系官方获取API Key
# 参考文档: https://www.itjuzi.com/api

headers = {
    'Authorization': 'Bearer YOUR_API_KEY',
    'Content-Type': 'application/json'
}
```

#### 方案3: 使用替代数据源
```python
# 其他国内投融资数据源:
1. 36kr (已有支持)
2. 投中网
3. 铅笔道
4. 猎云网
```

### 代码改进

当前代码已添加:
1. ✅ 多层备用抓取策略
2. ✅ 失败时显示友好提示
3. ✅ 提供直接访问链接

---

## 🎯 建议的数据源组合

由于上述限制，建议主要依赖以下**可稳定抓取**的数据源：

### 强烈推荐 ✅

1. **Hacker News** (news.ycombinator.com)
   - 无需登录
   - 静态HTML，易于抓取
   - 全球技术创业热点
   - 更新频繁

2. **Paul Graham** (paulgraham.com)
   - 无需登录
   - 纯静态页面
   - 创业投资经典文章
   - 内容质量极高

3. **36kr** (36kr.com) - 原有支持
   - 中文科技媒体
   - 国内创业资讯
   - API相对稳定

### 可选补充 ⚠️

4. **Product Hunt**
   - 建议直接浏览器访问
   - 或使用RSS
   - 最新产品发布

5. **IT桔子**
   - 建议直接浏览器访问
   - 需要登录
   - 国内投融资数据最全

---

## 🛠️ 技术改进建议

### 如果想完整抓取这些网站，需要：

#### 1. 使用Selenium/Playwright
```python
# 安装
pip install selenium webdriver-manager

# 或使用Playwright
pip install playwright
playwright install chromium
```

#### 2. 处理登录认证
```python
# 保存Cookie
# 或使用自动化登录
```

#### 3. 使用代理池
```python
# 轮换IP避免被封
# 使用付费代理服务
```

#### 4. 降低抓取频率
```python
# 增加延迟
DELAY = 5  # 秒
```

---

## 📊 当前实现的状态

| 数据源 | 状态 | 说明 |
|--------|------|------|
| Hacker News | ✅ 正常 | 可稳定抓取 |
| Paul Graham | ✅ 正常 | 可稳定抓取 |
| Product Hunt | ⚠️ 受限 | 尝试RSS，失败显示提示 |
| IT桔子 | ⚠️ 受限 | 尝试备用方案，失败显示提示 |

---

## 💡 使用建议

### Web界面使用
1. 点击"立即抓取"获取数据
2. Paul Graham和Hacker News会正常抓取
3. Product Hunt和IT桔子如果抓取失败，会显示提示
4. 点击提示中的链接直接访问网站

### 命令行使用
```bash
# 正常抓取可访问的数据源
python main.py multi-crawl --pg --hn

# 手动访问受限网站获取信息
# 然后整合到自己的数据库中
```

### 数据整合工作流
```
1. 自动抓取: Hacker News + Paul Graham
2. 手动收集: Product Hunt + IT桔子
3. 合并分析: 使用analyze模块分析所有数据
```

---

## 🔮 未来改进方向

1. **添加更多稳定数据源**
   - Reddit创业板块
   - IndieHackers
   - BetaList

2. **使用Headless浏览器**
   - Playwright支持
   - 自动化登录

3. **RSS聚合**
   - 订阅各网站RSS
   - 定时同步

4. **API集成**
   - 申请各平台官方API
   - 更稳定的数据获取

---

## 📞 需要帮助？

如果需要抓取这些受限网站，可以：

1. 使用浏览器书签手动收集
2. 考虑购买商业数据服务
3. 使用RSS阅读器订阅
4. 联系网站申请API权限

---

## ✅ 总结

- **Product Hunt** 和 **IT桔子** 抓取困难是技术限制，不是代码bug
- 建议主要使用 **Hacker News** 和 **Paul Graham** 进行自动化抓取
- 受限网站可通过浏览器直接访问，然后手动整合数据
- 代码已添加友好提示，指引用户正确访问这些网站
