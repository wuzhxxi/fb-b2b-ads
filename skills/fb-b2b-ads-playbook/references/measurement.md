# 指标与数据口径

## 复盘前核对

核对日期范围、广告账户时区/币种、层级、归因窗口、平台结果定义、点击口径、去重键、分解维度、平台与 CRM 获客映射、销售评估延迟。不能把 Campaign 总计与 Ad Set 明细一起相加；不能把年龄/版位分解表与同层级总计相加。ID 与报告期唯一，名称不代替 ID。

累计 Reach 是去重人数，跨广告/日期不得求和；指标平均数不能直接平均，需要用合计分子/分母重算。不同币种/时区/归因窗口/结果定义不得混算。`0` 是确认的零，`null` 或缺列是未知。

## 本地脚本输入

从原始导出或截图准确转录到 JSON；Excel/CSV 列名需先映射，本脚本不直接读表格或 OCR。无法确认点击类型时不映射 `link_clicks`。保留原始口径说明，不传原始个人联系方式。

`context` 必填：`currency`（三位大写代码）、`timezone`（IANA，如 Asia/Shanghai）、`date_start`/`date_end`（ISO 日期）、`grain`（campaign/ad_set/ad）、`attribution_window`、`results_definition`。不知道关键口径则先报告缺项，不编造填值。

可选布尔字段默认 false：

- `crm_cohort_aligned`：CRM 评估/报价/成交/收入对应本批获客队列，而非报告日期内所有历史成交。
- `crm_deduplicated`：CRM 每列是去重后独立线索；汇总前还要确认线索跨行只分配一次。
- `rows_disjoint`：花费和平台结果来自同一粒度、不重叠的行，且 CRM 线索跨行不重复。不能仅靠脚本推断。

`rows` 是非空数组，每行 `id` 唯一；可包含同名 `context` 覆盖，用于分组展示不同口径，此时不汇总。禁止同一输入混放多层级总计/明细。数值字段必须是 JSON 数字或 null，不能含千分位符、货币符或百分号。

| 字段 | 定义 |
| --- | --- |
| spend / impressions / reach | 实际花费 / 展示 / 该行期间去重触达 |
| link_clicks / landing_page_views | 明确的链接点击 / 落地页浏览；不等于 All clicks |
| results | 平台原生结果，定义在 context 中；不是 CRM 线索 |
| leads | 本批获客的去重线索；会话/表单按去重映射后计入 |
| assessed_leads / qualified_leads | 已评估 / 其中合格，待评估不计为无效 |
| quotes / wins | 该批合格线索中获得报价 / 成交的独立线索数；不是报价单或订单张数 |
| revenue / contribution_profit | 同队列实际收入 / 定义清楚的贡献利润；利润可负；退款需先按一致规则处理 |

脚本校验已评估 ≤ 线索、合格 ≤ 已评估/线索、报价/成交 ≤ 合格；不要求成交 ≤ 报价，因为某些业务不记录报价。数字为非负，贡献利润允许负数。脚本不验证 Meta 真实性、样本显著性、日志去重或字段语义；这些由分析者确认。

示例输入见 `assets/sample-metrics.json`，全部是合成数据。运行：

```bash
python scripts/analyze_metrics.py --input /path/to/normalized-metrics.json --output /path/to/result.json
```

## 指标解释

| 指标 | 公式 | 使用边界 |
| --- | --- | --- |
| CPM | 花费/展示 × 1000 | 拍卖/受众诊断，不是线索质量 |
| CTR(link) | 链接点击/展示 × 100% | 不与 All CTR 混用 |
| CPC(link) | 花费/链接点击 | 分母零不可计算 |
| Frequency | 展示/该行 Reach | 汇总省略，Reach 不可跨行相加 |
| 平台结果成本 | 花费/results | 必须注明结果是提交、会话还是其他事件 |
| CPL | 花费/去重线索 | 需确认去重 |
| 已评估覆盖率 | assessed/leads × 100% | 低覆盖时质量结论暂定 |
| 合格率（已评估） | qualified/assessed × 100% | 不是 qualified/全部 leads；可能有评估选择偏差 |
| CPQL | 花费/合格线索 | 同获客队列且去重；未评估完时仅为暂定 |
| 报价/成交率 | quotes 或 wins/qualified × 100% | 同队列成熟后判断 |
| CAC（仅广告费） | 花费/成交线索 | 不包括销售与其他渠道成本 |
| ROAS | 同队列收入/花费 | 不等于利润或增量效果 |
| 贡献利润/广告花费 | 同队列贡献利润/花费 | 需说明贡献利润是否已包含广告费，避免重复扣除 |

缺分子、缺分母或零分母输出 `null`；零合格线索时保留“0 合格”的事实，CPQL 写不可计算，不写成 0 或无限大。上下文冲突或重叠未确认则省略汇总。未知字段不会补为零，汇总中任何行缺某字段则该合计未知。

报告结果还需阅读警告并核查：队列是否成熟、未评估占比、销售响应、国家/素材样本数量与追踪可靠性。不根据脚本结果自动选赢家或改预算。
