# -*- coding: utf-8 -*-
"""简报发布前链接质量门（QA Gate）标准工具。

用法：
    python check_links.py <简报.html 或 简报.md>

支持：
    - .html：优先提取卡片中"阅读原文"链接；若页面无该标记，则回退为提取全部外链
    - .md  ：提取 Markdown 链接 [文本](url) 与裸链接（自动忽略图片链接）

检查项：
    1. 每条原文链接 HTTP 状态（200/3xx 视为可达；403/404/超时为问题）
    2. 是否首页 / 分类 / 列表页（shallow）
    3. 是否一条链接被多条新闻复用（一链一新闻）
    4. 汇总问题清单，问题数>0 时以非零码退出（供流水线阻断）

判断"具体文章页"的规则（避免单层 SEO slug 误报）：
    - 路径末段含 4 位以上数字、.html/.htm/.aspx，或
    - 末段 slug 长度 >= 25 且含 >= 3 个连字符（长 SEO slug 文章页）
    其余单层短路径（域名根、/news、/business、/newscategories/region/）判为列表页。
"""
import re
import ssl
import sys
import os
import urllib.request
from urllib.parse import urlparse

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}

SECTION_WORDS = {
    "news", "business", "businesses", "market", "markets", "category", "categories",
    "newscategory", "newscategories", "region", "topic", "topics", "tag", "tags",
    "en", "chn", "xwdt", "media", "press", "section", "sections",
}
LIST_SYSTEMS = re.compile(r'/(newscategor\w*|categor(?:y|ies)|topics?|tags?)/', re.I)
ARTICLE_SUFFIX = re.compile(r'\.(html?|aspx|php|jsp)$', re.I)


def extract_urls_html(page):
    urls = re.findall(r'href="(https?://[^"]+)"[^>]*>\s*阅读原文', page)
    if not urls:  # 回退：页面没有"阅读原文"标记时，检查全部外链
        urls = re.findall(r'href="(https?://[^"]+)"', page)
    return urls


def extract_urls_md(page):
    # 去掉图片，避免把图片链接算进来
    page = re.sub(r'!\[[^\]]*\]\(\s*https?://[^)]+\)', '', page)
    urls = re.findall(r'\]\(\s*(https?://[^)\s]+)\s*\)', page)
    # 裸链接（未被 markdown 链接包裹）
    for u in re.findall(r'(?<![(\w])https?://[^\s)>\]]+', page):
        urls.append(u.rstrip('.,;'))
    # 去重保序
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def is_article_page(u):
    """返回 (是否文章页, 原因)。先认文章强信号，栏目词仅在末段才判列表。"""
    p = urlparse(u)
    path = p.path.rstrip('/')
    segs = [s for s in path.split('/') if s]
    if not segs:
        return False, "首页(根路径)"
    last = segs[-1].lower()
    if LIST_SYSTEMS.search(path + '/'):
        return False, "分类/列表页"
    if ARTICLE_SUFFIX.search(last):
        return True, ""
    if re.search(r'\d{4,}', last):
        return True, ""
    if len(last) >= 25 and last.count('-') >= 3:
        return True, ""
    if len(segs) >= 2 and re.fullmatch(r'\d{3,}', segs[-2]):
        return True, ""
    if last in SECTION_WORDS:
        return False, "栏目首页/列表页"
    if len(segs) <= 1:
        return False, "单层短路径(疑似首页/栏目页)"
    return True, ""


def main():
    if len(sys.argv) < 2:
        print("用法: python check_links.py <简报.html 或 简报.md>")
        sys.exit(2)
    path = sys.argv[1]
    if not os.path.isfile(path):
        print(f"找不到文件: {path}")
        sys.exit(2)

    page = open(path, encoding="utf-8").read()
    if path.lower().endswith((".md", ".markdown")):
        urls = extract_urls_md(page)
    else:
        urls = extract_urls_html(page)
    print(f"检查文件: {os.path.basename(path)}  共 {len(urls)} 条链接\n")

    seen, problems = {}, []
    for i, u in enumerate(urls, 1):
        st = "-"
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers=HEADERS), timeout=15, context=CTX)
            st = r.status
        except Exception as e:
            st = getattr(e, "code", None) or type(e).__name__
        article, why = is_article_page(u)
        dup = ""
        if u in seen:
            dup = f" [与第{seen[u]}条重复!]"
            why = why or "链接被多条新闻复用"
        else:
            seen[u] = i
        reachable = st == 200 or (isinstance(st, int) and 300 <= st < 400)
        ok = reachable and article and not dup
        if not ok:
            problems.append((i, st, (why or dup.strip(" []!")), u))
        print(f"[{i:2d}] {'OK ' if ok else 'BAD'} {st} {(why or '') + dup} {u[:90]}")

    print("\n" + "=" * 60)
    if problems:
        print(f"问题 {len(problems)} 条，发布前必须修复：")
        for i, st, why, u in problems:
            print(f"  第{i}条 [{st}] {why}: {u}")
        sys.exit(1)
    print(f"全部 {len(urls)} 条链接通过：可达、均为具体文章页、无复用。")
    sys.exit(0)


if __name__ == "__main__":
    main()
