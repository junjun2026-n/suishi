<!--
文件名称：USER_GUIDE.md
生成日期：2026-11-23 | 修改日期：2026-11-23 | 版本信息：v0.261115
作者：JUN
备注：本程序由AI辅助完成。用途：说明邃室安装、引流、分析和维护流程；注意：部署凭据和采集数据不得上传仓库。
-->
# 邃室SuiShi 使用与部署说明

## 1. 获取与启动

需要 Python 3.10 或更新版本，或者 Docker Engine 与 Compose 插件。

```bash
git clone https://github.com/junjun2026-n/suishi.git
cd suishi
python -m venv .venv
```

Windows：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\start.ps1
```

Ubuntu：

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py
```

业务端口为 `8910`，管理端口为 `8911`，均监听 `0.0.0.0`。管理地址使用实际服务器 IP，例如 `http://localhost:8911`。管理员为 `admin`，初始随机密码保存在 `runtime/admin-password.txt`，首次启动也可通过 `SUISHI_ADMIN_PASSWORD` 指定。初始化后修改密码以数据库中的哈希为准。

## 2. Docker 部署

```bash
docker compose up -d --build
docker compose logs --tail=100 suishi
docker compose exec suishi cat runtime/admin-password.txt
```

默认仅将管理端口绑定宿主机 `127.0.0.1:8911`，可通过 SSH 隧道或 HTTPS 反向代理访问。业务端口 `8910` 对外发布。持久数据使用 `suishi-data` 命名卷；重新构建镜像不会重置数据，删除数据卷会丢失本地配置和 SQLite 数据。

| 环境变量 | 用途 |
| --- | --- |
| `SUISHI_DATA_DIR` | 运行目录，默认项目下 runtime |
| `SUISHI_ADMIN_PASSWORD` | 首次初始化 admin 密码 |
| `SUISHI_TRUSTED_PROXIES` | 可信 WAF 来源 IP/CIDR，逗号分隔 |
| `SUISHI_PORT` | 业务监听端口，默认 8910 |
| `SUISHI_ADMIN_PORT` | 管理监听端口，默认 8911 |

修改容器监听端口时需同步修改 Compose 端口映射。数据库凭据由管理界面配置，不要写入镜像或提交代码库。

## 3. WAF 引流与验收

1. 在 WAF 的蜜罐配置页启用引流，目标为 `http://蜜罐主机:8910`。
2. 将邃室的可信代理设置为实际 WAF 连接来源 IP/CIDR；Docker 部署可在环境或本地 `.env` 设置 `SUISHI_TRUSTED_PROXIES`，再重新创建容器。
3. 按 WAF 的站点规则选择需要引流的请求。邃室不会自动修改 WAF 规则。
4. 通过测试站点发送符合测试规则的请求，在访问记录中核对原始来源、直连 IP、路径、WAF 规则和请求编号。
5. 对照 WAF 日志中的 `X-WAF-Request-ID` 确认对应关系。

WAF 转发的请求应保留路径，附带 `X-Forwarded-For`、`X-WAF-Rule`、`X-WAF-Request-ID`。只有来自可信代理的这些字段会被采用。HTTPS 在 WAF 卸载后使用 HTTP 转发；不提供 TLS 密文解密。

## 4. 采集与分析

在“蜜罐配置”选择自适应或固定默认场景，保存后对后续请求生效。自适应匹配管理门户、CMS、Spring、Jenkins、GitLab、容器、数据服务、网关和文件调试路径。

访问记录可按来源、路径、风险和时间筛选；详情展示原始正文 Base64、可读正文、SHA-256、命中特征及 WAF 关联字段，可导出单条 JSON。来源画像聚合来源访问轨迹。正文有大小和读取超时限制，截断记录中的哈希只对应已保存字节。认证头会隐藏，无法还原 WAF 已移除的 Cookie 或 Authorization。

攻击特征是启发式匹配，须结合请求核实。诱饵返回固定虚构内容，不执行载荷、连接请求指定的上游或创建真实服务。

## 5. 攻击模拟

管理页勾选固定场景并执行，可查看预期类别、实际类别、HTTP 状态和关联记录。一次最多 32 项；当前提供 27 个固定场景。模拟通过内部 ASGI 回放，不能代替 WAF、网络和 TLS 联调，也不用于容量压测。

模拟数据带 `simulation_run` 标记，统计和来源画像包含模拟记录。访问查询 API 可用 `traffic=real` 或 `traffic=simulation` 区分。

## 6. 数据库、用户和日志转发

数据库配置支持 SQLite、PostgreSQL、MySQL / MariaDB。先创建目标数据库及专用用户，测试连接后执行初始化迁移；目标应为空库，现有数据不会被强制覆盖。详见 [数据库与用户管理](../DATABASE_USERS.md)。

用户支持管理员和只读角色。默认 admin 不可删除、禁用或降权。管理员可重置其他用户密码；改密、禁用或删除立即撤销相应会话。

日志转发支持 UDP/TCP、JSON、Syslog 和自定义格式。填写接收地址、端口并发送测试，确认接收端成功后启用；默认只转发启用后的新增记录。队列持久保存，最多 10000 条。详见 [日志转发说明](../LOG_FORWARDING.md)。

## 7. 备份、升级和排查

- 备份当前数据库以及整个运行目录或 Docker 数据卷；备份含敏感日志，应限制访问。
- 升级前备份，拉取代码并安装依赖，Docker 执行 `docker compose up -d --build`。
- 管理页无法访问时检查是否误用业务端口，以及 Docker 回环端口绑定。
- 来源 IP 不正确时核对可信代理与容器实际看到的 WAF 地址。
- 数据库无法启动时检查连接设置、服务可达性和建表权限；不会静默切回 SQLite。
- 转发失败时检查接收端口、协议、网络和队列状态。
- 尚未提供最大请求吞吐量承诺，部署容量应按正文大小、数据库和实际访问进行压测。

## 8. 开发验证与许可

```bash
.venv/bin/python -m pytest tests -q
```

Windows 使用 `.venv\Scripts\python.exe`。测试使用独立临时目录与模拟请求。

版本 `v0.261115`，作者 JUN，版权归本人所有。本项目包含 AI 辅助开发内容，采用 GPL-3.0，完整许可见 [LICENSE](../LICENSE)。运行密码、私钥、数据库和真实采集日志不包含在公开仓库中。
