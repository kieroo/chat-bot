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
        color-scheme: light dark;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }
      body {
        margin: 0;
        display: grid;
        place-items: center;
        min-height: 100vh;
        background: #f5f7fb;
      }
      .card {
        width: min(900px, 92vw);
        background: #fff;
        border-radius: 14px;
        padding: 20px;
        box-shadow: 0 10px 32px rgba(0, 0, 0, 0.08);
      }
      h1 {
        margin: 0 0 10px;
        font-size: 22px;
      }
      p.meta {
        margin: 0 0 14px;
        color: #6b7280;
        font-size: 14px;
      }
      textarea {
        width: 100%;
        min-height: 100px;
        border: 1px solid #d1d5db;
        border-radius: 10px;
        padding: 12px;
        box-sizing: border-box;
        resize: vertical;
      }
      .row {
        margin-top: 12px;
        display: flex;
        gap: 8px;
      }
      button {
        border: 0;
        background: #2563eb;
        color: #fff;
        border-radius: 10px;
        padding: 10px 16px;
        cursor: pointer;
      }
      #answer {
        margin-top: 16px;
        white-space: pre-wrap;
        line-height: 1.6;
        border-top: 1px solid #e5e7eb;
        padding-top: 16px;
      }
      .error {
        color: #b91c1c;
      }
    </style>
  </head>
  <body>
    <main class="card">
      <h1>AI 问答助手界面</h1>
      <p class="meta">provider=<span id="provider"></span>, model=<span id="model"></span></p>
      <label for="system">系统提示词</label>
      <textarea id="system" placeholder="系统提示词"></textarea>
      <label for="question">输入你的问题</label>
      <textarea id="question" placeholder="例如：请解释什么是向量数据库"></textarea>
      <div class="row">
        <button id="send">发送</button>
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

      providerEl.textContent = %PROVIDER%;
      modelEl.textContent = %MODEL%;
      systemEl.value = %SYSTEM_PROMPT%;

      sendBtn.addEventListener('click', async () => {
        const question = questionEl.value.trim();
        if (!question) {
          answerEl.className = 'error';
          answerEl.textContent = '请先输入问题。';
          return;
        }

        sendBtn.disabled = true;
        answerEl.className = '';
        answerEl.textContent = '思考中...';

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
          answerEl.className = '';
          answerEl.textContent = data.answer || '';
        } catch (err) {
          answerEl.className = 'error';
          answerEl.textContent = `网络错误: ${err}`;
        } finally {
          sendBtn.disabled = false;
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
