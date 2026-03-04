# AI 问答助手（多模型接入）

这是一个可扩展的 AI 问答助手示例，支持通过统一接口接入多个模型提供商：

- OpenAI（`openai`）
- Anthropic（`anthropic`）
- Ollama（`ollama`，本地模型）

## 功能特点

- 统一的 `ChatProvider` 抽象，方便后续扩展更多模型平台。
- 通过环境变量配置模型、URL 和 API Key。
- 提供命令行问答入口：`python -m app.main`。
- 内置基础错误处理与参数校验。

## 快速开始

### 1) 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) 配置环境变量

复制 `.env.example` 为 `.env`，然后按需填写：

```bash
cp .env.example .env
```

#### OpenAI 示例

```env
AI_PROVIDER=openai
AI_MODEL=gpt-4o-mini
OPENAI_API_KEY=your_openai_api_key
```

#### Anthropic 示例

```env
AI_PROVIDER=anthropic
AI_MODEL=claude-3-5-sonnet-latest
ANTHROPIC_API_KEY=your_anthropic_api_key
```

#### Ollama 示例

```env
AI_PROVIDER=ollama
AI_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://localhost:11434
```

### 3) 运行

```bash
python -m app.main "请解释什么是向量数据库"
```

或交互模式：

```bash
python -m app.main
```

## 扩展新模型提供商

1. 在 `app/providers.py` 中新增 provider 类并实现 `chat()`。
2. 在 `build_provider()` 中注册新 provider。
3. 增加对应环境变量读取逻辑即可。

## 注意

- 本项目示例使用各家 HTTP API，需确保网络和 API Key 可用。
- 如果使用 Ollama，请先本地安装并拉取模型。
