#!/bin/bash
# PythonAnywhere 部署打包脚本 (Bash)
# 使用方法: ./pack_for_deploy.sh

echo "🚀 开始打包部署文件..."

# 创建临时目录
TEMP_DIR="deploy_temp"
if [ -d "$TEMP_DIR" ]; then
    rm -rf "$TEMP_DIR"
fi
mkdir -p "$TEMP_DIR"

echo "📁 复制核心文件..."

# 复制核心文件
cp app.py "$TEMP_DIR/" 2>/dev/null || echo "❌ app.py 不存在"
cp requirements.txt "$TEMP_DIR/" 2>/dev/null || echo "❌ requirements.txt 不存在"
cp traffic_system.html "$TEMP_DIR/" 2>/dev/null || echo "❌ traffic_system.html 不存在"
cp driver.html "$TEMP_DIR/" 2>/dev/null || echo "❌ driver.html 不存在"

# 检查文件是否存在
MISSING_FILES=()
[ ! -f "$TEMP_DIR/app.py" ] && MISSING_FILES+=("app.py")
[ ! -f "$TEMP_DIR/requirements.txt" ] && MISSING_FILES+=("requirements.txt")
[ ! -f "$TEMP_DIR/traffic_system.html" ] && MISSING_FILES+=("traffic_system.html")
[ ! -f "$TEMP_DIR/driver.html" ] && MISSING_FILES+=("driver.html")

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo "❌ 缺少必需文件: ${MISSING_FILES[*]}"
    rm -rf "$TEMP_DIR"
    exit 1
fi

echo "📁 复制 backend 目录（排除 __pycache__）..."

# 复制 backend 目录，排除 __pycache__ 和 *.pyc
if [ -d "backend" ]; then
    rsync -av --exclude='__pycache__' --exclude='*.pyc' --exclude='*.pyo' backend/ "$TEMP_DIR/backend/"
else
    echo "❌ backend 目录不存在！"
    rm -rf "$TEMP_DIR"
    exit 1
fi

echo "📁 复制 css 目录..."
if [ -d "css" ]; then
    cp -r css "$TEMP_DIR/"
else
    echo "⚠️  css 目录不存在，跳过"
fi

echo "📁 复制 js 目录..."
if [ -d "js" ]; then
    cp -r js "$TEMP_DIR/"
else
    echo "❌ js 目录不存在！"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# 检查 js 目录中的必需文件
REQUIRED_JS_FILES=("api.js" "app-main.js" "charts.js" "config.js" "ui-manager.js" "utils.js" "websocket.js")
MISSING_JS_FILES=()
for file in "${REQUIRED_JS_FILES[@]}"; do
    if [ ! -f "$TEMP_DIR/js/$file" ]; then
        MISSING_JS_FILES+=("$file")
    fi
done

if [ ${#MISSING_JS_FILES[@]} -gt 0 ]; then
    echo "⚠️  js 目录缺少文件: ${MISSING_JS_FILES[*]}"
fi

echo "📦 创建压缩包..."

# 删除旧的压缩包
[ -f "deploy.zip" ] && rm -f "deploy.zip"

# 压缩
cd "$TEMP_DIR"
zip -r ../deploy.zip . > /dev/null
cd ..

# 清理临时目录
rm -rf "$TEMP_DIR"

# 显示文件大小
ZIP_SIZE=$(du -h deploy.zip | cut -f1)
echo ""
echo "✅ 部署包已创建: deploy.zip ($ZIP_SIZE)"
echo ""
echo "📋 包含的文件:"
echo "  ✓ app.py"
echo "  ✓ requirements.txt"
echo "  ✓ traffic_system.html"
echo "  ✓ driver.html"
echo "  ✓ backend/ (完整目录)"
echo "  ✓ css/ (如果存在)"
echo "  ✓ js/ (完整目录)"
echo ""
echo "🚀 下一步:"
echo "  1. 登录 PythonAnywhere"
echo "  2. 上传 deploy.zip 到 /home/yourusername/"
echo "  3. 解压: unzip deploy.zip"
echo "  4. 安装依赖: pip3.10 install --user -r requirements.txt"
echo "  5. 配置 WSGI 文件"
echo "  6. 重启应用"






