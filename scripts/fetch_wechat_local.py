#!/usr/bin/env python3
"""
微信公众号本地抓取脚本 - 混合策略
通过 wechat-article-exporter 本地服务 + 搜狗搜索的混合方式抓取公众号文章。

策略：
- account search：本地 API（无频率限制）→ 验证公众号、获取 fakeid
- 文章搜索：搜狗搜索（可选的 search_wechat.js）→ 获取标题、摘要、链接
- 全文下载：本地 download API（无频率限制、无需密钥）→ 获取文章全文

环境变量（可选，均有默认值）：
  WECHAT_EXPORTER_API  本地服务地址，默认 http://127.0.0.1:18901
  WECHAT_EXPORTER_DIR  wechat-article-exporter 项目目录，默认 ~/wechat-article-exporter
                       脚本据此从 .data/kv/cookie/ 自动发现登录密钥
  SOGOU_SEARCH_JS      可选，wechat-article-search 的 search_wechat.js 绝对路径；
                       不设置时 search 子命令不可用，verify/download 不受影响

用法:
  python fetch_wechat_local.py search "中东 投资" -n 10
  python fetch_wechat_local.py verify "看中东 DeepMENA"
  python fetch_wechat_local.py download "https://mp.weixin.qq.com/s/xxx"
  python fetch_wechat_local.py verify-all --accounts-file wechat_accounts.txt
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = os.environ.get("WECHAT_EXPORTER_API", "http://127.0.0.1:18901").rstrip("/")
EXPORTER_DIR = os.environ.get(
    "WECHAT_EXPORTER_DIR", str(Path.home() / "wechat-article-exporter")
)
KV_COOKIE_DIR = Path(EXPORTER_DIR) / ".data" / "kv" / "cookie"
SOGOU_SCRIPT = os.environ.get("SOGOU_SEARCH_JS", "")
DEFAULT_DELAY = 2


def discover_auth_key():
    """从 KV 目录自动发现 API 密钥（取最新的非空文件）。"""
    if not KV_COOKIE_DIR.is_dir():
        return None
    candidates = [p for p in KV_COOKIE_DIR.iterdir() if p.is_file() and p.stat().st_size > 0]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0].name


def make_request(path, auth_key=None, query=None, timeout=30, expect_json=True):
    """发起 HTTP 请求到本地 API。"""
    url = API_BASE + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    headers = {"User-Agent": "me-digest-wechat-fetcher/1.0"}
    if auth_key:
        headers["X-Auth-Key"] = auth_key
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            text = raw.decode(charset, errors="replace")
            if expect_json:
                return json.loads(text)
            return text
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"HTTP {e.code}: {detail}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"连接失败: {e.reason}（本地 exporter 服务是否已启动？{API_BASE}）")


def verify_account(name, auth_key):
    """用本地 API 验证公众号，返回精确匹配结果。"""
    payload = make_request("/api/public/v1/account", auth_key, {
        "keyword": name, "begin": 0, "size": 5,
    })
    base_resp = payload.get("base_resp", {})
    if base_resp.get("ret") != 0:
        raise RuntimeError(f"搜索失败: {base_resp.get('err_msg')}")
    accounts = payload.get("list", [])
    normalized = name.casefold().strip()
    for a in accounts:
        if str(a.get("nickname", "")).casefold().strip() == normalized:
            return a
    for a in accounts:
        if str(a.get("alias", "")).casefold().strip() == normalized:
            return a
    if accounts:
        return accounts[0]
    raise RuntimeError(f"未找到公众号: {name}")


def sogou_search(keyword, num=10, resolve=True):
    """用搜狗搜索公众号文章（需要 SOGOU_SEARCH_JS 指向 search_wechat.js）。"""
    if not SOGOU_SCRIPT or not Path(SOGOU_SCRIPT).is_file():
        raise RuntimeError(
            "未配置搜狗搜索脚本：请设置环境变量 SOGOU_SEARCH_JS 为 search_wechat.js 的绝对路径，"
            "或改用 fetch_wechat_v2.py（内置搜狗解析，无需 node 脚本）。"
        )
    cmd = ["node", SOGOU_SCRIPT, keyword, "-n", str(num)]
    if resolve:
        cmd.append("-r")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                            cwd=str(Path(SOGOU_SCRIPT).parent.parent), timeout=60)
    try:
        data = json.loads(result.stdout)
        return data.get("articles", [])
    except json.JSONDecodeError:
        print(f"搜狗搜索输出解析失败: {result.stdout[:200]}", file=sys.stderr)
        return []


def download_article(url, fmt="text"):
    """用本地 download API 下载文章全文（不需要密钥）。"""
    return make_request("/api/public/v1/download", query={"url": url, "format": fmt}, expect_json=False)


def main():
    parser = argparse.ArgumentParser(description="微信公众号本地抓取（混合策略）")
    sub = parser.add_subparsers(dest="command")

    p_verify = sub.add_parser("verify", help="验证公众号")
    p_verify.add_argument("name", help="公众号名称")

    p_verify_all = sub.add_parser("verify-all", help="批量验证公众号列表")
    p_verify_all.add_argument("--accounts-file", required=True, help="公众号列表文件")

    p_search = sub.add_parser("search", help="搜狗搜索文章（需 SOGOU_SEARCH_JS）")
    p_search.add_argument("keyword", help="搜索关键词")
    p_search.add_argument("-n", "--num", type=int, default=10, help="返回数量")
    p_search.add_argument("--no-resolve", action="store_true", help="不解析真实URL")

    p_download = sub.add_parser("download", help="下载文章全文")
    p_download.add_argument("url", help="公众号文章URL")
    p_download.add_argument("--format", choices=["text", "markdown", "html", "json"], default="text")
    p_download.add_argument("--output", help="输出文件路径")

    sub.add_parser("discover-key", help="自动发现 API 密钥")

    args = parser.parse_args()

    if args.command == "discover-key":
        key = discover_auth_key()
        print(f"API 密钥: {key}" if key else f"未发现密钥（查找目录: {KV_COOKIE_DIR}）")
        return

    if args.command == "verify":
        key = discover_auth_key()
        if not key:
            print("错误：未发现 API 密钥，请先登录 wechat-article-exporter")
            sys.exit(1)
        acc = verify_account(args.name, key)
        print(json.dumps({
            "nickname": acc.get("nickname"),
            "alias": acc.get("alias"),
            "fakeid": acc.get("fakeid"),
        }, ensure_ascii=False, indent=2))
        return

    if args.command == "verify-all":
        key = discover_auth_key()
        if not key:
            print("错误：未发现 API 密钥")
            sys.exit(1)
        with open(args.accounts_file, encoding="utf-8") as f:
            names = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        results = {}
        for name in names:
            try:
                acc = verify_account(name, key)
                results[name] = {
                    "nickname": acc.get("nickname"),
                    "alias": acc.get("alias"),
                    "fakeid": acc.get("fakeid"),
                    "status": "ok",
                }
                print(f"  OK  {name} -> {acc.get('nickname')}")
            except Exception as e:
                results[name] = {"status": "failed", "error": str(e)}
                print(f"  FAIL {name} -> {e}")
            time.sleep(DEFAULT_DELAY)
        out = args.accounts_file.replace(".txt", "_verified.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n已保存到 {out}")
        return

    if args.command == "search":
        articles = sogou_search(args.keyword, args.num, resolve=not args.no_resolve)
        print(json.dumps(articles, ensure_ascii=False, indent=2))
        return

    if args.command == "download":
        content = download_article(args.url, args.format)
        if args.output:
            Path(args.output).write_text(content, encoding="utf-8")
            print(f"已保存到 {args.output} ({len(content)} 字符)")
        else:
            print(content)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
