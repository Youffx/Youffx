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
    except Exception:
        return None

def make_progress_bar(percent, length=8):
    filled = int(length * percent // 100)
    bar = '█' * filled + '░' * (length - filled)
    return f"[{bar}] {percent}%"

def sync_state(run_id, key, val=None):
    url = f"https://kvdb.io/genesis_ci_build_{run_id}/{key}"
    if val is not None:
        data = str(val).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=3):
                pass
        except Exception:
            pass
        return str(val)
    else:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=3) as response:
                return response.read().decode('utf-8').strip()
        except Exception:
            return "0"

def monitor_single(token, chat_id, message_id, device, variant, pid, out_dir, run_id, total_expected=3000):
    last_state = ""
    
    while True:
        alive = False
        if pid:
            try:
                os.kill(int(pid), 0)
                alive = True
            except OSError:
                alive = False
        
        count = 0
        if out_dir and os.path.exists(out_dir):
            try:
                res = subprocess.check_output(f"find {out_dir} -name '*.o' 2>/dev/null | wc -l", shell=True)
                count = int(res.decode('utf-8').strip())
            except Exception:
                count = 0

        pct = min(99, int((count / total_expected) * 100)) if pid and alive else (100 if count > 0 else 0)
        
        sync_state(run_id, f"{variant}_pct", pct)

        ksu_pct_str = sync_state(run_id, "ksu_pct")
        nonksu_pct_str = sync_state(run_id, "nonksu_pct")
        saved_start = sync_state(run_id, "start_time")

        try:
            ksu_pct = int(ksu_pct_str)
        except ValueError:
            ksu_pct = 0

        try:
            nonksu_pct = int(nonksu_pct_str)
        except ValueError:
            nonksu_pct = 0

        try:
            start_time = float(saved_start) if float(saved_start) > 0 else time.time()
        except ValueError:
            start_time = time.time()

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
            
        if not alive:
            break
            
        time.sleep(4)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--chat-id", required=True)
    parser.add_argument("--message-id", default="")
    parser.add_argument("--device", default="Genesis")
    parser.add_argument("--variant", default="ksu")
    parser.add_argument("--pid", default="")
    parser.add_argument("--out", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--total-obj", default="3000")
    parser.add_argument("--ksu-status", default="pending")
    parser.add_argument("--nonksu-status", default="pending")
    parser.add_argument("--duration", default="")
    parser.add_argument("--build-url", default="")
    args = parser.parse_args()

    if args.action == "start":
        if args.run_id:
            sync_state(args.run_id, "start_time", int(time.time()))

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
        monitor_single(
            args.token,
            args.chat_id,
            args.message_id,
            args.device,
            args.variant,
            args.pid,
            args.out,
            args.run_id,
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
        
