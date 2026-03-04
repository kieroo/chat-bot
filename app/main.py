from __future__ import annotations

import argparse
import sys

from .config import settings
from .providers import ProviderError, build_provider


DEFAULT_SYSTEM_PROMPT = "你是一个专业、简洁、乐于助人的 AI 助手。"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="多模型 AI 问答助手")
    parser.add_argument("question", nargs="?", help="用户问题，不传则进入交互模式")
    parser.add_argument("--system", default=DEFAULT_SYSTEM_PROMPT, help="系统提示词")
    return parser.parse_args(argv)


def interactive_chat(system_prompt: str) -> int:
    provider = build_provider(settings)
    print(f"已连接 provider={settings.provider}, model={settings.model}")
    print("输入 exit 或 quit 退出。")
    while True:
        try:
            question = input("\n你: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n退出。")
            return 0

        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            print("再见。")
            return 0

        answer = provider.chat(question, system_prompt=system_prompt)
        print(f"\n助手: {answer}")


def run_once(question: str, system_prompt: str) -> int:
    provider = build_provider(settings)
    answer = provider.chat(question, system_prompt=system_prompt)
    print(answer)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    args = parse_args(argv)

    try:
        if args.question:
            return run_once(args.question, system_prompt=args.system)
        return interactive_chat(system_prompt=args.system)
    except ProviderError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
