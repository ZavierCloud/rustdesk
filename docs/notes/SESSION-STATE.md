# 会话状态快照（Session State）

> 新会话请先读本文件，再读各仓库 `progress.md`。本文件是当前进度的唯一权威快照。

更新时间：2026-10-21

## 目标

把 RustDesk 去品牌化为 `rd_client` / `rd_server`：产物不被识别为 rustdesk，功能不变，端口 +10（21124–21129），不保留与官方生态互通。

## 仓库与提交

| 仓库 | 位置 | 当前提交 | 说明 |
| --- | --- | --- | --- |
| 客户端 | `rustdesk/` | `2a67640d2` | 已 push 到 `ZavierCloud/rustdesk` master |
| 服务端 | `rustdesk-server/` | `9adf6c4` | 已 push 到 `ZavierCloud/rustdesk-server` master |
| 共享库 | 两端 `libs/hbb_common` | `f2e726e` / `e376512` | fork `ZavierCloud/hbb_common` 的 `rd-client` / `rd-server` 分支 |

## 已完成

- 品牌/产物改名：`rd_client`、`RDClient.exe`、`RDClient.app`、`librd_client.*`（macOS/Linux）、`rd_client.dll`（Windows）、bundle `com.spidercloude.rdclient`
- 端口 +10：API 21124、NAT 21125、会合 21126(tcp+udp)、中继 21127、WS 21128/21129
- 内置服务器 `net.spidercloude.com` + 公钥 `C8RvT8Leur0Q51eRyP1K5U7ggeOjIkiuSTUkYHftgUI=`
- 图标全平台替换（png/ico/icns/mipmap/svg）
- macOS 产物构建并启动验证（62MB，ad-hoc 签名后 FFI 初始化正常）
- 服务器迁移上线：`rd-server-id/relay` 跑在 21124–21129，密钥/数据库沿用，设备 `55333116` 已注册；旧服务已停、旧端口与防火墙规则已清理
- **Windows CI 跑通**（`windows-build.yml`，run #8/#9 success，约 25–45 分钟）：vcpkg 源码获取三处根因已修（libyuv 走 `lemenkov/libyuv` 镜像、git 禁凭据交互、install 重试 3 次），产物 `rd_client-windows-x64-unsigned` ≈36.5 MiB
- **Windows 产物 strings 验收通过**（run #9 产物）：`verify-strings.sh` 白名单外 0 命中；`RDClient.exe` 0 命中，`rd_client.dll` 8 命中全为白名单（驱动名 3、`rustdesk.com` 文档链接 4、updater 仓库名 1）
- 产物内核对：`net.spidercloude.com` / `rd.spidercloude.com` 在、官方 `rs-ny.rustdesk.com` 不在、公钥在
- v9 用 `--remap-path-prefix` 消除了 dll 里 12 条 `D:\a\rustdesk\rustdesk\…` 构建路径与 runner 用户名
- 服务端 `cargo test` 全通过；客户端 `cargo check --lib` 通过

## 进行中

**v10 端口文案验证**：`2a67640d2` 把 `src/lang/*.rs` 47 文件 179 处提示/示例里的官方端口 +10（`UDP 21116`→`21126`、示例 `...:21117`→`21127`），Dart 两处 `hintText 21118`→`21128`。**待跑 CI 确认产物不再出现旧端口文案**。

## 待办

1. v10 CI 重跑 + 新产物 `verify-strings.sh` 复验（期望白名单外 0，且旧端口文案消失）
2. Windows 产物在真机跑起来实测（本机只能静态验收）
3. 代码签名：Windows OV/EV 或 Azure Trusted Signing；macOS Developer ID + notarization
4. 客户端 GUI 手工连 `net.spidercloude.com` 做端到端验证（另一台设备输入 `55333116`）
5. 本地家用部署（`LOCAL-DEPLOY.md` 已写，暂不执行；需路由器 21124–21129 + 21126/udp 映射）

## 关键文档

| 文件 | 内容 |
| --- | --- |
| `RENAME-PLAN.md` | 改造全记录、9 个构建坑、保留项白名单 |
| `WINDOWS-BUILD.md`（`rustdesk/` 内也有） | Windows 环境、bridge 生成、接续指引、坑清单 |
| `LOCAL-DEPLOY.md` | 家用部署、端口映射、密钥迁移、DDNS |
| `rustdesk-server/progress.md` | 服务端迁移与验证记录（已提交） |
| `rustdesk/progress.md`（本地不追踪） | 客户端侧会话交接 |
| `migrate-to-rd-server.sh` / `verify-strings.sh` | 迁移脚本 / 产物验收脚本（带白名单判定） |

## 保留项（不能改）

`RustDeskIddDriver Device`、`RustDeskPrinterDriver`、`RustDesk v4 Printer Driver`（驱动名）、`https://rustdesk.com/docs/...`（帮助链接）、`github.com/rustdesk*` 与 `rustdesk-org` 依赖源、`LICENCE` / `Copyright Purslane`（AGPL 归属）、`updater.rs` 的仓库名 `rustdesk`（fork 未改名）、`allow-https-21114` 配置键名（hbb_common 双端共用，非品牌特征）。

## Windows CI 三个已知坑（避免重犯）

1. 不要用 `git fetch <url> <sha> | tail` 判断可用性——管道会吃掉 exit code，导致把 404 仓库误判为可用（v7 因此挂死 55 分钟）。
2. vcpkg 的 clone/bootstrap 必须排在缓存恢复之前：缓存不含 `vcpkg.exe`。
3. 必须设 `GIT_TERMINAL_PROMPT=0` / `credential.interactive=false`：仓库 404 时 git 会等凭据输入而永久挂起，而不是失败。
