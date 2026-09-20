#!/usr/bin/env python3
"""
公众号最新文章采集 - 基于 wechat-article-exporter article API
每个公众号间隔较长时间（默认60秒），获取最新若干篇，带频率控制退避。

环境变量（可选，均有默认值）：
  WECHAT_EXPORTER_API  本地服务地址，默认 http://127.0.0.1:18901
  WECHAT_EXPORTER_DIR  wechat-article-exporter 项目目录，默认 ~/wechat-article-exporter
                       脚本据此从 .data/kv/cookie/ 自动发现登录密钥

用法:
  python fetch_latest_articles.py --accounts-file config/wechat_accounts.txt --output latest.json
  python fetch_latest_articles.py --account "看中东 DeepMENA" --output one.json
  python fetch_latest_articles.py --accounts-file config/wechat_accounts.txt --dry-run
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

API_BASE = os.environ.get("WECHAT_EXPORTER_API", "http://127.0.0.1:18901").rstrip("/")
EXPORTER_DIR = os.environ.get(
    "WECHAT_EXPORTER_DIR", str(Path.home() / "wechat-article-exporter")
)
KV_COOKIE_DIR = Path(EXPORTER_DIR) / ".data" / "kv" / "cookie"
DEFAULT_DELAY = 60
ARTICLES_PER_ACCOUNT = 5


def discover_auth_key():
    """从 KV 目录自动发现 API 密钥。"""
    if not KV_COOKIE_DIR.is_dir():
        return None
    candidates = [p for p in KV_COOKIE_DIR.iterdir() if p.is_file() and p.stat().st_size > 0]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0].name


def make_request(path, auth_key=None, query=None, timeout=30):
    """发起 HTTP 请求到本地 API。"""
    url = API_BASE + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    headers = {"User-Agent": "me-digest-latest-fetcher/1.0"}
    if auth_key:
        headers["X-Auth-Key"] = auth_key
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            return json.loads(raw.decode(charset, errors="replace"))
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


def fetch_articles(fakeid, auth_key, size=5, max_retries=3):
    """用 article API 获取公众号最新文章，带重试和频率控制处理。"""
    encoded_fakeid = urllib.parse.quote(fakeid)
    for attempt in range(max_retries):
        try:
            payload = make_request("/api/public/v1/article", auth_key, {
                "fakeid": encoded_fakeid, "begin": 0, "size": size,
            }, timeout=30)
            base_resp = payload.get("base_resp", {})
            ret = base_resp.get("ret")
            if ret == 0:
                return payload.get("articles", [])
            elif ret == 200013:  # freq control
                wait_time = 60 * (attempt + 1)
                print(f"    频率控制，等待 {wait_time} 秒后重试 ({attempt+1}/{max_retries})...")
                time.sleep(wait_time)
            else:
                raise RuntimeError(f"获取失败: ret={ret}, err={base_resp.get('err_msg')}")
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"    请求失败: {e}，等待30秒后重试...")
                time.sleep(30)
            else:
                raise
    return []


def format_article(article, account_name):
    """格式化文章信息。"""
    update_time = article.get("update_time", 0)
    try:
        date_str = datetime.fromtimestamp(update_time).strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError):
        date_str = str(update_time)
    return {
        "title": article.get("title", ""),
        "url": article.get("link", ""),
        "digest": article.get("digest", ""),
        "author": article.get("author", ""),
        "published_at": date_str,
        "source_account": account_name,
        "cover": article.get("cover", ""),
    }


def main():
    parser = argparse.ArgumentParser(description="公众号最新文章采集（article API + 频率控制退避）")
    parser.add_argument("--accounts-file", help="公众号列表文件")
    parser.add_argument("--account", help="单个公众号名称")
    parser.add_argument("--output", required=True, help="输出 JSON 文件路径")
    parser.add_argument("--delay", type=int, default=DEFAULT_DELAY, help=f"每个公众号间隔秒数（默认{DEFAULT_DELAY}）")
    parser.add_argument("--size", type=int, default=ARTICLES_PER_ACCOUNT, help=f"每个公众号获取篇数（默认{ARTICLES_PER_ACCOUNT}）")
    parser.add_argument("--dry-run", action="store_true", help="只验证公众号，不获取文章")
    args = parser.parse_args()

    auth_key = discover_auth_key()
    if not auth_key:
        print(f"错误：未发现 API 密钥（查找目录 {KV_COOKIE_DIR}），请先登录 wechat-article-exporter")
        sys.exit(1)
    print(f"API 密钥: {auth_key[:8]}...")

    accounts = []
    if args.account:
        accounts = [args.account]
    elif args.accounts_file:
        with open(args.accounts_file, encoding="utf-8") as f:
            accounts = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    else:
        print("错误：请指定 --account 或 --accounts-file")
        sys.exit(1)

    print(f"共 {len(accounts)} 个公众号待采集")
    if not args.dry_run:
        print(f"每个间隔 {args.delay} 秒，预计耗时约 {len(accounts) * args.delay / 60:.1f} 分钟")
    print("=" * 60)

    results, failures = [], []
    for i, name in enumerate(accounts, 1):
        print(f"\n[{i}/{len(accounts)}] {name}")
        try:
            acc = verify_account(name, auth_key)
            fakeid = acc.get("fakeid", "")
            print(f"  验证通过: {acc.get('nickname')} (fakeid: {fakeid[:20]}...)")

            if args.dry_run:
                results.append({
                    "account": name, "nickname": acc.get("nickname"),
                    "alias": acc.get("alias"), "fakeid": fakeid,
                    "articles": [], "status": "verified_only",
                })
                continue

            print(f"  获取最新 {args.size} 篇文章...")
            articles = fetch_articles(fakeid, auth_key, size=args.size)
            formatted = [format_article(a, acc.get("nickname")) for a in articles]
            print(f"  获取到 {len(formatted)} 篇文章")
            for a in formatted[:3]:
                print(f"    - [{a['published_at']}] {a['title'][:40]}")

            results.append({
                "account": name, "nickname": acc.get("nickname"),
                "alias": acc.get("alias"), "fakeid": fakeid,
                "articles": formatted, "status": "ok",
            })
        except Exception as e:
            print(f"  失败: {e}")
            failures.append({"account": name, "error": str(e)})
            results.append({"account": name, "articles": [], "status": "failed", "error": str(e)})

        if i < len(accounts) and not args.dry_run:
            print(f"  等待 {args.delay} 秒...")
            time.sleep(args.delay)

    output = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_accounts": len(accounts),
        "success_count": len([r for r in results if r.get("status") == "ok"]),
        "failure_count": len(failures),
        "total_articles": sum(len(r.get("articles", [])) for r in results),
        "results": results,
        "failures": failures,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("采集完成！")
    print(f"  公众号: {output['success_count']}/{output['total_accounts']} 成功")
    print(f"  文章总数: {output['total_articles']}")
    print(f"  结果已保存: {args.output}")
    for fitem in failures:
        print(f"    - {fitem['account']}: {fitem['error']}")


if __name__ == "__main__":
    main()
