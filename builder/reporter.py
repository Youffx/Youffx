#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error


def esc(text):
    if not text:
        return ""
    for ch in r"_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, "\\" + ch)
    return text


def tg_call(token, method, **kw):
    import urllib.parse
    data = urllib.parse.urlencode(kw).encode()
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"tg error: {e}", file=sys.stderr)
        return None


COMPILE_RE = re.compile(r'^\s{2,}(?:CC|AS|AR|LD|HOSTCC|HOSTLD|GEN|DTC|CPP|MK|OBJCOPY|STRIP)\b', re.MULTILINE)
DONE_MARKERS = [r'Image\.gz-dtb', r'Kernel:\s+arch/arm64/boot/Image']


def estimate_progress(log_path):
    if not log_path or not os.path.exists(log_path):
        return 0
    try:
        with open(log_path, 'r', errors='ignore') as f:
            content = f.read()
    except Exception:
        return 0
    if any(re.search(p, content) for p in DONE_MARKERS):
        return 100
    count = len(COMPILE_RE.findall(content))
    if count >= 3500:
        return 99
    return int(count * 100 / 3500)


def bar(pct):
    f = pct // 10
    return "▰" * f + "▱" * (10 - f)


def build_msg(mine, pct, other_label):
    if mine == "KSU":
        ksu = f"🔨 `[{bar(pct)}]` {pct}%" if pct < 100 else "✅ Done"
        nonksu = other_label
    else:
        ksu = other_label
        nonksu = f"🔨 `[{bar(pct)}]` {pct}%" if pct < 100 else "✅ Done"
    all_done = "✅ Done" in ksu and "✅ Done" in nonksu
    title = "✅ *ALL BUILDS COMPLETE*" if all_done else "🔨 *KERNEL BUILD IN PROGRESS*"
    return f"""{title}
━━━━━━━━━━━━━━━━━━━━━━━━
├ KSU:    {ksu}
└ NONKSU: {nonksu}
━━━━━━━━━━━━━━━━━━━━━━━━
📊 [VIEW RUN]({build_url})"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--status', required=True,
                   choices=['started', 'progress', 'done', 'success', 'failure', 'aborted', 'monitor', 'finalize'])
    p.add_argument('--token', required=True)
    p.add_argument('--chat-id', required=True)
    p.add_argument('--message-id')
    p.add_argument('--job', default='KSU')
    p.add_argument('--progress', type=int, default=0)
    p.add_argument('--log')
    p.add_argument('--build-url', default='')
    p.add_argument('--msg-id-file')
    p.add_argument('--device', default='')
    p.add_argument('--commit', default='')
    p.add_argument('--compiler', default='')
    p.add_argument('--build-time', default='')
    p.add_argument('--build-time2', default='')
    p.add_argument('--zip-hash', default='')
    p.add_argument('--zip-hash2', default='')
    p.add_argument('--prev-status', default='{}')
    p.add_argument('--message-file')
    args = p.parse_args()

    global build_url
    ws = os.environ.get('GITHUB_WORKSPACE', '.')
    msg_id_file = args.msg_id_file or os.path.join(ws, '.build_msg_id')
    build_url = (args.build_url or
                 f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', '')}"
                 f"/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}")

    try:
        prev = json.loads(args.prev_status)
    except Exception:
        prev = {}

    msg_id = args.message_id
    if not msg_id and os.path.exists(msg_id_file):
        msg_id = open(msg_id_file).read().strip()

    if args.status == 'started':
        text = """🚀 *KERNEL BUILD STARTED*
━━━━━━━━━━━━━━━━━━━━━━━━
├ KSU:    🔨 Building
└ NONKSU: 🔨 Building
━━━━━━━━━━━━━━━━━━━━━━━━
📊 [VIEW RUN]({})""".format(build_url)
        resp = tg_call(args.token, 'sendMessage', chat_id=args.chat_id, text=text, parse_mode='MarkdownV2')
        if resp and resp.get('ok'):
            mid = str(resp['result']['message_id'])
            with open(msg_id_file, 'w') as f:
                f.write(mid)
            print(mid)
        return

    if not msg_id:
        print(f"No message_id available for status={args.status}", file=sys.stderr)
        return

    other_label = "🔨 Building"
    if args.status in ('done', 'success'):
        other_label = "✅ Done"

    if args.status == 'progress':
        pct = args.progress or estimate_progress(args.log)
        text = build_msg(args.job, pct, other_label)
        tg_call(args.token, 'editMessageText', chat_id=args.chat_id, message_id=msg_id, text=text,
                parse_mode='MarkdownV2')

    elif args.status == 'done':
        text = build_msg(args.job, 100, other_label)
        tg_call(args.token, 'editMessageText', chat_id=args.chat_id, message_id=msg_id, text=text,
                parse_mode='MarkdownV2')

    elif args.status == 'success':
        text = """✅ *BUILD COMPLETED SUCCESSFULLY*
━━━━━━━━━━━━━━━━━━━━━━━━
├ KSU:    ✅ Done ({})
├ NONKSU: ✅ Done ({})
├ *Kernel* : `{}`
├ *Compiler* : `{}`
└ *Commit* : `{}`
━━━━━━━━━━━━━━━━━━━━━━━━
📊 [VIEW RUN]({})""".format(esc(args.build_time), esc(args.build_time2),
                            esc(args.device), esc(args.compiler), esc(args.commit), build_url)
        tg_call(args.token, 'editMessageText', chat_id=args.chat_id, message_id=msg_id, text=text,
                parse_mode='MarkdownV2')

    elif args.status == 'failure':
        log_snippet = ""
        if args.log and os.path.exists(args.log):
            try:
                with open(args.log, 'r', errors='ignore') as f:
                    lines = f.readlines()[-50:]
                error_lines = [l.strip() for l in lines
                               if any(k in l.lower() for k in ['error:', 'fatal:', 'fail', '***'])]
                if error_lines:
                    log_snippet = "\n" + "\n".join(f"`{esc(l[:200])}`" for l in error_lines[-3:])
            except Exception:
                pass
        text = """❌ *BUILD FAILED* \\- {}
━━━━━━━━━━━━━━━━━━━━━━━━
├ KSU:    {}
└ NONKSU: {}{}
━━━━━━━━━━━━━━━━━━━━━━━━
📊 [VIEW RUN]({})""".format(esc(args.job),
                            prev.get('ksu', '🔨 Building'),
                            prev.get('nonksu', '🔨 Building'),
                            log_snippet, build_url)
        tg_call(args.token, 'editMessageText', chat_id=args.chat_id, message_id=msg_id, text=text,
                parse_mode='MarkdownV2')

    elif args.status == 'aborted':
        text = """🛑 *BUILD ABORTED*
━━━━━━━━━━━━━━━━━━━━━━━━
├ KSU:    {}
└ NONKSU: {}
━━━━━━━━━━━━━━━━━━━━━━━━
📊 [VIEW RUN]({})""".format(prev.get('ksu', '⏳ Waiting'),
                            prev.get('nonksu', '⏳ Waiting'),
                            build_url)
        tg_call(args.token, 'editMessageText', chat_id=args.chat_id, message_id=msg_id, text=text,
                parse_mode='MarkdownV2')

    elif args.status == 'monitor':
        log_path = args.log or os.path.join(ws, 'build.log')
        last_text = ""
        while True:
            pct = estimate_progress(log_path)
            text = build_msg(args.job, pct, other_label)
            if text != last_text:
                tg_call(args.token, 'editMessageText', chat_id=args.chat_id, message_id=msg_id, text=text,
                        parse_mode='MarkdownV2')
                last_text = text
            if pct >= 100:
                break
            time.sleep(10)

    elif args.status == 'finalize':
        if args.message_file and os.path.exists(args.message_file):
            with open(args.message_file, 'r') as f:
                text = f.read()
        else:
            text = "✅ Build completed successfully"
        tg_call(args.token, 'editMessageText', chat_id=args.chat_id, message_id=msg_id, text=text,
                parse_mode='MarkdownV2')


if __name__ == '__main__':
    main()
