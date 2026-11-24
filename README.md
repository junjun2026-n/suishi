<!--
============================================================
文件名称：README.md
生成日期：2026-11-21
修改日期：2026-11-23
版本信息：v0.261115
作者：JUN
备注：本程序由AI辅助完成。
文件功能用途：介绍邃室功能、安装启动、WAF 接入与日常维护。
注意事项：业务端口与管理端口分别使用，部署前检查权限和数据备份。
============================================================
-->
# 邃室SuiShi

邃室是面向琼海 WAF 非法请求引流的 Python HTTP 蜜罐。提供独立的业务接收入口、管理员访问页面、自适应模拟场景、攻击特征识别、来源画像、请求检索、分页和详情。不包含 SSH、数据库协议模拟或任意程序执行环境。

代码仓库：[junjun2026-n/suishi](https://github.com/junjun2026-n/suishi)。可配合 WAF 使用，也可独立接收 HTTP 请求。

## 功能概览

| 功能 | 说明 |
| --- | --- |
| HTTP 诱饵 | CMS、Spring、Jenkins、GitLab、容器、数据服务、网关及文件调试页面 |
| 请求分析 | 特征识别、风险分类、来源画像、请求详情与 JSON 导出 |
| 联调验证 | 27 个固定内部回放场景，保存命中结果和模拟标记 |
| 持久存储 | SQLite、PostgreSQL、MySQL / MariaDB，连接测试与初始化迁移 |
| 管理与转发 | 管理员/只读用户、登录退出、UDP/TCP 日志转发 |

完整操作步骤见 [使用与部署说明](docs/USER_GUIDE.md)，数据库操作见 [数据库与用户管理](DATABASE_USERS.md)，转发格式见 [日志转发说明](LOG_FORWARDING.md)。

版本：v0.261115。作者：JUN。请遵守版权协议。采用 GPL-3.0 许可，全文见 LICENSE。

## 本地启动

```powershell
cd C:\20260501\qionghai\suishi
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\start.ps1
```

业务入口：http://127.0.0.1:8910 。管理入口：http://127.0.0.1:8911 。两个服务均绑定 0.0.0.0，局域网访问时替换为主机实际 IP。

管理员账号为 `admin`。首次运行生成随机密码，保存在 `runtime/admin-password.txt`；也可在启动前设置 `SUISHI_ADMIN_PASSWORD` 环境变量。不要将业务端口作为管理入口。HTTP Basic 应在本机、受信管理网络使用，跨不可信网络时通过 HTTPS 反向代理保护。

## WAF 接入

在 WAF 的“站点配置 → 蜜罐”页签中启用蜜罐，将地址填写为 `http://邃室所在主机IP:8910`，保存。先用测试站点触发已配置的拦截规则，确认邃室管理页出现对应请求，再上线。只有 WAF 按现有策略判定可引流的请求会进入蜜罐。

WAF 会附带 `X-Forwarded-For`、`X-WAF-Rule`、`X-WAF-Request-ID`。邃室仅对可信代理读取这些字段。设置 `SUISHI_TRUSTED_PROXIES` 为 WAF 的实际连接来源 IP/CIDR（逗号分隔），默认只信任本机回环。Docker 中要以容器实际看到的 WAF 来源地址为准，不要直接信任所有地址。

管理列表支持来源 IP、路径、规则搜索；详情包含 UTC 时间、来源及直连 IP、主机、方法、路径和查询参数、请求头、正文及 Base64 原始字节。WAF 自身会移除原请求的 Cookie 和 Authorization，因此蜜罐无法恢复这些被移除的字段。直连蜜罐的认证头同样会隐藏。正文最多保存 64 KiB，超限记录截断并返回 413。当前不解析 TLS 密文，HTTPS 由 WAF 卸载后转发 HTTP。

## Ubuntu / Docker

```bash
docker compose up -d --build
docker compose exec suishi cat runtime/admin-password.txt
```

Compose 默认业务端口对外发布，管理端口仅发布到宿主机回环地址；远程管理可配置 HTTPS 反向代理。镜像以普通用户运行，只读根目录，持久数据写入命名卷。蜜罐不需要挂载物理网卡。

## 蜜罐功能操作

- **访问记录**：按来源、路径、WAF规则搜索；按风险级别、开始/结束时间筛选，每页可选择20/50/100条。时间控件使用浏览器当地时间，保存统一使用UTC。
- **请求详情**：查看直连与来源IP、原始正文Base64、可读正文、WAF请求编号、命中依据、诱捕场景与SHA-256；支持单条JSON导出。哈希仅对应已保存正文，截断或超时记录不代表完整请求，也不构成日志防篡改证明。
- **来源画像**：聚合全部来源的请求量、路径数量、高风险次数、首次/最近访问时间，显示实际来源数量，点击访问轨迹查询相关记录。
- **统计**：累计请求、高风险请求、来源IP、来源TOP5、攻击TOP5。攻击TOP5基于最近5000条含特征命中的记录，同一请求可包含多个类别。
- **蜜罐配置**：选择自适应场景或统一门户；调整正文采集上限（1KiB～1MiB）、读取超时（1～30秒）。保存到数据库，下一个请求生效；默认上限64KiB、超时10秒。
- **历史记录清理**：按历史截止时间删除记录，界面要求确认；不可恢复，先停止写入并备份数据库。删除不会立即缩小SQLite文件。

自适应场景包含管理登录、API/健康检查、环境模板、Git配置及普通门户。所有内容均为固定模拟数据；登录提交只记录为失败，不建立真实会话。无需上传真实凭据或真实系统文件。

识别规则包含SQL注入、跨站脚本、路径穿越、命令执行、SSRF、敏感文件、扫描器、管理入口探测，支持两次URL解码。结果是启发式特征判断，可能误报或漏报，应结合原始请求核实；不代表完整攻击链分析或已成功入侵。仅可信代理传入的WAF命中规则参与关联。管理配置写入要求自定义操作头以阻止跨站表单提交。

## 数据与维护

数据库支持 SQLite、PostgreSQL、MySQL / MariaDB，管理页面提供连接测试和初始化迁移。初次部署默认使用 SQLite，可按自己的环境配置网络数据库。支持管理员和只读用户，默认 admin 不可删除。详见 [数据库与用户操作说明](DATABASE_USERS.md)。

## 日志转发

管理页新增“日志转发”，支持 UDP/TCP、JSON/Syslog/自定义格式、可选请求正文、发送测试及队列状态。默认关闭，启用后转发新增采集记录。接收端故障自动重试，队列持久保存，最多 10000 条。详细字段、分帧规则及迁移行为见 [日志转发使用说明](LOG_FORWARDING.md)。

## 攻击模拟验证

### 引流服务扩展

“蜜罐配置”新增 8 类响应模式和引流服务目录。自适应模式匹配全部诱饵；指定模式用于未知路径的默认响应，已识别路径优先匹配。

| 类型 | 典型路径 |
| --- | --- |
| WordPress / CMS | `/wp-login.php`、`/wp-json/`、`/xmlrpc.php` |
| Spring 运维 | `/actuator/health`、`/actuator/env`、`/actuator/mappings` |
| Jenkins | `/jenkins/login`、`/jenkins/api/json`、`/jenkins/script` |
| GitLab | `/users/sign_in`、`/api/v4/projects` |
| Docker / Kubernetes | `/version`、`/containers/json`、`/api/v1/pods` |
| Elasticsearch / Web 数据管理 | `/_cluster/health`、`/_cat/indices`、`/_search`、`/adminer.php` |
| 网关 / VPN / OA | `/vpn/login`、`/remote/login`、`/oa/login`、`/cgi-bin/luci/` |
| 文件 / 调试 | `/.git/HEAD`、`/backup.sql`、`/server-status`、`/swagger.json`、`/debug/pprof/` |

WAF 蜜罐目标仍填写 `http://邃室主机:8910`。新增类型提供承接路径和分类记录，不自动更改 WAF 引流规则。请按站点配置相应策略，保留原请求路径并配置可信代理来源。返回内容均为虚构样例，不创建容器、不连接集群、不开放原生数据库协议、不运行控制台代码或提供真实账号。

### 内部回放

管理页“攻击模拟”提供27个固定场景：保留 SQL注入、XSS、目录穿越、命令执行、SSRF 等原12项；新增 WordPress REST、XML-RPC、Spring 配置、Jenkins 控制台、GitLab、Docker、Kubernetes、Elasticsearch、VPN、OA、Swagger、调试接口、NoSQL 注入、LDAP 注入及 Java 序列化特征验证。

勾选需要的场景后点击“执行选中场景”，可展开查看请求样例。结果展示预期类别、实际命中类别、HTTP状态及关联请求详情；历史保存最近30次展示，数据库保留全部任务。每批最多32条，逐条执行，页面和服务器均防止重复并发执行。模拟没有自定义外部目标入口，不产生外部网络流量，不执行请求中的命令、脚本或文件。

此功能通过本应用内部ASGI回放，验证蜜罐采集、攻击识别、响应和日志记录；不经过WAF、网卡或TLS入口，因此不能代替真实WAF引流联调，也不模拟DDoS或高并发压测。规则匹配通过不代表防护已经覆盖该类攻击的所有变体。

模拟日志的 `simulation_run` 字段记录任务编号；访问查询API通过 `traffic=simulation`、`traffic=real` 或默认 `traffic=all` 区分。当前统计与来源画像包含模拟记录，请查询时注意标记。正文样例、响应、命中依据在界面中均按文本展示。

初次未配置数据库时采用 SQLite WAL，数据文件为 `runtime/suishi.db`；配置网络数据库后，新数据写入所选数据库，连接设置保存在 `runtime/database.json`。可用 `SUISHI_DATA_DIR` 修改运行目录。升级保留已有记录，旧记录不会自动补分析。备份需包括当前数据库和整个 runtime；Docker 备份对应数据卷。采集记录可能包含攻击载荷及敏感正文，限制目录访问权限。需按容量定期归档或手动清理。此版本不自动修改 WAF 配置。

测试：`.\.venv\Scripts\python.exe -m pytest tests -q`。

蜜罐仅返回固定模拟页面，不执行命令、不连接攻击者指定的上游、不提供真实文件。建议业务网络只允许 WAF 访问蜜罐入口，并将蜜罐部署在隔离网络。
