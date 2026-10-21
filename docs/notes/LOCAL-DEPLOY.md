# 本地（家用）部署 RD Server

把 `rd_server` 跑在本地设备上，通过路由器端口映射对外提供服务。本文覆盖前提条件、端口映射、三种运行方式、密钥迁移与切换策略。

## 1. 前提条件（先确认，否则白折腾）

| 条件 | 说明 | 怎么查 |
| --- | --- | --- |
| 公网 IPv4 | 路由器 WAN 口拿到的是公网地址，不是你运营商内网地址（`100.64.x.x` / `10.x.x.x` 就是 CGNAT，映射无效） | 路由器状态页 WAN IP vs `curl ifconfig.me` 是否一致 |
| 上行带宽 | 远程桌面按 2–8 Mbps/会话估算；监控/多路并发要更高 | 测速网站看 upload |
| NAT 类型 | 全锥形（Full Cone）打洞成功率最高；对称 NAT 会大量走中继 | 用 RustDesk 客户端的 NAT 类型检测（会走 21125） |
| 运营商限制 | 部分家宽封 80/443，或封 UDP；21126/udp 被封会退化为中继 | 用 `nc -u` 或客户端连接观察是否 always relay |
| 电力/网络稳定性 | 家用断电/重启会让所有客户端掉线 | 建议 UPS + 路由器 DHCP 静态绑定 |

## 2. 端口映射（路由器 → 本地设备）

映射**外部端口与内部端口保持一致**，否则客户端要逐个改端口（客户端内置 21126/21127）。

| 外部端口 | 内部端口 | 协议 | 用途 | 必需 |
| --- | --- | --- | --- | --- |
| 21124 | 21124 | TCP | 控制台 / API | 是（要用控制台时） |
| 21125 | 21125 | TCP | NAT 类型检测 | 是 |
| 21126 | 21126 | TCP **+ UDP** | 会合服务（核心） | 是（UDP 尤其关键） |
| 21127 | 21127 | TCP | 中继 | 是 |
| 21128 | 21128 | TCP | WebSocket 会合 | 可选 |
| 21129 | 21129 | TCP | WebSocket 中继 | 可选 |

注意：
- **21126 的 UDP 必须映射**，否则打洞失败、全部走中继，延迟和带宽都会变差
- 不要只映射 TCP 就以为完事
- 本地设备用 DHCP 静态绑定，避免 IP 变化导致映射失效

## 3. 三种运行方式

### 方式 A：Docker（推荐，跨平台一致）

仓库自带 `docker-compose.yml`，已改名为 `rd_server_id` / `rd_server_relay` 并映射 21125–21129：

```bash
cd rustdesk-server
docker compose up -d --build
docker compose logs -f rd_server_id
```

数据目录是 `./data`（挂载到容器 `/root`），密钥与 `db_v2.sqlite3` 都在里面。

### 方式 B：macOS 原生（本机就是 Mac 时）

```bash
cd rustdesk-server
cargo build --release --locked
mkdir -p ~/rd_server && cp target/release/rd_server_id target/release/rd_server_relay ~/rd_server/
cd ~/rd_server && ./rd_server_id          # 前台跑，确认能监听 21124/21126
```

常驻用 `launchd`（`~/Library/LaunchAgents/com.spidercloude.rdserver.plist`），`KeepAlive=true`、`WorkingDirectory` 指向 `~/rd_server`。

> macOS 上跑不了服务器上那个 linux/amd64 二进制，必须本机重新编译（或走 Docker）。

### 方式 C：Linux 小主机 / NAS

```bash
cargo build --release --locked           # 或直接用服务器上编译好的 amd64 产物
mkdir -p /opt/rd_server && cp target/release/rd_server_{id,relay} /opt/rd_server/
```

systemd 单元参考 `docs/deployment-centos9.md`，把 `WorkingDirectory` 指到 `/opt/rd_server`。

## 4. 密钥迁移（最关键的一步）

客户端已经信任公钥 `C8RvT8Leur0Q51eRyP1K5U7ggeOjIkiuSTUkYHftgUI=`。本地部署**必须沿用同一对密钥**，否则所有客户端都要改 Key：

```bash
# 从现网服务器拷回（不要重新生成！）
scp MySpiderServer:/opt/rd_server/id_ed25519      ./data/
scp MySpiderServer:/opt/rd_server/id_ed25519.pub  ./data/
scp MySpiderServer:/opt/rd_server/db_v2.sqlite3*  ./data/   # 保留用户/设备/策略数据
```

`WorkingDirectory`（或 compose 的 volume）必须是这两个文件所在目录，否则会生成新密钥。

## 5. 域名与动态 IP

`net.spidercloude.com` 现在指向云服务器 `149.88.68.22`。切到家用后：

| 场景 | 做法 |
| --- | --- |
| 家宽是固定公网 IP | 把 `net.spidercloude.com` 的 A 记录改成家用 IP |
| 家宽是动态 IP | 用 DDNS：路由器自带 DDNS，或设备上跑 `ddclient` / Cloudflare API 脚本，每分钟更新一条 A 记录（如 `home.spidercloude.com`） |
| 想云端/家里双活 | 客户端 ID 服务器只能填一个；可用 DDNS 记录在两边切换，或保持云端为主、家里做备份 |

客户端侧配置不变（仍是 `net.spidercloude.com` + 内置 Key），只要 DNS 指过来就行。

## 6. 与现网云服务器切换

```bash
# 1) 家里起服务并确认监听
ss -lntup | grep -E '2112[4-9]'
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:21124/api/login-options

# 2) 改 DNS 指向家用 IP（TTL 提前调小到 60s）
# 3) 客户端重连（重启客户端或等它自动重连）
# 4) 观察 1–2 天无异常后，云端停服务
systemctl disable --now rd-server-id rd-server-relay
```

回滚：DNS 改回云服务器 IP，`systemctl start rd-server-id rd-server-relay`。

## 7. 家用部署的额外风险

| 风险 | 说明 | 缓解 |
| --- | --- | --- |
| 家庭 IP 被扫描/攻击 | 21124 直接暴露公网 | 控制台走 nginx + HTTPS，或只在内网访问；`firewall-cmd`/`ufw` 限制 |
| 断网断电 | 远程协助全部失效 | UPS、手机热点备份、保留云端作为第二 ID 服务器方案 |
| 上行带宽不足 | 多路并发卡顿 | 限制画质/码率，或继续用云端中继 |
| 无固定 IP | DNS 失效 | DDNS + 短 TTL |
| 无 DDNS 时的兜底 | 客户端可填 IP | 支持 `IP:端口` 形式，但 IP 变化就得重配 |

## 8. 建议的落地顺序

1. 确认公网 IP 非 CGNAT 且上行 ≥ 30 Mbps
2. 路由器做 21124–21129 + 21126/udp 映射
3. 本地设备跑起来（Docker 最省事），**沿用旧密钥**，先用局域网 IP 验证
4. DDNS 配好，把 `net.spidercloude.com` 指向家用 IP（TTL 60s）
5. 用另一台设备（手机流量）验证外网连接
6. 观察稳定后再决定是否停云端
