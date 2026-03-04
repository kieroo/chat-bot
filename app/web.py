from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import settings
from .providers import ProviderError, build_provider

DEFAULT_SYSTEM_PROMPT = "你是一个专业、简洁、乐于助人的 AI 助手。"

HTML_PAGE = """<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AI 问答助手</title>
    <style>
      :root {
        font-family: "Inter", "PingFang SC", "Microsoft YaHei", -apple-system, BlinkMacSystemFont,
          "Segoe UI", sans-serif;
        --bg: #f2f6ff;
        --card: rgba(255, 255, 255, 0.82);
        --text: #111827;
        --muted: #6b7280;
        --border: #d9e1f3;
        --primary: #3b82f6;
        --primary-deep: #2563eb;
        --success: #0f766e;
        --danger: #b91c1c;
      }
      body {
        margin: 0;
        display: grid;
        place-items: center;
        min-height: 100vh;
        color: var(--text);
        background: radial-gradient(circle at 10% 10%, #e0ecff 0%, #f5f8ff 45%, #eef3ff 100%);
      }
      body::before,
      body::after {
        content: "";
        position: fixed;
        width: 280px;
        height: 280px;
        border-radius: 50%;
        filter: blur(45px);
        z-index: -1;
        opacity: 0.45;
      }
      body::before {
        background: #93c5fd;
        top: -80px;
        left: -80px;
      }
      body::after {
        background: #c4b5fd;
        bottom: -110px;
        right: -80px;
      }
      .card {
        width: min(900px, 92vw);
        background: var(--card);
        border: 1px solid rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 24px;
        box-shadow: 0 18px 45px rgba(30, 64, 175, 0.12);
      }
      h1 {
        margin: 0 0 6px;
        font-size: 26px;
        letter-spacing: 0.02em;
      }
      p.meta {
        margin: 0 0 18px;
        color: var(--muted);
        font-size: 14px;
      }
      .meta-chip {
        display: inline-flex;
        align-items: center;
        margin-right: 6px;
        margin-top: 6px;
        padding: 4px 10px;
        border-radius: 999px;
        background: rgba(59, 130, 246, 0.1);
      }
      label {
        display: block;
        margin-bottom: 8px;
        font-size: 14px;
        color: #374151;
      }
      textarea {
        width: 100%;
        min-height: 88px;
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 12px 14px;
        box-sizing: border-box;
        resize: vertical;
        font-size: 15px;
        transition: all 0.2s ease;
        outline: none;
        background: rgba(255, 255, 255, 0.9);
      }
      textarea:focus {
        border-color: var(--primary);
        box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.16);
      }
      .row {
        margin-top: 14px;
        display: flex;
        gap: 10px;
      }
      button {
        border: 0;
        background: linear-gradient(135deg, var(--primary), var(--primary-deep));
        color: #fff;
        border-radius: 12px;
        padding: 11px 18px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        transition: transform 0.18s ease, box-shadow 0.18s ease, opacity 0.2s;
      }
      button:hover:not(:disabled) {
        transform: translateY(-1px);
        box-shadow: 0 10px 18px rgba(37, 99, 235, 0.25);
      }
      button:disabled {
        opacity: 0.65;
        cursor: not-allowed;
      }
      #clear {
        background: #fff;
        color: #374151;
        border: 1px solid var(--border);
      }
      #answer {
        margin-top: 18px;
        white-space: pre-wrap;
        line-height: 1.6;
        border-top: 1px solid #e5e7eb;
        padding: 16px 4px 2px;
        min-height: 120px;
      }
      #answer.typing {
        color: #334155;
      }
      #answer.success {
        color: var(--success);
      }
      .error {
        color: var(--danger);
      }
      .pulse {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #94a3b8;
        animation: blink 1s infinite ease-in-out;
      }
      @keyframes blink {
        0%,
        100% {
          transform: translateY(0);
          opacity: 0.3;
        }
        50% {
          transform: translateY(-2px);
          opacity: 1;
        }
      }
    </style>
  </head>
  <body>
    <main class="card">
      <h1>AI 问答助手界面</h1>
      <p class="meta">
        <span class="meta-chip">provider=<span id="provider"></span></span>
        <span class="meta-chip">model=<span id="model"></span></span>
      </p>
      <label for="system">系统提示词</label>
      <textarea id="system" placeholder="系统提示词"></textarea>
      <label for="question">输入你的问题</label>
      <textarea id="question" placeholder="例如：请解释什么是向量数据库"></textarea>
      <div class="row">
        <button id="send">发送</button>
        <button id="clear">清空</button>
      </div>
      <div id="answer"></div>
    </main>

    <script>
      const providerEl = document.getElementById('provider');
      const modelEl = document.getElementById('model');
      const systemEl = document.getElementById('system');
      const questionEl = document.getElementById('question');
      const answerEl = document.getElementById('answer');
      const sendBtn = document.getElementById('send');
      const clearBtn = document.getElementById('clear');

      const setLoadingState = (loading) => {
        sendBtn.disabled = loading;
        if (loading) {
          answerEl.className = 'typing';
          answerEl.innerHTML = '思考中 <span class="pulse"></span> <span class="pulse" style="animation-delay:0.15s"></span> <span class="pulse" style="animation-delay:0.3s"></span>';
        }
      };

      const animateText = (text) => {
        answerEl.textContent = '';
        answerEl.className = 'success';
        let idx = 0;
        const timer = setInterval(() => {
          idx += 3;
          answerEl.textContent = text.slice(0, idx);
          if (idx >= text.length) {
            clearInterval(timer);
          }
        }, 12);
      };

      providerEl.textContent = %PROVIDER%;
      modelEl.textContent = %MODEL%;
      systemEl.value = %SYSTEM_PROMPT%;

      const submitQuestion = async () => {
        const question = questionEl.value.trim();
        if (!question) {
          answerEl.className = 'error';
          answerEl.textContent = '请先输入问题。';
          return;
        }

        setLoadingState(true);

        try {
          const resp = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              question,
              system_prompt: systemEl.value.trim(),
            }),
          });

          const data = await resp.json();
          if (!resp.ok) {
            answerEl.className = 'error';
            answerEl.textContent = data.error || '请求失败';
            return;
          }
          animateText(data.answer || '');
        } catch (err) {
          answerEl.className = 'error';
          answerEl.textContent = `网络错误: ${err}`;
        } finally {
          sendBtn.disabled = false;
        }
      };

      sendBtn.addEventListener('click', submitQuestion);
      clearBtn.addEventListener('click', () => {
        questionEl.value = '';
        answerEl.className = '';
        answerEl.textContent = '';
      });

      questionEl.addEventListener('keydown', (event) => {
        if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
          submitQuestion();
        }
      });
    </script>
  </body>
</html>
"""


class ChatUIHandler(BaseHTTPRequestHandler):
    provider = None

    def _json_response(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path not in {"/", "/index.html"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        page = (
            HTML_PAGE.replace("%PROVIDER%", json.dumps(settings.provider, ensure_ascii=False))
            .replace("%MODEL%", json.dumps(settings.model, ensure_ascii=False))
            .replace("%SYSTEM_PROMPT%", json.dumps(DEFAULT_SYSTEM_PROMPT, ensure_ascii=False))
        ).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path != "/api/chat":
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        content_len = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_len)
        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._json_response({"error": "请求体必须是合法 JSON。"}, status=HTTPStatus.BAD_REQUEST)
            return

        question = str(data.get("question", "")).strip()
        system_prompt = str(data.get("system_prompt", "")).strip() or None
        if not question:
            self._json_response({"error": "question 不能为空。"}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            if self.provider is None:
                self._json_response({"error": "Provider 未初始化。"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            answer = self.provider.chat(question, system_prompt=system_prompt)
        except ProviderError as exc:
            self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
            return

        self._json_response({"answer": answer})


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="启动 AI 问答助手网页界面")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        ChatUIHandler.provider = build_provider(settings)
    except ProviderError as exc:
        print(f"启动失败: {exc}")
        return 2

    server = ThreadingHTTPServer((args.host, args.port), ChatUIHandler)
    print(f"界面已启动: http://{args.host}:{args.port}")
    print(f"当前 provider={settings.provider}, model={settings.model}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n正在关闭...")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
