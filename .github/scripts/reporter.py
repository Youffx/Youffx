import argparse
import os
import sys
import json
import time
import urllib.request
import urllib.parse
import subprocess

def send_telegram(token, chat_id, text):
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
            res = json.loads(response.read().decode('utf-8'))
            if res.get("ok"):
                return res["result"]["message_id"]
    except Exception as e:
        print(f"Error sending Telegram message: {e}", file=sys.stderr)
    return None

def edit_telegram(token, chat_id, message_id, text):
    url = f"https://api.telegram.org/bot{token}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
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
        print(f"Error editing Telegram message: {e}", file=sys.stderr)
        return None

def make_progress_bar(percent, length=8):
    filled = int(length * percent // 100)
    bar = '█' * filled + '░' * (length - filled)
    return f"[{bar}] {percent}%"

def monitor_progress(token, chat_id, message_id, device, ksu_pid, nonksu_pid, ksu_out, nonksu_out, total_expected=3000):
    start_time = time.time()
    last_state = ""
    
    while True:
        ksu_alive = False
        nonksu_alive = False
        
        if ksu_pid:
            try:
                os.kill(int(ksu_pid), 0)
                ksu_alive = True
            except OSError:
                ksu_alive = False

        if nonksu_pid:
            try:
                os.kill(int(nonksu_pid), 0)
                nonksu_alive = True
            except OSError:
                nonksu_alive = False
        
        if not ksu_alive and not nonksu_alive:
            break
            
        ksu_count = 0
        if ksu_out and os.path.exists(ksu_out):
            try:
                res = subprocess.check_output(f"find {ksu_out} -name '*.o' | wc -l", shell=True)
                ksu_count = int(res.decode('utf-8').strip())
            except Exception:
                ksu_count = 0

        nonksu_count = 0
        if nonksu_out and os.path.exists(nonksu_out):
            try:
                res = subprocess.check_output(f"find {nonksu_out} -name '*.o' | wc -l", shell=True)
                nonksu_count = int(res.decode('utf-8').strip())
            except Exception:
                nonksu_count = 0

        ksu_pct = min(99, int((ksu_count / total_expected) * 100)) if ksu_pid and ksu_alive else (100 if ksu_count > 0 else 0)
        nonksu_pct = min(99, int((nonksu_count / total_expected) * 100)) if nonksu_pid and nonksu_alive else (100 if nonksu_count > 0 else 0)

        elapsed = int(time.time() - start_time)
        mins = elapsed // 60
        secs = elapsed % 60
        time_str = f"{mins}m {secs}s"
        
        ksu_bar = make_progress_bar(ksu_pct)
        nonksu_bar = make_progress_bar(nonksu_pct)

        current_state = f"{ksu_pct}-{nonksu_pct}-{elapsed // 5}"
        if current_state != last_state:
            msg = (
                f"⚙️ *BUILD IN PROGRESS*\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"├ 📱 *Build*   : `{device}`\n"
                f"├ ⏱ *Elapsed*  : `{time_str}`\n"
                f"├ 🛡 *KSU*      : `{ksu_bar}`\n"
                f"└ 📦 *Non-KSU*  : `{nonksu_bar}`\n"
                f"━━━━━━━━━━━━━━━━━━━"
            )
            edit_telegram(token, chat_id, message_id, msg)
            last_state = current_state
            
        time.sleep(4)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--chat-id", required=True)
    parser.add_argument("--message-id", default="")
    parser.add_argument("--device", default="Genesis")
    parser.add_argument("--ksu-pid", default="")
    parser.add_argument("--nonksu-pid", default="")
    parser.add_argument("--ksu-out", default="")
    parser.add_argument("--nonksu-out", default="")
    parser.add_argument("--total-obj", default="3000")
    parser.add_argument("--ksu-status", default="pending")
    parser.add_argument("--nonksu-status", default="pending")
    parser.add_argument("--duration", default="")
    parser.add_argument("--build-url", default="")
    args = parser.parse_args()

    if args.action == "start":
        msg = (
            f"🚀 *BUILD STARTED*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"├ 📱 *Build*   : `{args.device}`\n"
            f"├ 🛡 *KSU*      : `[░░░░░░░░] 0%`\n"
            f"├ 📦 *Non-KSU*  : `[░░░░░░░░] 0%`\n"
            f"└ 🔗 [View Action]({args.build_url})\n"
            f"━━━━━━━━━━━━━━━━━━━"
        )
        msg_id = send_telegram(args.token, args.chat_id, msg)
        if msg_id:
            print(msg_id)

    elif args.action == "monitor":
        monitor_progress(
            args.token,
            args.chat_id,
            args.message_id,
            args.device,
            args.ksu_pid,
            args.nonksu_pid,
            args.ksu_out,
            args.nonksu_out,
            int(args.total_obj)
        )

    elif args.action == "finish":
        ksu_icon = "✅" if args.ksu_status == "success" else ("❌" if args.ksu_status == "failure" else "⚪")
        nonksu_icon = "✅" if args.nonksu_status == "success" else ("❌" if args.nonksu_status == "failure" else "⚪")
        
        main_icon = "✨" if (args.ksu_status == "success" and args.nonksu_status == "success") else "⚠️"
        
        msg = (
            f"{main_icon} *BUILD COMPLETED*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"├ 📱 *Build*   : `{args.device}`\n"
            f"├ ⏱ *Duration* : `{args.duration}`\n"
            f"├ 🛡 *KSU*      : {ksu_icon} `{args.ksu_status}`\n"
            f"├ 📦 *Non-KSU*  : {nonksu_icon} `{args.nonksu_status}`\n"
            f"└ 🔗 [View Action]({args.build_url})\n"
            f"━━━━━━━━━━━━━━━━━━━"
        )
        edit_telegram(args.token, args.chat_id, args.message_id, msg)

if __name__ == "__main__":
    main()
                
