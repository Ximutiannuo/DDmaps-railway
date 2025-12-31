# PythonAnywhere 部署打包脚本 (PowerShell)
# 使用方法: .\pack_for_deploy.ps1

Write-Host "🚀 开始打包部署文件..." -ForegroundColor Green

# 创建临时目录
$tempDir = "deploy_temp"
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

Write-Host "📁 复制核心文件..." -ForegroundColor Yellow

# 复制核心文件
Copy-Item app.py $tempDir\ -ErrorAction SilentlyContinue
Copy-Item requirements.txt $tempDir\ -ErrorAction SilentlyContinue
Copy-Item traffic_system.html $tempDir\ -ErrorAction SilentlyContinue
Copy-Item driver.html $tempDir\ -ErrorAction SilentlyContinue

# 检查文件是否存在
$missingFiles = @()
if (-not (Test-Path "$tempDir\app.py")) { $missingFiles += "app.py" }
if (-not (Test-Path "$tempDir\requirements.txt")) { $missingFiles += "requirements.txt" }
if (-not (Test-Path "$tempDir\traffic_system.html")) { $missingFiles += "traffic_system.html" }
if (-not (Test-Path "$tempDir\driver.html")) { $missingFiles += "driver.html" }

if ($missingFiles.Count -gt 0) {
    Write-Host "❌ 缺少必需文件: $($missingFiles -join ', ')" -ForegroundColor Red
    Remove-Item -Recurse -Force $tempDir
    exit 1
}

Write-Host "📁 复制 backend 目录（排除 __pycache__）..." -ForegroundColor Yellow

# 复制 backend 目录，排除 __pycache__ 和 *.pyc
if (Test-Path "backend") {
    Get-ChildItem -Path backend -Recurse | Where-Object {
        $_.FullName -notmatch '__pycache__' -and
        $_.Extension -ne '.pyc' -and
        $_.Extension -ne '.pyo'
    } | ForEach-Object {
        $relativePath = $_.FullName.Substring((Get-Location).Path.Length + 1)
        $destPath = Join-Path $tempDir $relativePath
        $destDir = Split-Path $destPath -Parent
        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        }
        if (-not $_.PSIsContainer) {
            Copy-Item $_.FullName $destPath -ErrorAction SilentlyContinue
        }
    }
} else {
    Write-Host "❌ backend 目录不存在！" -ForegroundColor Red
    Remove-Item -Recurse -Force $tempDir
    exit 1
}

Write-Host "📁 复制 css 目录..." -ForegroundColor Yellow
if (Test-Path "css") {
    Copy-Item -Recurse css $tempDir\ -ErrorAction SilentlyContinue
} else {
    Write-Host "⚠️  css 目录不存在，跳过" -ForegroundColor Yellow
}

Write-Host "📁 复制 js 目录..." -ForegroundColor Yellow
if (Test-Path "js") {
    Copy-Item -Recurse js $tempDir\ -ErrorAction SilentlyContinue
} else {
    Write-Host "❌ js 目录不存在！" -ForegroundColor Red
    Remove-Item -Recurse -Force $tempDir
    exit 1
}

# 检查 js 目录中的必需文件
$requiredJsFiles = @("api.js", "app-main.js", "charts.js", "config.js", "ui-manager.js", "utils.js", "websocket.js")
$jsFiles = Get-ChildItem -Path "$tempDir\js" -File | Select-Object -ExpandProperty Name
$missingJsFiles = $requiredJsFiles | Where-Object { $jsFiles -notcontains $_ }

if ($missingJsFiles.Count -gt 0) {
    Write-Host "⚠️  js 目录缺少文件: $($missingJsFiles -join ', ')" -ForegroundColor Yellow
}

Write-Host "📦 创建压缩包..." -ForegroundColor Yellow

# 删除旧的压缩包
if (Test-Path "deploy.zip") {
    Remove-Item "deploy.zip" -Force
}

# 压缩
Compress-Archive -Path "$tempDir\*" -DestinationPath "deploy.zip" -Force

# 清理临时目录
Remove-Item -Recurse -Force $tempDir

# 显示文件大小
$zipSize = (Get-Item "deploy.zip").Length / 1MB
Write-Host ""
Write-Host "✅ 部署包已创建: deploy.zip ($([math]::Round($zipSize, 2)) MB)" -ForegroundColor Green
Write-Host ""
Write-Host "📋 包含的文件:" -ForegroundColor Cyan
Write-Host "  ✓ app.py" -ForegroundColor Green
Write-Host "  ✓ requirements.txt" -ForegroundColor Green
Write-Host "  ✓ traffic_system.html" -ForegroundColor Green
Write-Host "  ✓ driver.html" -ForegroundColor Green
Write-Host "  ✓ backend/ (完整目录)" -ForegroundColor Green
Write-Host "  ✓ css/ (如果存在)" -ForegroundColor Green
Write-Host "  ✓ js/ (完整目录)" -ForegroundColor Green
Write-Host ""
Write-Host "🚀 下一步:" -ForegroundColor Yellow
Write-Host "  1. 登录 PythonAnywhere" -ForegroundColor White
Write-Host "  2. 上传 deploy.zip 到 /home/yourusername/" -ForegroundColor White
Write-Host "  3. 解压: unzip deploy.zip" -ForegroundColor White
Write-Host "  4. 安装依赖: pip3.10 install --user -r requirements.txt" -ForegroundColor White
Write-Host "  5. 配置 WSGI 文件" -ForegroundColor White
Write-Host "  6. 重启应用" -ForegroundColor White






