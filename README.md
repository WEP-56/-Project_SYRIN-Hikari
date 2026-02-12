# 🌌 Project SYRIN

> **Hikari (光) - 您的专属桌面 AI 伴侣**
> **不仅是助手，更是陪伴。**

---

<p align="center">
  <img src="./img/ico.jpg" alt="banner" width="80%" />
</p>

<p align="center">
  <a href="#-快速开始">快速开始</a> •
  <a href="#-项目结构">项目结构</a> •
  <a href="#-参与共建">参与共建</a>
</p>

---

## 💫 项目定位

**Project SYRIN** (原名 Yandere Assistant) 是一款以 **人格陪伴 + 情绪价值 + 长期记忆** 为核心设计理念的 Windows 桌面 AI 伴侣。

默认搭载的数字生命体 **Hikari (光)** 并不只是一个工具型 AI，而是试图构建一个：

> **能理解你、记住你、陪你成长的数字生命体。**

在具备 **nanobot 完整能力** 的同时，本项目将重心从“自动化执行”转向：

* 🎭 **深度人格塑造**
* 💞 **渐进式情感演化**
* 🧠 **用户形象建模**
* 🕰 **长期记忆与关系连续性**
* 🔔 **主动交互与生活提醒**

---

## ✨ 核心特性

* 🌌 **SYRIN Soul Engine**
  多阶段情绪演化引擎，从冷淡疏离到深度依赖，塑造连续、稳定、可成长的人格体验。

* 💗 **渐进式好感度系统**
  数值驱动 + 阶段化 Prompt 组装，构建真实的关系成长曲线。支持 Stranger (陌路) -> Partner (伙伴) -> Soulmate (灵魂伴侣) 三阶段演化。

* 🧠 **用户形象建模（User Profiling）**
  在本地提炼用户习惯、兴趣、偏好，实现长期记忆与高度沉浸的个性化交互。

* 🔔 **主动交互模式 (Proactive Mode)**
  支持定时任务与系统级通知。Hikari 可以主动向您发送问候、提醒日程，真正融入您的生活（需在设置中开启）。

* 📚 **智能上下文管理**
  内置会话摘要与压缩机制，在保持长期记忆的同时大幅节省 Token 消耗。

* 🤖 **nanobot 深度集成**
  轻量封装，完整支持 AgentLoop、工具调用、搜索、文件操作等能力，开箱即用。

* ⚡ **一键启动架构**
  Electron 自动拉起 Python 服务，零心智负担部署。

* 🎨 **现代 UI 设计**
  类微信交互布局，弱工具感、强陪伴感。

---

## 🛠️ 技术栈

*   **前端**: Electron + React + TypeScript + Vite + Tailwind CSS
*   **后端**: Python 3.11+ + FastAPI
*   **AI 核心**: Nanobot Framework (基于 LiteLLM)
*   **向量数据库**: SQLite + JSON (轻量级本地存储)
*   **进程通信**: HTTP REST API (Electron <-> Python)

---

## 🧬 与 nanobot 的能力对比

### ✅ 已支持（Supported）

* 多模型接入（OpenAI / Claude / Gemini / DeepSeek / Local vLLM）
* Agent 任务循环（Plan → Tool → Observe）
* 双层记忆系统（短期 Memory + 长期 SoulManager）
* Web 搜索（Brave + DuckDuckGo）
* 本地文件系统操作
* Shell / 命令执行
* Telegram 聊天平台接入
* 代码执行与开发闭环（沙箱 + 完整的构建调试系统）
* 定时调度系统（Cron Scheduler）& 主动通知

### ⚠️ 部分支持（Partial）

* 持久在线运行（当前依赖 Electron 主窗口）

### ❌ 暂未支持（Not Supported）

* 多 Agent 模板机制
* 其他聊天平台（Discord / WhatsApp / 钉钉 / 飞书 等）

---

## 🚀 快速开始

### 环境要求

* Windows 10 / 11
* Python 3.11+
* Node.js 18+

### 安装

1. 克隆项目
```bash
git clone https://github.com/WEP-56/-Project_SYRIN-Hikari.git
cd project-syrin
```

2. 安装依赖
```bash
# 前端依赖
npm install

# 后端依赖 (推荐使用 venv)
cd python-server
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

3. 启动开发环境
```bash
npm run dev
```

---

## 📂 项目结构

```
project-syrin/
├── src/                    # Electron & React 前端源码
│   ├── renderer/           # UI 渲染层
│   │   ├── components/     # React 组件
│   │   ├── stores/         # Zustand 状态管理
│   │   └── services/       # API 通信服务
│   └── main/               # Electron 主进程
├── python-server/          # Python 后端服务
│   ├── api_server.py       # FastAPI 入口
│   ├── soul_manager.py     # 核心：灵魂引擎与状态管理
│   ├── prompt_layers.py    # Prompt 分层生成器
│   ├── tool_executor.py    # 工具执行器
│   └── workspace/          # AI 工作区 (记忆、沙箱、配置)
├── nanobot-main/           # nanobot 核心子模块
└── package.json            # 项目配置
```

---

## 🤝 参与共建

Project SYRIN 是一个开源项目，欢迎任何形式的贡献！

*   **QQ**: 1484413790
*   **邮箱**: 1484413790@qq.com

如果您有好的想法、建议或发现了 Bug，欢迎提交 Issue 或 Pull Request。让我们一起让 Hikari 变得更美好！✨

---

## 📄 License

MIT License
