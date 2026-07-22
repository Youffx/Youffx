#!/usr/bin/env python3
import argparse
import os
import sys
import json
import urllib.request
import urllib.parse

def send_telegram_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as response:
            return response.read()
    except Exception as e:
        print(f"Error sending Telegram message: {e}", file=sys.stderr)
        return None

def extract_error_log(log_path, lines_count=15):
    if not log_path or not os.path.exists(log_path):
        return "Log file not found."
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        error_lines = [line.strip() for line in lines if any(kw in line.lower() for kw in ["error:", "fatal:", "failed:"])]
        if error_lines:
            return "\n".join(error_lines[-lines_count:])
        return "\n".join([line.strip() for line in lines[-lines_count:]])
    except Exception as e:
        return f"Failed to read log file: {e}"

def main():
    parser = argparse.ArgumentParser(description="Kernel Build Telegram Reporter")
    parser.add_argument("--status", required=True, choices=["started", "success", "failure"])
    parser.add_argument("--type", default="KSU", help="Build variant (KSU / NONKSU)")
    parser.add_argument("--token", required=True)
    parser.add_argument("--chat-id", required=True)
    parser.add_argument("--device", default="Genesis")
    parser.add_argument("--kernel-ver", default="-")
    parser.add_argument("--compiler", default="-")
    parser.add_argument("--commit", default="-")
    parser.add_argument("--duration", default="-")
    parser.add_argument("--hash", default="-")
    parser.add_argument("--log-file", default="")
    parser.add_argument("--build-url", default="")
    parser.add_argument("--release-url", default="")
    args = parser.parse_args()

    if args.status == "started":
        msg = (
            f"🚀 *BUILD STARTED*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"├ 🛠 *Variant*  : `{args.type}`\n"
            f"├ 📱 *Device*   : `{args.device}`\n"
            f"└ 🔗 [View Action]({args.build_url})\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━"
        )

    elif args.status == "failure":
        error_text = extract_error_log(args.log_file)
        msg = (
            f"❌ *BUILD FAILED*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"├ 🛠 *Variant*  : `{args.type}`\n"
            f"├ 📱 *Device*   : `{args.device}`\n"
            f"├ 🔗 [View Action]({args.build_url})\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *Error Summary*:\n"
            f"```\n{error_text[:3500]}\n```"
        )

    elif args.status == "success":
        msg = (
            f"✨ *BUILD COMPLETED*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"├ 🛠 *Variant*  : `{args.type}`\n"
            f"├ 📱 *Device*   : `{args.device}`\n"
            f"├ 🐧 *Version*  : `{args.kernel_ver}`\n"
            f"├ ⚡ *Compiler* : `{args.compiler}`\n"
            f"├ ⏱ *Duration* : `{args.duration}`\n"
            f"├ 🔑 *MD5 Hash* : `{args.hash}`\n"
            f"├ 📝 *Commit*   : `{args.commit}`\n"
            f"└ 🔗 [Check Release]({args.release_url})\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━"
        )

    send_telegram_message(args.token, args.chat_id, msg)

if __name__ == "__main__":
    main()
