# 中东财经简报 · 每日采集与编译流程

> 本文只覆盖**采集 → 筛选 → 编译 → 输出结构**。编译产物为 Markdown，发布到哪个平台（文档 / 网站 / IM）由使用者自行决定。

## 一、采集阶段

### 1. 外网一手源（优先）

**信息源分层清单：**
- 国际通讯社：Reuters Middle East、Bloomberg Middle East、AP、AFP
- 海湾官方媒体：Saudi Gazette、WAM、The Peninsula Qatar、Oman Daily Observer、Kuwait Times
- 商业专业媒体：Zawya、AGBI、TradeArabia、MEED、The National、Gulf News
- 各国外交部 / 央行 / 证监会 / 税务局官网（沙特 CMA/SAMA/ZATCA、阿联酋 CBUAE/FTA、卡塔尔 QCB/QFCRA）
- 律所简报：Allen & Overy、Clifford Chance、Latham & Watkins、Pinsent Masons、Al Tamimi
- 四大中东税务简报：PwC、Deloitte、EY、KPMG

完整可点链接见 `config/external_sources.yaml`。

**采集方式：** 多关键词并行检索，逐条打开原文精读核对。
**时间窗口：** 过去 24-48 小时内发布或持续发酵的新闻。

### 2. 中文公众号源（双通道：本地授权抓取 + 搜狗搜索备选）

#### 2.1 本地授权抓取（首选通道）

**依赖：** 开源项目 [wechat-article-exporter](https://github.com/wechat-article-exporter/wechat-article-exporter)，本地运行（默认 http://127.0.0.1:18901）。

```bash
# 启动服务
cd /path/to/wechat-article-exporter
NUXT_PORT=18901 PORT=18901 npx nuxt dev --port 18901 --host 127.0.0.1

# 告诉脚本 exporter 位置（自动发现 .data/kv/cookie 下的登录密钥）
export WECHAT_EXPORTER_DIR=/path/to/wechat-article-exporter   # Windows 用 $env:
```

- 浏览器打开 `http://127.0.0.1:18901/dashboard/account` 扫码登录一个公众号账号。
- article API 有严格频控（ret=200013, freq control）：间隔建议 ≥60 秒，遇限流指数退避 60→120→240s；每日只抓 3-5 个核心号、每个取最近 3-5 篇。
- account search API 无频率限制，可随时验证公众号。
- 登录态约 4 天有效，过期重新扫码；服务需后台运行。

```bash
python scripts/fetch_wechat_local.py verify "看中东 DeepMENA"
python scripts/fetch_latest_articles.py --accounts-file config/wechat_accounts.txt --delay 60 --output latest.json
```

#### 2.2 搜狗搜索（备选 / 补充通道）

`fetch_wechat_v2.py` 内置搜狗微信搜索解析，无需 node 脚本或登录密钥：

```bash
python scripts/fetch_wechat_v2.py --keyword "中东 投资" -n 15 --download --output result.json
```

若你另外部署了 `wechat-article-search` 的 `search_wechat.js`，可设置 `SOGOU_SEARCH_JS` 环境变量后用 `fetch_wechat_local.py search`；`-r` 会尝试把搜狗中转链接解析为 `mp.weixin.qq.com` 原文链接（实测成功率约 60-75%）。

**推荐监控公众号与关注方向（示例，可自行替换）：**

| 公众号 | 关注方向 |
|---|---|
| 米昱出海 | 沙特资本市场、卡塔尔劳动法、支付监管、阿联酋财税 |
| 看中东 DeepMENA | 中东北非中亚商业资讯、科技 / 投融资 / 本地产业 |
| 中国驻沙特大使馆 | 中沙合作、政策动态（官方） |
| 中信建投国际 | 中东专题、海湾金融机构动态 |
| quide的香港规划 | 中东资本东进、海湾金融机构落地香港 |
| FET国际经济与产业科技智库 | 中东主权基金全球投资 |
| 中卡路宜工业园 | 卡塔尔投资机遇、中卡合作 |

**每日关键词组合（每次搜 1-2 个，避免触发反爬）：**
"中东 投资 金融"、"沙特 资本市场 监管"、"阿联酋税务"、"卡塔尔投资"、"中东 主权基金"、"海湾 金融科技"、"中沙合作"、"海合会 中国"、"中海自贸"、"中国 海湾 投资"。

**⚠️ 公众号搜索局限性与应对：**
- 搜狗微信对官方号最新文章收录有 1-3 天延迟；按公众号名搜索常返回历史热门文而非最新文章，**必须用"公众号名 + 话题/月份"关键词**。
- 使馆官网同步可能晚于公众号。对重要官方号，以**官网直采 + 通讯社检索**为主、公众号搜索为辅：
  - 驻沙特：https://sa.china-embassy.gov.cn/chn/xwdt/
  - 驻阿联酋：https://ae.china-embassy.gov.cn/chn/
  - 驻卡塔尔：https://qa.china-embassy.gov.cn/chn/
- 多词组合（如"卡塔尔 法律 税务"）可能返回空，应拆成单词或双词。
- 公众号与外网源报道同一事件时，**优先以外网一手源为准**，公众号作为中文视角补充。

### 3. 内容筛选标准

- 领域：仅投资、金融、法律、税务（泛政治 / 军事 / 社会新闻除非直接影响投资金融环境，否则不收）。
- 地域：海湾六国为核心（沙特、阿联酋、卡塔尔、科威特、巴林、阿曼），可扩展至伊朗、伊拉克、以色列、埃及、土耳其。
- 每条必须包含：标题、来源、日期、2-4 句中文摘要、原文链接（具体文章页）。
- 关键术语保留英文原文括号标注。
- **配比红线**：财经主体 ≥70%；突发 / 地缘最多 1-2 条且只放头条提示位，从市场 / 资金 / 监管 / 交易影响视角写。

## 二、编译阶段

1. 外网源内容翻译为中文，关键术语保留英文。
2. 公众号来源标注公众号名（如「来源：米昱出海」），附原文链接（搜狗中转链接需标注）。
3. 按国家分栏、按重要性排序，头条要闻 3-5 条。
4. 提炼「⚡ 业务启示 / Actionable Insights」2-3 条，要求具体、可行动。
5. 整理数据速览表格、明日关注时间线。
6. 编译完成后运行 `python scripts/check_links.py <成品>` 通过质量门，再对外发布。

## 三、输出结构

```
⚡ 业务启示 / Actionable Insights（2-3 条，置顶）
头条要闻（3-5 条，含最多 1-2 条突发提示位）
沙特阿拉伯 🇸🇦
阿联酋 🇦🇪
卡塔尔 🇶🇦 / 阿曼 🇴🇲 / 科威特 🇰🇼 / 巴林 🇧🇭
海湾综合（跨境 / 主权基金 / 评级）
中文源（公众号 / 国内媒体，3-5 条）
数据速览
明日关注
```

模板见 `templates/digest_template.md`。
