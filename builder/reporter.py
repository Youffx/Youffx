#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone


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


def fmt_job(pct, label=None):
    if label:
        return label
    if pct is None:
        return "`[▱▱▱▱▱▱▱▱▱▱]` 0%"
    if pct >= 100:
        return "Done"
    return f"`[{bar(pct)}]` {pct}%"


def build_msg(mine, pct, prev, version="", compiler="", commit="", date_str=None,
              ksu_time="", ksu_hash="", nonksu_time="", nonksu_hash=""):
    other = prev or {}
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%a %b %d %H:%M:%S UTC %Y")

    if mine == "KSU":
        ksu_pct = pct
        nonksu_pct = other.get('nonksu')
    else:
        ksu_pct = other.get('ksu')
        nonksu_pct = pct

    ksu_done = ksu_pct is not None and ksu_pct >= 100
    nonksu_done = nonksu_pct is not None and nonksu_pct >= 100
    all_done = ksu_done and nonksu_done

    if all_done:
        title = "ALL BUILDS COMPLETE"
        ksu_line = f"{ksu_time} | sha256: `{ksu_hash}`" if ksu_time else "Done"
        nonksu_line = f"{nonksu_time} | sha256: `{nonksu_hash}`" if nonksu_time else "Done"
    else:
        title = "KERNEL BUILD IN PROGRESS"
        ksu_line = fmt_job(ksu_pct)
        nonksu_line = fmt_job(nonksu_pct)

    return f"""{title}
Kernel Version: {esc(version)}
Compiler: {esc(compiler)}
Date: {esc(date_str)}
Build Variants: KSU, Non-KSU
Latest Commit: {esc(commit)}
Build Statistics:
{chr(8226)} KSU: {ksu_line}
{chr(8226)} Non-KSU: {nonksu_line}

Check Build ({build_url})"""


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
    p.add_argument('--kernel-ver', default='')
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
        text = f"""KERNEL BUILD IN PROGRESS
Build Variants: KSU, Non-KSU
Build Statistics:
{chr(8226)} KSU: `[▱▱▱▱▱▱▱▱▱▱]` 0%
{chr(8226)} Non-KSU: `[▱▱▱▱▱▱▱▱▱▱]` 0%

Check Build ({build_url})"""
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

    if args.status == 'progress':
        pct = args.progress or estimate_progress(args.log)
        text = build_msg(args.job, pct, prev,
                         version=args.kernel_ver, compiler=args.compiler, commit=args.commit)
        tg_call(args.token, 'editMessageText', chat_id=args.chat_id, message_id=msg_id, text=text,
                parse_mode='MarkdownV2')

    elif args.status == 'done':
        text = build_msg(args.job, 100, prev,
                         version=args.kernel_ver, compiler=args.compiler, commit=args.commit,
                         ksu_time=args.build_time if args.job == "KSU" else args.build_time2,
                         ksu_hash=args.zip_hash if args.job == "KSU" else args.zip_hash2,
                         nonksu_time=args.build_time2 if args.job == "KSU" else args.build_time,
                         nonksu_hash=args.zip_hash2 if args.job == "KSU" else args.zip_hash)
        tg_call(args.token, 'editMessageText', chat_id=args.chat_id, message_id=msg_id, text=text,
                parse_mode='MarkdownV2')

    elif args.status == 'success':
        text = f"""ALL BUILDS COMPLETE
Kernel Version: {esc(args.kernel_ver)}
Compiler: {esc(args.compiler)}
Date: {datetime.now(timezone.utc).strftime("%a %b %d %H:%M:%S UTC %Y")}
Build Variants: KSU, Non-KSU
Latest Commit: {esc(args.commit)}
Build Statistics:
{chr(8226)} KSU: {args.build_time} | sha256: `{args.zip_hash}`
{chr(8226)} Non-KSU: {args.build_time2} | sha256: `{args.zip_hash2}`

Check Build ({build_url})"""
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
        ksu_pct = prev.get('ksu')
        nonksu_pct = prev.get('nonksu')
        text = f"""BUILD FAILED - {esc(args.job)}
Kernel Version: {esc(args.kernel_ver)}
Compiler: {esc(args.compiler)}
Latest Commit: {esc(args.commit)}
Build Statistics:
{chr(8226)} KSU: {fmt_job(ksu_pct)}
{chr(8226)} Non-KSU: {fmt_job(nonksu_pct)}{log_snippet}

Check Build ({build_url})"""
        tg_call(args.token, 'editMessageText', chat_id=args.chat_id, message_id=msg_id, text=text,
                parse_mode='MarkdownV2')

    elif args.status == 'aborted':
        text = f"""BUILD ABORTED
Build Statistics:
{chr(8226)} KSU: {fmt_job(prev.get('ksu'))}
{chr(8226)} Non-KSU: {fmt_job(prev.get('nonksu'))}

Check Build ({build_url})"""
        tg_call(args.token, 'editMessageText', chat_id=args.chat_id, message_id=msg_id, text=text,
                parse_mode='MarkdownV2')

    elif args.status == 'monitor':
        log_path = args.log or os.path.join(ws, 'build.log')
        last_text = ""
        while True:
            pct = estimate_progress(log_path)
            text = build_msg(args.job, pct, prev,
                             version=args.kernel_ver, compiler=args.compiler, commit=args.commit)
            if text != last_text:
                tg_call(args.token, 'editMessageText', chat_id=args.chat_id, message_id=msg_id, text=text,
                        parse_mode='MarkdownV2')
                last_text = text
            if pct >= 100:
                break
            time.sleep(10)

    elif args.status == 'finalize':
        text = f"""ALL BUILDS COMPLETE
Kernel Version: {esc(args.kernel_ver)}
Compiler: {esc(args.compiler)}
Date: {datetime.now(timezone.utc).strftime("%a %b %d %H:%M:%S UTC %Y")}
Build Variants: KSU, Non-KSU
Latest Commit: {esc(args.commit)}
Build Statistics:
{chr(8226)} KSU: {args.build_time} | sha256: `{args.zip_hash}`
{chr(8226)} Non-KSU: {args.build_time2} | sha256: `{args.zip_hash2}`

Check Release ({build_url})"""
        tg_call(args.token, 'editMessageText', chat_id=args.chat_id, message_id=msg_id, text=text,
                parse_mode='MarkdownV2')


if __name__ == '__main__':
    main()
