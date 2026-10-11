# 小优 B2B 投流 Skill · v2.0

面向外贸批发、工厂、进口商、分销商与项目采购的 Facebook / Instagram 投流助手。基于用户上传的 `fb-b2b-ads-playbook` 升级，保留新产品重置、截图指导、多语言广告与真实性要求。

## 本次升级

- 从生成投放配置扩展为「产品事实→市场测试→采购链路→线索筛选→数据复盘→可控实验」。
- 不再把 WhatsApp 固定对应互动目标；按实际账户判断潜在客户或消息互动路径。
- 加入有效线索成本、已评估覆盖率、报价与成交队列；避免只凭 CPL/CTR 决策。
- 加入预算总分校验、测试主变量、观察条件、止损和扩量实验，删除固定行业阈值假设。
- 修正语言过滤、年龄/性别和受众扩展的机械建议；当前平台字段需要截图/官方资料核实。
- 添加跨平台的本地 JSON 指标脚本，检查重复、缺失、口径冲突、零分母、CRM 队列与触达汇总。

## 安装与使用

将 `skills/fb-b2b-ads-playbook` 整个目录复制到 Codex 的技能目录。未设置 `CODEX_HOME` 时通常是 `~/.codex/skills/`；否则使用 `$CODEX_HOME/skills/`。根据所用客户端重新加载技能。

```text
$fb-b2b-ads-playbook
为这个产品做首轮外贸 B2B 测试方案，总预算 USD 140。

$fb-b2b-ads-playbook
根据这张后台截图，告诉我选哪个转化位置。

$fb-b2b-ads-playbook
这批询盘很便宜但无效，请结合销售跟进结果复盘。

结束，下一个产品。
```

产品截图不证明材质、MOQ、认证或品牌授权。未补齐的配置是草稿。Skill 提供流程与素材，不自带 Meta/WhatsApp/CRM 连接器，也不会因安装而自动发布广告。

## Windows、macOS 与 Linux

Skill 与 Python 脚本可在 Windows、macOS、Linux 运行。需要 Python 3.9+；路径含空格时按对应终端的引号规则引用。下面的命令从仓库根目录运行。

Windows PowerShell：

```powershell
py -3 -m unittest discover -s tests -v
py -3 skills/fb-b2b-ads-playbook/scripts/analyze_metrics.py --input skills/fb-b2b-ads-playbook/assets/sample-metrics.json
```

macOS / Linux：

```sh
python3 -m unittest discover -s tests -v
python3 skills/fb-b2b-ads-playbook/scripts/analyze_metrics.py --input skills/fb-b2b-ads-playbook/assets/sample-metrics.json
```

脚本本身只用 Python 标准库，不依赖 bash。它还需要 IANA 时区资料：macOS/Linux 通常提供系统数据库；Windows 或精简容器若报 `IANA timezone data is unavailable`，先安装可选的 `tzdata`：

```powershell
py -3 -m pip install tzdata
```

其他系统可运行 `python3 -m pip install tzdata`。如使用虚拟环境，先激活环境再安装。示例数据是合成数据。真实输入格式与口径见 `skills/fb-b2b-ads-playbook/references/measurement.md`；脚本只读取标准化 JSON，不直接读取 Excel/CSV 或接入广告账户。

GitHub Actions 会在 Windows、macOS 和 Ubuntu 上运行指标测试。

## 本地数据工具

运行结果保存到文件时，`--output` 指定目标路径：

```sh
python3 skills/fb-b2b-ads-playbook/scripts/analyze_metrics.py --input skills/fb-b2b-ads-playbook/assets/sample-metrics.json --output metrics-result.json
```

真实输入按 `references/measurement.md` 映射成 JSON。原始表格不直接输入；不上传个人线索、令牌或广告账户秘密。脚本只算描述性指标，不判统计显著性、不自动暂停或扩量。平台动态规则需在使用时重新核实。

技能正文放在 `skills/fb-b2b-ads-playbook/SKILL.md`；参考流程按任务读取，脚本与示例在相同目录下。

## 版本依据与限制

升级日期：2026-10-11。以外层 ZIP 中带产品重置规则的完整版本为基础；未把嵌套旧版本或压缩包系统元数据带入仓库。仓库忽略 Finder 与 Windows 缩略图等系统文件。官方来源与核验状态见 `references/platform-verification.md`。帮助中心登录墙所阻挡的内容标记为未核实，未将经验预算或比例包装成官方规则。

