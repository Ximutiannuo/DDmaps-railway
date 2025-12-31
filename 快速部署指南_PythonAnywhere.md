# 🚀 PythonAnywhere 快速部署指南（5步完成）

## 📋 准备工作

### 需要上传的文件
```
必需文件：
├── app.py                    # 主程序
├── requirements.txt          # 依赖包
├── backend/                  # 整个后端目录
├── traffic_system.html       # 管理端页面
├── driver.html              # 司机端页面
├── css/                     # 样式目录
│   ├── traffic_system.css
│   └── driver.css
└── js/                      # JavaScript目录
    ├── api.js
    ├── app-main.js
    ├── charts.js
    ├── config.js
    ├── ui-manager.js
    ├── utils.js
    └── websocket.js

可选文件（保留数据用）：
├── system_checkpoint.json
└── travel_time_database.json
```

---

## 🎯 部署步骤（5步）

### 步骤 1️⃣: 打包文件

**Windows PowerShell：**
```powershell
# 在项目目录下运行
Compress-Archive -Path app.py,requirements.txt,backend,traffic_system.html,driver.html,css,js,system_checkpoint.json,travel_time_database.json -DestinationPath pythonanywhere_deploy.zip -Force
```

**手动打包：**
将上述文件和目录压缩成 `pythonanywhere_deploy.zip`

---

### 步骤 2️⃣: 上传到 PythonAnywhere

1. 登录 [www.pythonanywhere.com](https://www.pythonanywhere.com)
2. 点击 **Files** 标签
3. 点击 **Upload a file** 上传 `pythonanywhere_deploy.zip`
4. 在 Bash Console 中解压：
   ```bash
   cd ~
   unzip pythonanywhere_deploy.zip
   ```

---

### 步骤 3️⃣: 安装依赖

在 **Bash Console** 中运行：
```bash
pip3.10 install --user -r requirements.txt
```

等待安装完成（约2-5分钟）

---

### 步骤 4️⃣: 配置 Web 应用

1. 点击 **Web** 标签
2. 点击 **Add a new web app**
3. 选择 **Flask**
4. 选择 **Python 3.10**
5. 设置路径为默认（会自动创建）

**编辑 WSGI 配置文件：**

点击 WSGI configuration file 链接，替换全部内容为：

```python
import sys

# 添加项目路径（替换 YOUR_USERNAME 为你的用户名）
path = '/home/YOUR_USERNAME'
if path not in sys.path:
    sys.path.insert(0, path)

# 导入 Flask 应用
from app import app as application
```

**重要**: 将 `YOUR_USERNAME` 替换为你的 PythonAnywhere 用户名！

---

### 步骤 5️⃣: 配置静态文件（可选但推荐）

在 **Web** 标签的 **Static files** 部分添加：

| URL | Directory |
|-----|-----------|
| `/js/` | `/home/YOUR_USERNAME/js` |
| `/css/` | `/home/YOUR_USERNAME/css` |

**替换 YOUR_USERNAME 为你的用户名！**

点击页面顶部绿色的 **Reload** 按钮

---

## ✅ 访问你的网站

部署完成后，访问：
- **管理端**: `https://YOUR_USERNAME.pythonanywhere.com/`
- **司机端**: `https://YOUR_USERNAME.pythonanywhere.com/driver`

---

## ⚠️ 重要提示

### 1. WebSocket 限制
PythonAnywhere **免费账户不支持 WebSocket**：
- 实时更新功能会降级为轮询模式
- 功能不受影响，只是更新频率稍慢
- 如需 WebSocket，需升级到付费账户

### 2. 内存限制
免费账户内存限制：
- 检查 Web 标签页的内存使用情况
- 如果超限，考虑删除不用的数据文件

### 3. 文件存储
- 免费账户有 512MB 存储限制
- 定期清理不需要的备份文件

---

## 🔧 常见问题

### 问题 1: 页面显示 "500 Internal Server Error"

**解决方法：**
1. 查看错误日志：Web 标签 → Log files → Error log
2. 常见原因：
   - 依赖包未安装完整
   - WSGI 文件路径错误
   - Python 版本不匹配

**快速修复：**
```bash
# 重新安装依赖
pip3.10 install --user -r requirements.txt --force-reinstall
```

### 问题 2: 样式/JS 文件加载失败

**解决方法：**
1. 检查 Static files 配置是否正确
2. 确认文件路径大小写一致
3. 点击 Reload 重启应用

### 问题 3: 找不到模块

**解决方法：**
检查 WSGI 文件中的路径，确保指向包含 `app.py` 的目录：
```python
# 如果 app.py 在 /home/username/ 下
path = '/home/username'

# 如果 app.py 在 /home/username/mysite/ 下
path = '/home/username/mysite'
```

---

## 📱 测试清单

部署后测试：
- [ ] 管理端页面能正常打开
- [ ] 司机端页面能正常打开
- [ ] 能添加节点和道路
- [ ] 能添加车辆
- [ ] 能进行路径规划
- [ ] CSS 样式正常加载
- [ ] JavaScript 功能正常

---

## 🎯 一键部署脚本

创建 `deploy_to_pythonanywhere.ps1`：

```powershell
# PythonAnywhere 快速部署脚本

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PythonAnywhere 部署打包工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查必需文件
$requiredFiles = @("app.py", "requirements.txt", "traffic_system.html", "driver.html")
$missing = @()

foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        $missing += $file
    }
}

if ($missing.Count -gt 0) {
    Write-Host "❌ 缺少必需文件：" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "   - $_" -ForegroundColor Red }
    exit 1
}

# 打包文件
Write-Host "📦 正在打包文件..." -ForegroundColor Yellow
$items = @(
    "app.py",
    "requirements.txt",
    "backend",
    "traffic_system.html",
    "driver.html",
    "css",
    "js"
)

# 添加可选文件（如果存在）
if (Test-Path "system_checkpoint.json") { $items += "system_checkpoint.json" }
if (Test-Path "travel_time_database.json") { $items += "travel_time_database.json" }

try {
    Compress-Archive -Path $items -DestinationPath "pythonanywhere_deploy.zip" -Force
    Write-Host "✅ 打包成功！" -ForegroundColor Green
    Write-Host ""
    Write-Host "📦 文件已保存为: pythonanywhere_deploy.zip" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "接下来的步骤：" -ForegroundColor Yellow
    Write-Host "1. 登录 www.pythonanywhere.com" -ForegroundColor White
    Write-Host "2. 上传 pythonanywhere_deploy.zip" -ForegroundColor White
    Write-Host "3. 在 Bash Console 中运行: unzip pythonanywhere_deploy.zip" -ForegroundColor White
    Write-Host "4. 运行: pip3.10 install --user -r requirements.txt" -ForegroundColor White
    Write-Host "5. 配置 WSGI 文件" -ForegroundColor White
    Write-Host ""
    Write-Host "详细步骤请查看: 快速部署指南_PythonAnywhere.md" -ForegroundColor Cyan
} catch {
    Write-Host "❌ 打包失败: $_" -ForegroundColor Red
    exit 1
}
```

---

## 🌟 就这么简单！

1. ✅ 运行打包脚本
2. ✅ 上传 zip 文件
3. ✅ 解压并安装依赖
4. ✅ 配置 WSGI
5. ✅ 点击 Reload

**5步完成，开始使用！** 🎉













