#!/usr/bin/env python3
"""
公众号文章采集脚本 v2 - 直接调用搜狗搜索 + download API 下载全文
绕过 search_wechat.js 的 cookie/UA 问题。

用法:
  python fetch_wechat_v2.py --keyword "中东 投资" --output result.json
  python fetch_wechat_v2.py --accounts-file config/wechat_accounts.txt --output all.json
  python fetch_wechat_v2.py --keyword "看中东 沙特" --download --output with_fulltext.json
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

SOGOU_URL = "https://weixin.sogou.com/weixin"
DOWNLOAD_API = os.environ.get(
    "WECHAT_EXPORTER_API", "http://127.0.0.1:18901"
).rstrip("/") + "/api/public/v1/download"
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
]


def http_get(url, timeout=15):
    """发起 HTTP GET 请求，带随机 UA。"""
    import random
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://weixin.sogou.com/",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"连接失败: {e.reason}")


def parse_sogou_results(html):
    """解析搜狗搜索结果页，提取文章列表。"""
    articles = []
    items = re.findall(r'<li[^>]*id="sogou_vr_.*?"[^>]*>(.*?)</li>', html, re.DOTALL)
    if not items:
        items = re.findall(r'<div class="txt-box">(.*?)</div>\s*</div>', html, re.DOTALL)

    for item in items:
        try:
            title_match = re.search(r'<h3[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', item, re.DOTALL)
            if not title_match:
                continue
            url = title_match.group(1)
            if url.startswith("/"):
                url = "https://weixin.sogou.com" + url
            title = re.sub(r'<[^>]+>', '', title_match.group(2)).strip()
            title = title.replace('&nbsp;', ' ').replace('&amp;', '&')

            summary_match = re.search(r'<p class="txt-info[^"]*"[^>]*>(.*?)</p>', item, re.DOTALL)
            summary = re.sub(r'<[^>]+>', '', summary_match.group(1)).strip() if summary_match else ""
            summary = summary.replace('&nbsp;', ' ').replace('&amp;', '&')

            source_match = re.search(r'<a[^>]*class="account"[^>]*>(.*?)</a>', item, re.DOTALL)
            if not source_match:
                source_match = re.search(r'<span class="all-time-y2"[^>]*>(.*?)</span>', item, re.DOTALL)
            source = re.sub(r'<[^>]+>', '', source_match.group(1)).strip() if source_match else ""

            time_match = re.search(r'timeConvert\s*\(\s*[\'\"]?(\d{10})[\'\"]?\s*\)', item)
            if not time_match:
                time_match = re.search(r'(\d{10})', item)
            published_at = ""
            if time_match:
                try:
                    ts = int(time_match.group(1))
                    published_at = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
                except (ValueError, OSError):
                    pass

            articles.append({
                "title": title,
                "url": url,
                "summary": summary,
                "source": source,
                "published_at": published_at,
            })
        except Exception:
            continue

    return articles


def sogou_search(keyword, num=10, sort_by_time=False):
    """搜狗微信搜索。"""
    articles = []
    page = 1
    pages_needed = (num + 9) // 10

    while len(articles) < num and page <= pages_needed:
        try:
            params = {
                "query": keyword,
                "type": "2",
                "page": str(page),
                "ie": "utf8",
            }
            if sort_by_time:
                params["sort"] = "1"
            url = SOGOU_URL + "?" + urllib.parse.urlencode(params)
            html = http_get(url)
            parsed = parse_sogou_results(html)
            if not parsed:
                break
            articles.extend(parsed)
            page += 1
            if page <= pages_needed:
                time.sleep(1 + len(articles) * 0.1)
        except Exception as e:
            print(f"  第{page}页失败: {e}", file=sys.stderr)
            break

    return articles[:num]


def download_fulltext(url, fmt="text"):
    """用 wechat-article-exporter download API 下载全文。"""
    try:
        params = {"url": url, "format": fmt}
        full_url = DOWNLOAD_API + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(full_url, headers={"User-Agent": "me-digest/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"[下载失败: {e}]"


def filter_by_date(articles, days=7):
    """按发布时间筛选最近 N 天的文章。"""
    cutoff = datetime.now() - timedelta(days=days)
    filtered = []
    for a in articles:
        if not a.get("published_at"):
            filtered.append(a)
            continue
        try:
            pub_date = datetime.strptime(a["published_at"], "%Y-%m-%d %H:%M")
            if pub_date >= cutoff:
                filtered.append(a)
        except ValueError:
            filtered.append(a)
    return filtered


def main():
    parser = argparse.ArgumentParser(description="公众号文章采集 v2（搜狗搜索 + download API）")
    parser.add_argument("--keyword", help="搜索关键词")
    parser.add_argument("--accounts-file", help="公众号列表文件（每个公众号名+通用关键词搜索）")
    parser.add_argument("--output", required=True, help="输出 JSON 文件路径")
    parser.add_argument("-n", "--num", type=int, default=10, help="每个关键词返回数量（默认10）")
    parser.add_argument("--sort-by-time", action="store_true", help="按时间排序（可能触发反爬）")
    parser.add_argument("--download", action="store_true", help="下载全文（需要 wechat-article-exporter 运行）")
    parser.add_argument("--filter-days", type=int, default=0, help="只保留最近N天的文章（0=不过滤）")
    args = parser.parse_args()

    all_articles = []
    keywords = []

    if args.keyword:
        keywords.append(args.keyword)
    elif args.accounts_file:
        with open(args.accounts_file, encoding="utf-8") as f:
            accounts = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        common_keywords = ["投资", "金融", "法律", "税务", "政策"]
        for acc in accounts:
            for kw in common_keywords:
                keywords.append(f"{acc} {kw}")
    else:
        print("错误：请指定 --keyword 或 --accounts-file")
        sys.exit(1)

    print(f"共 {len(keywords)} 个关键词待搜索")
    print("=" * 60)

    for i, kw in enumerate(keywords, 1):
        print(f"\n[{i}/{len(keywords)}] 搜索: {kw}")
        try:
            articles = sogou_search(kw, num=args.num, sort_by_time=args.sort_by_time)
            print(f"  获取到 {len(articles)} 篇")
            for a in articles[:3]:
                print(f"    - [{a.get('published_at', '?')}] {a['title'][:40]}")
            all_articles.extend(articles)
        except Exception as e:
            print(f"  失败: {e}")
        if i < len(keywords):
            time.sleep(2)

    seen = set()
    deduped = []
    for a in all_articles:
        key = a.get("title", "") + a.get("url", "")
        if key not in seen:
            seen.add(key)
            deduped.append(a)

    if args.filter_days > 0:
        before = len(deduped)
        deduped = filter_by_date(deduped, args.filter_days)
        print(f"\n时间筛选: {before} -> {len(deduped)}（最近{args.filter_days}天）")

    if args.download:
        print(f"\n开始下载 {len(deduped)} 篇全文...")
        for i, a in enumerate(deduped, 1):
            print(f"  [{i}/{len(deduped)}] {a['title'][:30]}...")
            a["fulltext"] = download_fulltext(a["url"])
            time.sleep(0.5)

    output = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_keywords": len(keywords),
        "total_articles": len(deduped),
        "articles": deduped,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"采集完成！共 {len(deduped)} 篇文章")
    print(f"结果已保存: {args.output}")


if __name__ == "__main__":
    main()
