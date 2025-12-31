# PythonAnywhere 快速部署脚本
# 使用方法: 在 PowerShell 中运行 .\deploy_to_pythonanywhere.ps1

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

Write-Host "✅ 所有必需文件检查通过" -ForegroundColor Green
Write-Host ""

# 检查目录
$requiredDirs = @("backend", "css", "js")
$missingDirs = @()

foreach ($dir in $requiredDirs) {
    if (-not (Test-Path $dir)) {
        $missingDirs += $dir
    }
}

if ($missingDirs.Count -gt 0) {
    Write-Host "❌ 缺少必需目录：" -ForegroundColor Red
    $missingDirs | ForEach-Object { Write-Host "   - $_" -ForegroundColor Red }
    exit 1
}

Write-Host "✅ 所有必需目录检查通过" -ForegroundColor Green
Write-Host ""

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
if (Test-Path "system_checkpoint.json") { 
    $items += "system_checkpoint.json"
    Write-Host "   ✓ 包含 system_checkpoint.json" -ForegroundColor Gray
}
if (Test-Path "travel_time_database.json") { 
    $items += "travel_time_database.json"
    Write-Host "   ✓ 包含 travel_time_database.json" -ForegroundColor Gray
}

Write-Host ""

try {
    # 如果已存在旧的压缩包，先删除
    if (Test-Path "pythonanywhere_deploy.zip") {
        Remove-Item "pythonanywhere_deploy.zip" -Force
    }
    
    Compress-Archive -Path $items -DestinationPath "pythonanywhere_deploy.zip" -Force
    
    $fileSize = (Get-Item "pythonanywhere_deploy.zip").Length / 1MB
    
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✅ 打包成功！" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "📦 文件名: pythonanywhere_deploy.zip" -ForegroundColor Cyan
    Write-Host "📊 文件大小: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "  接下来的部署步骤" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "步骤 1: 登录 PythonAnywhere" -ForegroundColor White
    Write-Host "   访问: https://www.pythonanywhere.com" -ForegroundColor Gray
    Write-Host ""
    Write-Host "步骤 2: 上传文件" -ForegroundColor White
    Write-Host "   Files → Upload a file → 选择 pythonanywhere_deploy.zip" -ForegroundColor Gray
    Write-Host ""
    Write-Host "步骤 3: 解压文件" -ForegroundColor White
    Write-Host "   在 Bash Console 中运行:" -ForegroundColor Gray
    Write-Host "   cd ~" -ForegroundColor Cyan
    Write-Host "   unzip pythonanywhere_deploy.zip" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "步骤 4: 安装依赖" -ForegroundColor White
    Write-Host "   pip3.10 install --user -r requirements.txt" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "步骤 5: 配置 WSGI" -ForegroundColor White
    Write-Host "   Web → Add a new web app → Flask → Python 3.10" -ForegroundColor Gray
    Write-Host "   编辑 WSGI 文件，复制以下内容（替换 YOUR_USERNAME）:" -ForegroundColor Gray
    Write-Host ""
    Write-Host "   import sys" -ForegroundColor Cyan
    Write-Host "   path = '/home/YOUR_USERNAME'" -ForegroundColor Cyan
    Write-Host "   if path not in sys.path:" -ForegroundColor Cyan
    Write-Host "       sys.path.insert(0, path)" -ForegroundColor Cyan
    Write-Host "   from app import app as application" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "步骤 6: 重启应用" -ForegroundColor White
    Write-Host "   Web → 点击绿色 Reload 按钮" -ForegroundColor Gray
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "完成！访问你的网站：" -ForegroundColor Green
    Write-Host "https://YOUR_USERNAME.pythonanywhere.com" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "📖 详细文档: 快速部署指南_PythonAnywhere.md" -ForegroundColor Yellow
    Write-Host ""
} catch {
    Write-Host "❌ 打包失败: $_" -ForegroundColor Red
    exit 1
}













