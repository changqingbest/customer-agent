import argparse
import json
import sys

from customer_agent.http_server import run_server
from customer_agent.service import CustomerServiceAgent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Foreign trade customer service Agent.")
    parser.add_argument("message", nargs="?", help="Visitor message.")
    parser.add_argument("--session-id", default="cli-demo")
    parser.add_argument("--country", default="")
    parser.add_argument("--email", default="")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.serve or not args.message:
        if not args.serve:
            print("No message provided. Starting web demo at http://127.0.0.1:8000")
        run_server(args.host, args.port)
        return 0

    agent = CustomerServiceAgent()
    response = agent.chat(
        session_id=args.session_id,
        message=args.message,
        visitor={"country": args.country, "email": args.email},
    )
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
