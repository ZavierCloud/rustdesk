# 去品牌化改造计划（rustdesk → rd_client / rd_server）

## 1. 目标与验收

| 项 | 验收标准 |
| --- | --- |
| 品牌 | 用户可见处（窗口标题、托盘、安装包、控制台、文案）不出现 RustDesk |
| 产物标识 | 二进制名、库名、bundle id、applicationId、服务名、注册表键、配置目录、日志全部换名 |
| 产物字符串 | `strings <产物> \| grep -i rustdesk` 无命中（`LICENCE` 归属声明除外） |
| 功能 | 客户端 ↔ 自建服务端连接、打洞/中继、剪贴板、文件传输、控制台登录/策略下发与改造前一致 |
| 合规 | 保留 `LICENCE`、版权头、上游归属说明（AGPL-3.0 要求），不得删除 |

## 2. 现实边界（重要）

改名解决的是**静态特征**：文件名、PE/ELF/Mach-O 元数据、bundle id、注册表、路径、可打印字符串、默认域名。

改名**不能**解决：
- **行为检测**：屏幕捕获、输入注入、自启动、提权、常驻服务——远控软件的核心行为面
- **证书与信誉**：无代码签名必被 SmartScreen 拦截；新签名的信誉积累需时间
- **网络特征**：端口 21114–21119、握手协议、TLS 指纹；不改端口与协议则网络侧仍可识别
- **图标与 UI 视觉**：必须换图标资源，否则视觉/哈希匹配仍命中

结论：本计划只保证"静态标识与字符串不再指向 RustDesk"。要真正降低误报，需要配套：代码签名证书、企业/厂商白名单报备、图标与 UI 视觉替换、必要时改端口与协议特征。

## 3. 命名映射

| 对象 | 现值 | 新值 |
| --- | --- | --- |
| 产品显示名（客户端） | `RustDesk` | `RD Client` |
| 产品显示名（服务端） | `RustDesk Server` / `RustDesk 控制台` | `RD Server` / `RD Server 控制台` |
| 客户端 crate / bin | `rustdesk` | `rd_client` |
| 客户端 lib | `librustdesk`（产物 `librustdesk.dll/.so/.dylib/.a`） | `rd_client`（产物 `librd_client.*`） |
| 服务端 bin | `hbbs` / `hbbr` / `rustdesk-utils` | `hbbs` / `hbbr` / `rd_server-utils`（hbbs/hbbr 不变，避免破坏部署脚本与协议习惯） |
| 服务端包名 | `hbbs` | `rd_server` |
| macOS bundle id | `com.carriez.rustdesk` | `com.spidercloude.rdclient` |
| Android applicationId / namespace | `com.carriez.flutter_hbb` | `com.spidercloude.rdclient` |
| Android Kotlin 包目录 | `com/carriez/flutter_hbb` | `com/spidercloude/rdclient` |
| Windows 服务 | `RustDesk Service` | `RD Client Service` |
| Windows 数据目录 | `%ProgramData%\RustDesk` | `%ProgramData%\RDClient` |
| 配置目录 | `~/.config/rustdesk`、`%APPDATA%\RustDesk` | `rd_client`（`RDClient`） |
| systemd 单元 | `rustdesk-hbbs/hbbr` | `rd-server-hbbs/hbbr` |
| 安装路径 | `/opt/rustdesk/rustdesk-server`、`/var/lib/rustdesk-server` | `/opt/rd_server`、`/var/lib/rd_server` |
| 默认服务器 | `rs-ny.rustdesk.com` 等官方 | `net.spidercloude.com`（自建） |
| 剪贴板 owner 格式 | `dyn.n.owner`（`RUSTDESK_CLIPBOARD_OWNER_FORMAT`） | `rdclient.n.owner` |
| 控制台 token key | `rustdesk_console_token` | `rd_server_console_token` |
| JWT issuer | `RustDesk Server` | `RD Server` |

用户原文的 `rd_clinet` 按 `rd_client` 处理（拼写修正，若确需 `rd_clinet` 请说明）。

## 4. 分层改动清单

### A 层：品牌常量与产物标识（必做，低风险）

客户端：
- `Cargo.toml`：`package.name`、`description`、`authors`、`default-run`、`[lib] name`、`[[bin]]`
- `librustdesk` 全部引用：`build.py:639,656,766,789,901,924,932`、`flutter/windows/CMakeLists.txt:106,108`、`flutter/windows/runner/main.cpp:26,29`、`flutter/build_fdroid.sh:469,470`、`flutter/ios/Runner.xcodeproj/project.pbxproj:33,115`、`src/main.rs:6`、`src/service.rs:1,10`、`examples/ipc.rs:6`
- `APP_NAME` 相关逻辑：`src/common.rs:1064-1082,2381`、`src/core_main.rs:249,281`（注意 `common.rs:1069` 用 `eq("RustDesk")` 判定，必须同步改）
- 默认服务器与公钥：`libs/hbb_common`（客户端子模块与服务端副本**必须同步**）
- 剪贴板格式：`src/clipboard.rs`
- Windows：`src/platform/windows.rs`（`rustdesk.exe`、`ProgramData\RustDesk`、`RustDeskCustomClientStaging`、`rustdesk-*.msi` 文件前缀、服务名、注册表、窗口类名）
- 图标/文件名资源：`res/rustdesk.desktop`、`res/rustdesk-link.desktop`、`res/msi/*.wxs`、`res/msi/preprocess.py`、`res/job.py`、`res/DEBIAN/*`

服务端：
- `Cargo.toml`：`package.name`、`authors`、`[[bin]] rustdesk-utils`
- `systemd/rustdesk-hbbs.service`、`rustdesk-hbbr.service`（文件名与内容）
- `src/main.rs:28`（`init_args` 显示名）、`src/hbbr.rs:23-24`、`src/common.rs:123`、`src/utils.rs`（帮助文案）
- `console/`：`index.html` 标题、`package.json` name、`AppLayout.tsx`、`Login.tsx`、`api/client.ts`、`src/api/console.rs`（JWT issuer）
- `docker-compose.yml`、`docker*/`、`kubernetes/example.yaml`、`Dockerfile*`（镜像 tag 与路径）

### B 层：打包与系统集成（中风险，改错会装不上/起不来）

- macOS：`flutter/macos/Runner.xcodeproj/project.pbxproj`（3 处 bundle id）、`Info.plist`、授权 plist（`agent.plist`/`daemon.plist` 的 label）
- iOS：`flutter/ios/Runner/Info.plist`、`exportOptions.plist`、pbxproj 库名
- Android：`build.gradle`（namespace/applicationId）、3 个 `AndroidManifest.xml`、Kotlin 包路径重命名、`res/values/strings.xml`、`fastlane/metadata`
- Windows：`flutter/windows/runner/Runner.rc`（产品名/公司名）、`main.cpp`、`res/msi/*`、NSIS（`ui/setup.nsi`，服务端）
- Linux：`res/*.desktop`、`flatpak/com.rustdesk.RustDesk.metainfo.xml` + `rustdesk.json`（id/name/icon/exec）、`appimage/*.yml`
- 服务端：systemd 单元文件名与 `ExecStart`/`WorkingDirectory`/日志路径、`docs/deployment-centos9.md` 中的安装路径

### C 层：UI 与多语言文案（低风险，量大）

- `src/lang/*.rs`（54 文件）：只替换品牌词 `RustDesk` → `RD Client`，不动翻译键、占位符、字符串结构
- `flutter/lib`（37 文件）：标题、关于页、提示语
- `console/src`：标题与用户可见文案

### D 层：源码内部标识符（可选，对产物检测几乎无收益）

- 函数/变量名如 `try_kill_rustdesk_main_window_process`、注释里的 GitHub 链接与 issue 引用
- 建议：**不做**。Cargo/编译器不会把函数名写入 release 产物（panic 只带 `文件:行`），改名只增加 diff 与回归风险。若必须"源码无 rustdesk 字样"，作为独立阶段并在每平台回归。

### E 层：协议与端口（高风险，默认不动）

- protobuf `package hbb`、握手 `version` 字段、端口 21114–21119：改则与官方客户端/服务端互不兼容，且需同步改防火墙、nginx、部署文档
- 默认建议：保留，仅在自建生态内使用；若确需改端口，单独排期并做两端同步验证

## 5. 关键风险与对策

| 风险 | 后果 | 对策 |
| --- | --- | --- |
| `librustdesk` 引用链漏改 | 编译失败或运行时找不到库（Windows/macOS/Android/iOS 各有引用点） | 以 `rg librustdesk` 为清单逐个改，四平台各编译一次 |
| 客户端与服务端 `hbb_common` 副本不一致 | 协议/配置语义漂移，连接异常 | 客户端子模块当前为**空目录**，需先初始化；改域名/常量时两副本同步，`diff -rq` 校验 |
| 配置目录/服务名/bundle id 改动 | 旧版配置不迁移，等同全新安装；Android 视为新应用 | 接受（品牌隔离）；如需要则写迁移逻辑，单独评估 |
| `common.rs:1069` 用 `eq("RustDesk")` 判定 | 只改显示名会导致自定义客户端判定失效 | 同步修改判定值 |
| 二进制内嵌 crate 名 | `strings` 命中 `rustdesk` | 改 `package.name` 为 `rd_client` 后重建 |
| 图标未换 | 视觉与哈希匹配仍可识别 | 替换 `res/` 全部图标与 logo，重新生成各平台图标集 |

## 6. 执行顺序

1. 初始化客户端子模块，建立编译基线（改动前 `cargo check` + `strings` 计数）
2. 客户端 A 层 → `cargo check` → 改 B 层 → macOS 构建验证
3. 服务端 A 层 → `cargo check` + `npm run build`
4. C 层文案
5. 验收：`strings` 扫描、双端联调、控制台功能回归
6. （可选）D 层与 E 层

## 7. 决策点（待确认）

1. 平台优先级：Windows / macOS / Linux / Android / iOS 全做，还是先做 Windows + macOS？
2. 是否保留与官方 RustDesk 生态互通（决定 E 层动不动）？
3. 内部标识符（D 层）是否必须清零？
4. 是否有 Windows 代码签名证书（决定能否真正改善 SmartScreen/杀软判定）？
5. 服务端 `hbbs`/`hbbr` 是否也要改名（当前计划保留，因部署脚本、防火墙、文档都依赖）？

## 8. 执行记录（本轮）

### 已完成

- **共享层（hbb_common 两份副本同步）**：`APP_NAME=RDClient`、`ORG=com.spidercloude`、`RENDEZVOUS_SERVERS=net.spidercloude.com`、`RS_PUB_KEY` 换自建、端口 21126/21127/21128/21129、文档链接改自建、`VER_TYPE_*` 值改 `rd-server`/`rd-client`、版本检查 API 改 `rd.spidercloude.com`
- **客户端**：crate/lib `rd_client`、exe `RDClient.exe`、`.app RDClient.app`、bundle `com.spidercloude.rdclient`、URI `rdclient`、MethodChannel/DBus/Rust 导出符号/`librd_client.*` 引用链全部同步、Windows 服务与注册表名、Android 包名与 Kotlin 目录、图标（png/ico/icns/mipmap/svg）、`src/lang` 1458 处文案 + 6 个英文长键改名并同步调用点、`src` 约 300 处标识符、MSI/flatpak/spec/PKGBUILD/DEBIAN
- **服务端**：包名 `rd_server`、bin `rd_server_id/relay/utils`、systemd/debian/rcd/k8s/docker 同步、console 品牌与 token key、JWT issuer、部署文档重写、迁移脚本

### 验证结果

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 服务端编译 | `cargo check` | 通过（仅 warning） |
| 服务端测试 | `cargo test` | 7 + 5 + 1 passed，0 failed |
| 控制台构建 | `bun install && bun run build` | 通过，3105 modules |
| 客户端编译 | `cargo check --lib` | 通过 |
| 服务端产物 strings | `strings target/debug/rd_server_*` | 仅剩 debug 构建绝对路径（release 不含） |

### 保留项（功能/合规必需）

| 项 | 原因 |
| --- | --- |
| `RustDeskIddDriver Device` | 虚拟显示器驱动的设备接口名，改了功能失效 |
| `RustDeskPrinterDriver` | 远程打印机驱动名，同上 |
| `github.com/rustdesk*`、`rustdesk-org` 依赖源 | 改了下不到源码（libdrmtap、pubspec 的 fork 依赖） |
| `LICENCE`、`Copyright Purslane`、README 归属声明 | AGPL-3.0 要求保留版权与许可 |
| `updater.rs` 的 `repo != "rustdesk"` | 仓库名仍是 rustdesk（fork 未改名） |

### 待办

1. 服务器迁移（`migrate-to-rd-server.sh`，需确认时机）
2. Windows/macOS 实际产物构建与 `verify-strings.sh` 验收（macOS 需 Flutter SDK；Windows 需 Windows 机器或 CI）
3. `hbb_common` fork 并更新两个 `.gitmodules`（当前改动只在本地子模块）
4. 代码签名（Windows OV/EV 或 Azure Trusted Signing；macOS Developer ID + notarization）

### hbb_common 落地方式（已完成）

- fork：`git@github.com:ZavierCloud/hbb_common.git`
- 分支 `rd-client`，commit `f2e726e`：`APP_NAME=RDClient`、`ORG=com.spidercloude`、端口 21126–21129、自建服务器与公钥、`VER_TYPE_*` 值、版本检查 API
- 两个父仓库 `.gitmodules` 已改为该 fork，`submodule sync` + `git add` 完成
- 服务端子模块已 checkout 到同一 commit（`rd-server` 分支跟踪 `origin/rd-client`），目标是与客户端完全同源

### 事故与恢复记录（重要）

期间 pi-lens 的 `clippy --fix` 与 formatter 在 post-write pipeline 自动改写了工作树（287 文件、约 175 个与品牌无关的重构 hunk，如 `&'static str` → `&str`）。

处理过程：
1. 生成 `rustdesk-brand-only.patch` / `rustdesk-server-brand-only.patch`（按 hunk 过滤：仅保留含品牌/端口关键字的改动，丢弃 clippy hunk）
2. `git checkout -- .` 恢复两端工作树
3. `git apply --3way --unidiff-zero <绝对路径补丁>` 重新应用品牌改动
4. 重新生成全部图标（PNG/ICO/ICNS/mipmap/SVG，被 checkout 还原过）
5. 重新编译验证两端

最终状态：品牌改动完整、无 clippy 无关 diff。补丁存档在仓库外目录，可用于复核。

### 同时修复的跨组件一致性（编译不报错但运行会失效）

| 位置 | 问题 | 修复 |
| --- | --- | --- |
| `src/common.rs` vs `libs/portable` | 环境变量 key 不一致（`RD_CLIENT_APPNAME` vs `RUSTDESK_APPNAME`） | 统一 |
| `src/privacy_mode` vs `libs/portable` | `RuntimeBroker_*.exe` 进程名不一致 | 统一为 `RuntimeBroker_rd_client.exe` |
| `libs/portable/bin_reader.rs` | `IDENTIFIER = b"rustdesk"`（8 字节）与 `APP_PREFIX="rd_client"`（9 字节）不一致 | 改为 `b"rd_client"` + `IDENTIFIER_LENGTH=9` |
| `flutter/linux/main.cc` | `dlopen("librustdesk.so")` / `dlsym("rustdesk_core_main")` | 改为 `librd_client.so` / `rd_client_core_main` |
| `.github/workflows` | `liblibrustdesk.so` 双 lib 前缀、`RustDesk.app` 路径 | 修正为 `librd_client.*` / `RDClient.app` |

### 构建环境适配（改名后新增的必需改动）

| 平台 | 问题 | 修复 |
| --- | --- | --- |
| macOS (arm64) | `bridge_generated.*` 被 gitignore，直接 `cargo build --features flutter` 报 `E0583 file not found for module bridge_generated` 与 `IntoIntoDart` 未实现 | 安装 `flutter_rust_bridge_codegen@1.80.1` + `cargo-expand@1.0.95`，生成 Rust/Dart/头文件（步骤见 `WINDOWS-BUILD.md` 3.5 节） |
| macOS (arm64) | Homebrew 的 `aom` 静态库引用 `_vmaf_*`，链接报 Undefined symbols | `libs/scrap/build.rs` 在 homebrew 分支为 `aom` 追加 `-L/opt/homebrew/lib -lvmaf` |
| 全平台 | crate lib 名从 `librustdesk` 改为 `rd_client` 后，build.py 仍执行 `cp liblibrd_client.dylib librd_client.dylib`（产物名已正确） | 该步改为 `true`，跳过重命名 |
| Android/Flutter | `RustDeskClientImpl` 等标识符被替换成带空格的 `RD ClientClientImpl`，`build_runner` 报语法错误 | 正则 `RD Client(?=[A-Za-z0-9_])` → `RdClient`，修正 12 个 Dart/Rust 文件 |
