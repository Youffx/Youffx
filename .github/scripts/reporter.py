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

def main():
    parser = argparse.ArgumentParser(description="Kernel Build Telegram Reporter")
    parser.add_argument("--status", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--chat-id", required=True)
    parser.add_argument("--device", default="Genesis")
    parser.add_argument("--kernel-ver", default="-")
    parser.add_argument("--compiler", default="-")
    parser.add_argument("--commit", default="-")
    parser.add_argument("--duration", default="-")
    parser.add_argument("--ksu-status", default="-")
    parser.add_argument("--nonksu-status", default="-")
    parser.add_argument("--build-url", default="")
    parser.add_argument("--release-url", default="")
    args = parser.parse_args()

    if args.status == "started":
        msg = (
            f"🚀 *BUILD STARTED*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"├ 📱 *Device*   : `{args.device}`\n"
            f"├ 🛠 *Variants* : `KSU & Non-KSU`\n"
            f"└ 🔗 [View Action]({args.build_url})\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    elif args.status == "finished":
        both_success = (args.ksu_status == "success" and args.nonksu_status == "success")
        status_icon = "✨" if both_success else "⚠️"
        msg = (
            f"{status_icon} *BUILD SUMMARY*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"├ 📱 *Device*      : `{args.device}`\n"
            f"├ 🐧 *Version*     : `{args.kernel_ver}`\n"
            f"├ ⚡ *Compiler*    : `{args.compiler}`\n"
            f"├ ⏱ *Duration*    : `{args.duration}`\n"
            f"├ 🛡 *KSU Build*   : `{args.ksu_status}`\n"
            f"├ 📦 *Non-KSU*     : `{args.nonksu_status}`\n"
            f"├ 📝 *Commit*      : `{args.commit}`\n"
            f"└ 🔗 [Check Action]({args.build_url})\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        msg = f"Status: {args.status}"

    send_telegram_message(args.token, args.chat_id, msg)

if __name__ == "__main__":
    main()
    
