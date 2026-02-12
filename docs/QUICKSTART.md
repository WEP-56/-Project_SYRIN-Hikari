# Yandere Assistant - 病娇助手娘

## 快速启动

### 方法一：双击启动（推荐）
直接双击 `start.vbs` 文件

### 方法二：命令行
```powershell
# PowerShell
.\scripts\dev.ps1

# 或 CMD
powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
```

### 方法三：手动启动
```powershell
# 1. 确保 nanobot 已安装
cd nanobot-main
pip install -e .
cd ..

# 2. 安装依赖
npm install

# 3. 启动
npm run dev
```

## 首次使用

1. 启动后会自动打开应用窗口
2. 点击"设置"页面
3. 配置你的 API Key（OpenAI/DeepSeek 等）
4. 返回对话页面开始聊天

## 项目结构

- `src/` - 前端源码
- `python-server/` - Python API 服务
- `nanobot-main/` - nanobot 源码（需单独克隆）

## 注意事项

- 需要 Python 3.11+
- 需要 Node.js 18+
- Windows 10/11 系统
- 确保 nanobot-main 目录存在

## 技术支持

如有问题，请检查：
1. Python 是否正确安装并添加到 PATH
2. nanobot 是否已安装 (`pip list | grep nanobot`)
3. Node.js 依赖是否完整 (`npm install`)
