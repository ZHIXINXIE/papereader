# Paper Reader / 论文阅读助手

Paper Reader is a local AI-powered academic paper reading assistant. It helps you manage reading lists, automatically download papers from Arxiv/OpenReview, and uses Gemini 3 to interpret and summarize papers.
Paper Reader 是一个本地 AI 驱动的学术论文阅读助手。它帮助你管理阅读清单，自动从 Arxiv/OpenReview 下载论文，并使用 Gemini 3 来解读和总结论文。

## Features / 功能特性

- **Task Management**: Create reading tasks and organize papers.
  **任务管理**：创建阅读任务并组织论文。
- **Auto Download**: Automatically search and download PDFs from Arxiv and OpenReview.
  **自动下载**：自动从 Arxiv 和 OpenReview 搜索并下载 PDF。
- **AI Interpretation**: Use Google Gemini models to summarize and chat with papers.
  **AI 解读**：使用 Google Gemini 模型总结论文并进行对话。
- **Local Storage**: All PDFs and data are stored locally on your machine.
  **本地存储**：所有 PDF 和数据都存储在你的本地机器上。
- **Reading Room**: Dedicated interface for reading and chatting with papers.
  **阅读室**：专用于阅读和与论文对话的界面。

## Prerequisites / 前置要求

Before you begin, ensure you have the following installed:
在开始之前，请确保你已经安装了以下软件：

1.  **Python 3.10+**: [Download Python](https://www.python.org/downloads/)
    **Python 3.10+**：[下载 Python](https://www.python.org/downloads/)
2.  **Node.js 18+**: [Download Node.js](https://nodejs.org/) (Includes npm)
    **Node.js 18+**：[下载 Node.js](https://nodejs.org/)（包含 npm）

## Installation & Setup / 安装与配置

### 1. Clone the Repository / 克隆仓库

```bash
git clone <repository_url>
cd code
```

### 2. Configure Environment Variables / 配置环境变量

You need a Google Gemini API Key to use the AI features.
你需要一个 Google Gemini API Key 来使用 AI 功能。

1.  Get your API Key from [Google AI Studio](https://aistudio.google.com/).
    从 [Google AI Studio](https://aistudio.google.com/) 获取你的 API Key。
2.  Create a `.env` file in the `backend` directory:
    在 `backend` 目录下创建一个 `.env` 文件：

    **Windows (PowerShell):**
    ```powershell
    cd backend
    New-Item .env -Type File
    Set-Content .env "GEMINI_API_KEY=your_api_key_here"
    ```

    **Mac/Linux:**
    ```bash
    cd backend
    echo "GEMINI_API_KEY=your_api_key_here" > .env
    ```

    *(Replace `your_api_key_here` with your actual API key)*
    *（将 `your_api_key_here` 替换为你实际的 API key）*

### 3. Install Dependencies / 安装依赖

**Backend (Python) / 后端 (Python):**

It is recommended to use a virtual environment.
推荐使用虚拟环境。

```bash
# Create virtual environment with Conda / 使用 Conda 创建虚拟环境
conda create -n paperreader python=3.10

# Activate virtual environment / 激活虚拟环境
conda activate paperreader

# Install requirements / 安装依赖包
pip install -r backend/requirements.txt
```

**Frontend (Node.js) / 前端 (Node.js):**

The startup script will handle this automatically, but you can also install manually:
启动脚本会自动处理此步骤，但你也可以手动安装：

```bash
cd frontend
npm install
```

## Running the Application / 运行应用

We provide a convenient startup script that launches both the backend and frontend services.
我们提供了一个便捷的启动脚本，可以同时启动后端和前端服务。

**Make sure you are in the root `code` directory.**
**请确保你位于根目录 `code` 下。**

```bash
# Ensure your virtual environment is activated if you used one
# 如果你使用了虚拟环境，请确保已激活
python start.py
```

- **Frontend / 前端**: http://localhost:5173 (Open this in your browser / 在浏览器中打开)
- **Backend API / 后端 API**: http://localhost:8000/docs

## Troubleshooting / 故障排除

-   **"GEMINI_API_KEY not found"**: Please configure your `GEMINI_API_KEY` in the environment variables.
    **"GEMINI_API_KEY not found"**：请在环境变量中配置你的 `GEMINI_API_KEY`。
-   **Node modules missing**: If `start.py` fails to install frontend dependencies, try running `npm install` manually inside the `frontend` folder.
    **Node modules missing**：如果 `start.py` 安装前端依赖失败，请尝试在 `frontend` 文件夹内手动运行 `npm install`。
-   **Port already in use**: Ensure ports 8000 (Backend) and 5173 (Frontend) are free.
    **Port already in use**：确保端口 8000 (后端) 和 5173 (前端) 未被占用。

## Project Structure / 项目结构

-   `backend/`: Python FastAPI application, database, and services.
    `backend/`：Python FastAPI 应用程序、数据库和服务。
-   `frontend/`: React + TypeScript + Vite application.
    `frontend/`：React + TypeScript + Vite 应用程序。
-   `data/`: Created automatically. Stores your database (`app.db`) and downloaded PDFs.
    `data/`：自动创建。存储你的数据库 (`app.db`) 和下载的 PDF 文件。
-   `start.py`: Launcher script.
    `start.py`：启动脚本。
