# Yandere Assistant 项目结构

```
yandere-assistant/
├── 📦 package.json              # 项目配置
├── 📦 tsconfig.json            # TypeScript 配置
├── 📦 tsconfig.main.json       # 主进程 TS 配置
├── 📦 tsconfig.node.json       # Node TS 配置
├── 📦 vite.config.ts           # Vite 配置
├── 📦 tailwind.config.js       # Tailwind CSS 配置
├── 📄 index.html               # 入口 HTML
├── 📄 README.md                # 项目说明
├── 📄 .editorconfig            # 编辑器配置
│
├── 🔧 scripts/                 # 脚本工具
│   └── dev.ps1                # PowerShell 启动脚本
│
├── 🎨 src/                     # 源代码
│   ├── 📺 main/               # Electron 主进程
│   │   ├── index.ts          # 主入口（启动 Python 服务）
│   │   └── preload.ts        # 预加载脚本（IPC 桥接）
│   │
│   └── 🖼️ renderer/           # React 前端
│       ├── main.tsx          # React 入口
│       ├── App.tsx           # 主应用组件
│       ├── styles.css        # 全局样式
│       ├── types.ts          # TypeScript 类型
│       │
│       ├── components/       # 组件
│       │   ├── ChatInterface.tsx    # 聊天界面
│       │   ├── SettingsPanel.tsx    # 设置面板
│       │   └── StatusBar.tsx        # 状态栏
│       │
│       └── services/         # 服务
│           └── api.ts        # API 封装
│
├── 🐍 python-server/          # Python API 服务
│   ├── api_server.py         # FastAPI 封装 nanobot
│   └── requirements.txt      # Python 依赖
│
├── 🤖 nanobot-main/           # nanobot 源码（需单独克隆）
│   └── ...                   # nanobot 项目文件
│
└── 🎨 assets/                 # 静态资源
    └── icon.ico              # 应用图标
```

## 架构说明

### 三层架构

1. **Electron 前端** (React)
   - 聊天界面
   - 设置管理
   - 人格状态展示

2. **Node 中控** (Electron Main)
   - 自动启动 Python 服务
   - 系统级操作
   - 配置持久化

3. **Python 服务** (FastAPI)
   - 轻量封装 nanobot
   - 工具执行
   - AI 对话接口

### 通信流程

```
用户输入 → React UI → Electron IPC → Python API → nanobot → LLM
                                                     ↓
响应 ← React UI ← Electron IPC ← Python API ← 执行结果
```

## 开发流程

1. 启动应用：`./scripts/dev.ps1`
2. 前端开发：修改 `src/renderer/`
3. 后端调整：修改 `python-server/`
4. 打包：`npm run package:win`
