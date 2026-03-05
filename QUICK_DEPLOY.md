# 🚀 5分钟完成部署指南

## 步骤1: 创建GitHub仓库（1分钟）

1. 访问 https://github.com/new
2. 填写:
   - **Repository name**: `News-about-VC`
   - **Description**: VC投资热度追踪器
   - **Public**: 勾选
   - **Initialize**: 不勾选任何选项
3. 点击 **Create repository**

## 步骤2: 上传代码（2分钟）

在终端中执行：

```bash
# 进入项目目录
cd "News about VC"

# 初始化Git
git init

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit"

# 关联远程仓库（替换YOUR_USERNAME为你的GitHub用户名）
git remote add origin https://github.com/YOUR_USERNAME/News-about-VC.git

# 推送代码
git branch -M main
git push -u origin main
```

## 步骤3: 启用GitHub Pages（1分钟）

1. 打开你的GitHub仓库页面
2. 点击 **Settings** → **Pages**（左侧菜单）
3. **Source** 部分选择 **GitHub Actions**
4. 保存

## 步骤4: 配置权限（1分钟）

1. 点击 **Settings** → **Actions** → **General**
2. 找到 **Workflow permissions**
3. 选择 **Read and write permissions**
4. 保存

## 步骤5: 运行工作流（自动）

1. 点击仓库顶部的 **Actions** 标签
2. 点击左侧的 **VC Tracker Deploy**
3. 点击右侧的 **Run workflow** → **Run workflow**
4. 等待2-3分钟，直到显示绿色✓

## ✅ 完成！

访问你的网站：
```
https://YOUR_USERNAME.github.io/News-about-VC/
```

（将YOUR_USERNAME替换为你的GitHub用户名）

---

## 🔄 自动更新

网站会自动每天更新2次（北京时间10:00和22:00），无需手动操作。

## 📱 查看数据

- 网站首页会显示抓取的新闻列表
- 支持按来源筛选和搜索
- 点击标题可跳转到原文

## ⚠️ 注意事项

1. **第一次访问可能需要1-2分钟加载**
2. **Product Hunt和IT桔子可能显示提示信息**（技术限制）
3. **如果显示404，请等待2分钟后刷新**

## 🆘 遇到问题？

### 推送失败
```bash
# 如果提示权限错误，使用SSH方式
git remote set-url origin git@github.com:YOUR_USERNAME/News-about-VC.git
```

### Actions运行失败
1. 检查GitHub仓库中是否有 `.github/workflows/deploy.yml` 文件
2. 确认 `requirements.txt` 存在且内容正确
3. 查看Actions日志获取详细错误信息

### 网页404错误
1. 确认Actions已成功运行（绿色✓）
2. 确认Pages设置中Source为GitHub Actions
3. 等待1-2分钟后刷新页面

---

**恭喜！你的VC追踪器已经成功部署到GitHub Pages！** 🎉
