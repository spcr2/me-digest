---
name: me-digest
description: 中东（海湾六国为核心）投资、金融、法律、税务领域每日财经简报的采集、翻译整理与发布前质量校验。外网一手源为主、中文公众号为辅，含突发新闻强制扫描、财经/地缘配比红线、链接与信源质量门（QA Gate）。当用户说"生成今天的中东财经日报/简报"或每日定时触发时使用。本技能只负责采集与编译，不绑定任何文档、网站或 IM 发布渠道。
version: 1.0.0
metadata:
  requires:
    bins: ["python"]
---

# 中东财经简报（me-digest）

每日采集中东地区投资、金融、法律、税务领域新闻，翻译整理为结构化中文简报，并在发布前通过硬性质量门。**采集与编译完成后输出 Markdown，发布到哪个平台由使用者自行决定。**

## 功能概述

- **信息采集**：外网一手源（Reuters/Bloomberg/MEED/律所简报/四大税务简报/各国监管机构）+ 可选的中文监控公众号
- **内容整理**：中文翻译、按国家分栏、业务启示提炼、数据速览表
- **质量校验**：链接可达性 / 文章页识别 / 重复链接 / 旧闻 / 信源黑名单（QA Gate）

## 可选前置：微信公众号本地采集服务

中文公众号采集依赖开源项目 [wechat-article-exporter](https://github.com/wechat-article-exporter/wechat-article-exporter)，需本地后台运行；外网一手源采集无任何依赖。

```bash
# 启动服务（默认 http://127.0.0.1:18901）
cd /path/to/wechat-article-exporter
NUXT_PORT=18901 PORT=18901 npx nuxt dev --port 18901 --host 127.0.0.1
```

- 浏览器打开 `http://127.0.0.1:18901/dashboard/account` 扫码登录一个公众号账号，登录态约 4 天有效。
- 通过环境变量告诉脚本 exporter 位置，脚本会自动从其 `.data/kv/cookie/` 发现密钥：
  - `WECHAT_EXPORTER_DIR`：exporter 项目目录（默认 `~/wechat-article-exporter`）
  - `WECHAT_EXPORTER_API`：服务地址（默认 `http://127.0.0.1:18901`）

## 采集流程

### 阶段零：突发新闻强制扫描（最高优先级，不可跳过）

> **教训**：曾出现利雅得凌晨遭空袭、首都首次拉响防空警报，权威媒体早上 8 点已发稿，简报 10 点发布却漏掉。根因：①关键词偏投资/金融/税务，地缘安全突发权重不足；②没有独立的突发扫描环节；③误把转载页时间当成首发时间，未追溯原稿时间戳。**漏一条重大突发的代价远大于少发十条常规财经新闻。**

**两个时点必须各做一次：**
1. **采集开始时（阶段零）**：先扫突发，再扫常规财经。
2. **临发布前 5-10 分钟（最终 sweep）**：再扫一次"最近 3 小时"突发，堵住"采集完成→正式发布"之间的空窗。命中重大突发就推迟发布、补进去再发。

**固定扫描源（直接打开最新稿页面 / 站内检索，不只靠通用搜索排序）：**
- 中文：央视新闻客户端（ysxw.cctv.cn）、新华网国际频道、中新网（chinanews.com）、参考消息
- 外文：Reuters Middle East、AP、AFP、Bloomberg、Al Arabiya、Al Jazeera、Anadolu（阿纳多卢）、沙特通讯社 SPA、WAM，以及各国民防 / 外交部官方渠道

**突发词矩阵（与国家/首都/设施名交叉检索）：**
- 中文：空袭、袭击、爆炸、导弹、无人机、拦截、防空警报、撤离、断交、制裁、停火、油轮、海峡封锁、使馆提醒
- 英文：airstrike、attack、explosion (heard)、missile、drone、intercepted / interception、air defence alert、evacuation、breaking
- 地名：利雅得 Riyadh、阿布扎比 Abu Dhabi、迪拜 Dubai、多哈 Doha、马斯喀特 Muscat、科威特城 Kuwait City、麦加 Mecca、延布 Yanbu、达曼 Dammam、霍尔木兹海峡 Strait of Hormuz、红海 Red Sea、阿美 Aramco

**判定与处理：**
- 只采权威源已确认事实，严格执行 QA Gate 第 7 条信源黑名单；自媒体推测的武器型号 / 拦截数 / 伤亡数一律不写。
- 命中即列为**头号突发头条（featured）**，并配一条应急类「⚡ 业务启示」（人员安全、差旅、航班保险、资产避险、使馆联络）。
- **以原始稿件时间戳为准**，转载平台时间不等于首发时间。
- 周末 / 节假日照常执行，不得因"休市"降低突发扫描密度。

**内容配比红线（财经为主、地缘为辅，不可颠倒）：**
- 本栏目定位是**投资 / 金融 / 法律 / 税务**简报，不是战报。突发扫描是为了"不漏"，不是"以战争为主线"。
- **突发 / 地缘类最多 1-2 条，且只放头条提示位**；每条必须从**财经 / 市场 / 资金 / 监管 / 交易 / 中资避险影响**视角写（如对油价、航运、供应链、航班、签证、资产配置的影响），**不要写成纯战况**。
- **主体（≥70%）必须是真财经**：央行 / 利率决议、主权基金（PIF/ADQ/QIA/Mumtalakat 等）动向、资本市场（IPO / 并购 / 债券 / 指数 / 外资持仓）、投资大单 / 项目、法律税务监管（VAT / 企业税 / 牌照 / ZATCA / FTA）、跨境支付 / 金融科技。
- **国家覆盖均衡**：沙特 / 阿联酋 / 卡塔尔 / 阿曼 / 科威特 / 巴林，每期每个核心市场尽量至少 1 条真财经，不要让单一国家或单一事件霸版。
- 若当天确属重大地缘升级：突发放头条并配应急启示，但**正文主体仍要补满财经条目**，宁可多搜市场 / 监管 / 项目，也不要整期都是战况。

### 阶段一：外网一手源采集

**信息源分层清单（另见 `config/external_sources.yaml`）：**

1. **国际通讯社**：Reuters Middle East、Bloomberg Middle East、AP、AFP（地缘/突发）
2. **海湾官方媒体**：Saudi Gazette、WAM、The Peninsula Qatar、Oman Daily Observer、Muscat Daily、Kuwait Times / Arab Times
3. **商业专业媒体**：Zawya、AGBI、TradeArabia、MEED、The National、Gulf News
4. **数据 / 研究机构**：Vortexa、S&P / Moody's / Fitch、IEA、Alpen Capital、牛津经济研究院
5. **专业服务机构**：律所（Al Tamimi、Allen & Overy、Clifford Chance、Latham & Watkins、Pinsent Masons）、四大中东税务简报（PwC/Deloitte/EY/KPMG）、各国监管机构官网（沙特 CMA/SAMA/ZATCA、阿联酋 CBUAE/FTA、卡塔尔 QCB/QFCRA）

**采集方式：** 多关键词并行检索，逐条打开原文精读核对。
**时间窗口：** 过去 24-48 小时。

### 阶段二：中文公众号源采集（可选）

**已知限制：**
- 微信已关闭历史文章列表接口，搜狗微信搜索按相关度而非时间排序，对官方号最新文章收录有 1–3 天延迟。
- 稳定可用的是 download API（有文章链接即可下载全文）。
- 公众号通道只能作为中文视角补充；同一事件外网一手源与公众号冲突时，**以一手源为准**。

```bash
# 搜狗通道：关键词搜索（无需登录密钥）
python scripts/fetch_wechat_v2.py --keyword "看中东 9月" -n 10 --output result.json
python scripts/fetch_wechat_v2.py --accounts-file config/wechat_accounts.txt -n 5 --output all.json
python scripts/fetch_wechat_v2.py --keyword "中东 投资" --download --output full.json
python scripts/fetch_wechat_v2.py --keyword "看中东 9月" --filter-days 7 --output recent.json

# 本地 exporter 通道：验证公众号 / 取最新文章（article API 有严格频控，建议间隔 60s）
python scripts/fetch_wechat_local.py verify "看中东 DeepMENA"
python scripts/fetch_latest_articles.py --accounts-file config/wechat_accounts.txt --delay 60 --output latest.json
```

**关键词策略：** `{公众号名} {月份}` 或 `{公众号名} {话题}`；通用话题词：投资、金融、法律、税务、政策、VAT、IPO、并购；另补外交合作类：中沙合作、海合会 中国、中海自贸。

**使馆官网直采（不依赖搜狗）：** 中国驻沙特 `sa.china-embassy.gov.cn/chn/xwdt/`、驻阿联酋 `ae.china-embassy.gov.cn/chn/`、驻卡塔尔 `qa.china-embassy.gov.cn/chn/`，每日直接抓新闻列表页。

推荐监控公众号见 `config/wechat_accounts.txt`，可按需替换为自己的清单。

### 阶段三：内容整理

1. 翻译为中文，关键术语保留英文原文括号标注。
2. **按国家分栏编排**：业务启示（置顶）→ 沙特 → 阿联酋 → 卡塔尔 → 阿曼 → 科威特/巴林 → 海湾综合 → 数据与数字 → 明日关注。
3. 提炼 3 条「⚡ 业务启示」，具体可行动、不空泛。
4. 每条新闻包含：标题、来源、日期、2-4 句中文摘要、原文链接。
5. **每条必须明确标注原始信源**（如"来源：Zawya"），不能笼统写"据外媒"。
6. **【硬约束】原文链接必须指向具体文章页，不能是首页或列表页**；找不到具体文章页就宁可不放这条。

## 发布前质量门（QA Gate，硬门禁）

**触发时机：内容整理完成后、对外发布之前，必须逐项通过。宁少勿假。**

1. **链接逐条可达**：`python scripts/check_links.py <简报.html或.md>`，必须全部 200/3xx；403/404/超时一律换源——你打不开，读者也打不开。
2. **链接必须是具体文章页**：禁止首页、栏目首页、分类/列表页、查询页、域名根。判断标准：URL 末段是文章 slug / 数字 ID / `.html`/`.aspx`。
3. **一链一新闻**：同一条原文链接不得被多条复用。
4. **严防旧闻当新闻**：逐条核对发布时间在过去 24-72 小时；报告 / 数据 / 战略文件被近日转载时追溯原始发布时间，超窗内容只能进数据板块并标注时间。
5. **数据与来源一致**：利率、收益率、金额、指数、增减幅必须能在原文找到；二手数字回溯一手源，无法核实不写精确值。
6. **无法证实即删**：只在单一低质聚合站出现、权威渠道查不到的"新闻"整条删除。
7. **信源黑名单（不得作为原文链接或事实依据）**：
   - 今日头条 / 头条号（toutiao）、抖音、快手、微博、B站、公众号搜狗中转页等自媒体 / UGC 平台，只能当线索并回溯权威源。
   - 低质量聚合页：`*/executive-report`、`/newscategories/...` 列表页、域名根、`?eid=` 查询页。
   - 中文以央视新闻、新华社、中新社、人民日报等权威媒体具体文章页为准；外文以 Reuters、Bloomberg、AP、AFP、Anadolu、SPA、WAM、各国政府 / 央行 / 交易所 / 税务局官网为准。
   - 突发只采用官方或权威通讯社已确认事实；自媒体推测的武器型号、拦截数、伤亡数不写。
8. **成品抽检**：发布前用最终成品（含手机视口）通读一遍，确认头条、卡片、链接、排版正常。

> `scripts/check_links.py` 自动完成第 1-3 项，问题数 >0 时以非零码退出，可接入流水线阻断；第 4-7 项需人工 / 检索核验。

## 输出结构

参考 `templates/digest_template.md`：业务启示 → 头条要闻 → 各国分栏（投资并购 / 金融市场 / 法律监管 / 税务政策）→ 中文源 → 数据速览 → 明日关注。

## 常见问题

**Q：公众号采集返回 freq control（ret=200013）？**
A：article API 有微信端全局限流。把间隔调到 60 秒以上并指数退避（60→120→240s），每日只抓 3-5 个核心号；或改用 `fetch_wechat_v2.py` 的搜狗搜索 + download API 通道。

**Q：登录态过期？**
A：重新打开 exporter 的 `/dashboard/account` 扫码，登录态约 4 天有效，密钥保存在 `.data/kv/`，重启服务不丢失。

**Q：搜官方号返回的全是几个月前的旧文？**
A：按公众号名搜会命中历史热门文，必须用"公众号名 + 话题/月份"关键词，并对重要官方号改走官网直采。
