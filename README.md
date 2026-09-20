# Middle East Finance Digest (me-digest)

一套面向**中东（海湾六国为核心）投资 / 金融 / 法律 / 税务**领域的每日财经简报采集与编译方法论 + 可复用脚本。外网一手源为主、中文公众号为辅，产出结构化的中文每日简报，并在发布前用一道硬性「质量门（QA Gate）」卡住死链、列表页链接、旧闻、低质信源。

> 本仓库**只包含信息采集、翻译整理与质量校验**，不含任何特定平台（文档 / 网站 / IM）的发布与推送代码，也不含任何凭证或个人配置。编译好的 Markdown 你可以接到任意自己的发布渠道。

## 为什么需要它

- 中东财经信息分散在通讯社、各国官方媒体、监管机构、律所 / 四大简报、中文公众号之间，人工每天扫一遍成本高。
- 通用搜索引擎按相关度而非时间排序，**重大突发容易漏**；纯战报又容易刷屏、淹没真正的财经内容。
- 聚合站 / 自媒体死链、列表页链接、旧闻翻炒、未经证实的数字非常多，直接转发风险高。

me-digest 用一套固定流程解决这三件事：**不漏突发、不被战报带偏、不放不可靠的链接和数字**。

## 核心特性

- **分层信源清单**：国际通讯社 → 海湾官方媒体 → 商业专业媒体 → 数据 / 研究机构 → 律所与四大税务简报，外加中文官方源与监控公众号清单（见 `config/`）。
- **阶段零：突发新闻强制扫描**：开工先扫突发、临发布前再扫一次最近 3 小时，附突发词矩阵与固定权威源。
- **内容配比红线**：财经主体 ≥70%，突发 / 地缘最多 1–2 条且只放提示位、必须从市场 / 资金 / 监管 / 交易影响视角写，避免整期变成战报。
- **发布前质量门 QA Gate**：链接逐条可达、必须是具体文章页、一链一新闻、严防旧闻、数字可溯源、信源黑名单（头条号等 UGC 不作为信源）。
- **可选的微信公众号采集脚本**：基于本地 [wechat-article-exporter](https://github.com/wechat-article-exporter/wechat-article-exporter) 服务 + 搜狗微信搜索的混合采集，自带频率控制与全文下载。

## 目录结构

```
me-digest/
├── SKILL.md                      # 完整流程规范（采集 → 整理 → QA Gate）
├── config/
│   ├── external_sources.yaml     # 外网一手源分层清单
│   └── wechat_accounts.txt       # 推荐监控的中文公众号清单（示例）
├── scripts/
│   ├── fetch_wechat_v2.py        # 公众号采集：搜狗搜索 + 全文下载（无需密钥）
│   ├── fetch_wechat_local.py     # 公众号采集：本地 exporter 混合通道
│   ├── fetch_latest_articles.py  # 公众号采集：最新文章（带频率控制退避）
│   └── check_links.py            # 【QA Gate】链接可达性 / 文章页 / 重复链接检查
├── references/
│   └── COLLECTION_WORKFLOW.md    # 采集与编译流程详细说明
└── templates/
    └── digest_template.md        # 每日简报 Markdown 模板
```

## 快速开始

### 1. 外网一手源（必做，无需任何依赖）

按 `SKILL.md` 的「阶段零 / 阶段一」和 `config/external_sources.yaml`，用任意搜索工具多关键词并行检索、打开原文核对，时间窗口取过去 24–48 小时。这部分不绑定任何特定工具或 API。

### 2. 中文公众号源（可选）

公众号采集依赖本地运行的 [wechat-article-exporter](https://github.com/wechat-article-exporter/wechat-article-exporter)：

```bash
# 1) 启动本地服务（默认 127.0.0.1:18901），并在浏览器扫码登录
# 2) 设置 exporter 项目目录（脚本据此自动发现登录密钥）
#    Windows PowerShell:
$env:WECHAT_EXPORTER_DIR = "C:\path\to\wechat-article-exporter-master"
#    macOS / Linux:
export WECHAT_EXPORTER_DIR="$HOME/wechat-article-exporter"

# 搜狗通道搜索 + 下载全文（不依赖登录密钥）
python scripts/fetch_wechat_v2.py --keyword "中东 投资" --download --output result.json

# 本地 exporter 通道：验证公众号 / 批量取最新文章
python scripts/fetch_wechat_local.py verify "看中东 DeepMENA"
python scripts/fetch_latest_articles.py --accounts-file config/wechat_accounts.txt --output latest.json
```

> 微信已关闭历史文章列表接口、搜狗对官方号收录有延迟且按相关度排序，公众号通道只能作为补充；重要官方新闻以官网直采 + 通讯社为准。详见 `references/COLLECTION_WORKFLOW.md`。

### 3. 编译 + 质量门

按 `templates/digest_template.md` 整理成中文简报，发布前校验所有原文链接：

```bash
# 支持 .html（提取"阅读原文"链接）或 .md（提取所有外链）
python scripts/check_links.py digest.html
python scripts/check_links.py digest.md
```

脚本在发现死链 / 列表页 / 重复链接时以非零码退出，可直接接入 CI 或流水线阻断发布。

## 信源红线（摘要）

- **不作为信源**：今日头条 / 头条号、抖音、快手、微博、B站、公众号搜狗中转页等 UGC / 自媒体平台（只能当线索，须回溯权威源）；首页 / 栏目页 / 列表页链接。
- **突发只采权威源已确认事实**：通讯社（Reuters / AP / AFP / Bloomberg / Anadolu）、官方通讯社（SPA / WAM）、央视 / 新华社 / 中新社等；自媒体推测的武器型号、拦截数、伤亡数不写。
- 以**原始稿件时间戳**为准，转载平台时间不等于首发时间。

## 免责声明

本项目仅用于公开信息的聚合与研究，自动采集请遵守目标网站的服务条款与当地法律法规；简报内容不构成任何投资建议。

## License

MIT
