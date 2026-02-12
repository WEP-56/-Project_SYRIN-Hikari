# 快速启动脚本

$ErrorActionPreference = "Stop"

Write-Host "🎀 启动病娇助手娘..." -ForegroundColor Magenta
Write-Host ""

# 检查 Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "❌ 错误: 未找到 Python" -ForegroundColor Red
    Write-Host "请先安装 Python 3.11+: https://python.org"
    exit 1
}

# 检查 Node.js
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    Write-Host "❌ 错误: 未找到 Node.js" -ForegroundColor Red
    Write-Host "请先安装 Node.js 18+: https://nodejs.org"
    exit 1
}

# 安装 nanobot
Write-Host "📦 检查 nanobot..." -ForegroundColor Cyan
if (-not (Test-Path "./nanobot-main")) {
    Write-Host "❌ 错误: 未找到 nanobot-main 目录" -ForegroundColor Red
    exit 1
}

try {
    $null = python -c "import nanobot" 2>$null
    Write-Host "✓ nanobot 已安装" -ForegroundColor Green
} catch {
    Write-Host "⚙️ 安装 nanobot..." -ForegroundColor Yellow
    Push-Location nanobot-main
    pip install -e . | Out-Null
    Pop-Location
    Write-Host "✓ nanobot 安装完成" -ForegroundColor Green
}

# 安装前端依赖
Write-Host ""
Write-Host "📦 检查前端依赖..." -ForegroundColor Cyan
if (-not (Test-Path "./node_modules")) {
    Write-Host "⚙️ 安装 npm 依赖..." -ForegroundColor Yellow
    npm install
}
Write-Host "✓ 前端依赖已就绪" -ForegroundColor Green

# 启动开发服务器
Write-Host ""
Write-Host "🚀 启动开发服务器..." -ForegroundColor Cyan
Write-Host ""

npm run dev
