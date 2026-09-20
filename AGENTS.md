# RustDesk 开发指南

> 用户级规则（沟通、工作流程、编码风格）已上提到工作区根 `../AGENTS.md`。

## 项目结构

### 目录结构
* `src/` Rust 应用
* `src/server/` 音频 / 剪贴板 / 输入 / 视频 / 网络
* `src/platform/` 平台相关代码
* `src/ui/` 旧版 Sciter UI（已废弃）
* `flutter/` 当前 UI
* `libs/hbb_common/` 与服务端共享：rendezvous 协议、socket、`Config` 核心
* `libs/base/`（crate 名 `base`）仅客户端：选项键、message 协议、文件传输、平台代码
* `libs/scrap/` 屏幕捕获
* `libs/enigo/` 输入控制
* `libs/clipboard/` 剪贴板
* `libs/base/src/config/keys.rs` 所有选项的唯一导入路径

### 关键组件
- **远程桌面协议**：在 `src/rendezvous_mediator.rs` 中实现的自定义协议，用于与 rustdesk-server 通信
- **屏幕捕获**：`libs/scrap/` 中的平台相关屏幕捕获
- **输入处理**：`libs/enigo/` 中的跨平台输入模拟
- **音频/视频服务**：`src/server/` 中的实时音视频流
- **文件传输**：`libs/base/src/fs.rs` 中的安全文件传输实现

`hbb_common` 是与服务端共享的 git 子模块，改动它需要一次上游往返。仅客户端的代码请放到 `libs/base`：它是普通的 workspace 成员。`base::config::keys` 重新导出了 `hbb_common` 仍会读取的少数几个键，因此调用方从这一条路径就能拿到完整集合。

### 关联仓库：服务端

服务端不在本仓库，位于与本项目根目录**同级**的 `../rustdesk-server`（远端 `git@github.com:ZavierCloud/rustdesk-server.git`）。
它产出 rendezvous 服务 `hbbs`、relay 服务 `hbbr` 与 `rustdesk-utils`，与本仓库通过 `libs/hbb_common` 共享协议。
注意区分：本仓库的 `src/server/` 是客户端的**被控端服务**，`src/hbbs_http/` 是访问 hbbs 的 HTTP 客户端，二者都不是服务端程序。

### UI 架构
- **旧版 UI**：基于 Sciter（已废弃）— 文件在 `src/ui/`
- **现代 UI**：基于 Flutter — 文件在 `flutter/`
  - 桌面端：`flutter/lib/desktop/`
  - 移动端：`flutter/lib/mobile/`
  - 共享：`flutter/lib/common/` 与 `flutter/lib/models/`

## 构建与工具链

* Rust MSRV 为 1.75（`Cargo.toml` 中的 `rust-version`；CI 固定 `RUST_VERSION: "1.75"`）；macOS 需要 1.81。
  Flutter 固定为 3.24.5（Windows arm64 使用 3.44.x）。`flutter_rust_bridge_codegen` 必须是
  `1.80.1`，以匹配 `=1.80` 的 crate 版本约束。
* `libs/hbb_common` 是 git 子模块。普通 `git clone` 会让它为空，任何构建都会失败：
  `git submodule update --init --recursive`。
* 必须安装 `vcpkg` 并设置 `VCPKG_ROOT`。依赖与固定的 registry baseline 在 `vcpkg.json` 中；
  安装命令：`$VCPKG_ROOT/vcpkg install --x-install-root="$VCPKG_ROOT/installed"`。
  更新 baseline 时还需同步修改 `ci.yml` 与 `flutter-build.yml` 中的 `VCPKG_COMMIT_ID`。
* 始终使用 `--locked` 构建（CI 如此）。大量依赖是 `rustdesk-org` 下的 git fork，其中若干按 `rev`
  而非分支固定；不要放松这些约束。
* `.cargo/config.toml` 设置了 `git-fetch-with-cli = true`（cargo 的 git 依赖走 `git` 命令，因此代理/认证
  需要让 `git` 可用，而不是 libgit2），并为 Windows MSVC 目标启用了静态 CRT。

### 构建入口

* Flutter（当前 UI），在仓库根目录执行：`python3 ./build.py --flutter`，可加 `--hwcodec`、
  `--vram`、`--portable`、`--unix-file-copy-paste`、`--drm`。`build.py` 自身会 `chdir` 进
  `flutter/`，因此在其它目录调用会出错。
* `python3 ./build.py --print-features <flags>` 只打印这些 flag 选中的 cargo feature 列表而不构建 —
  用它替代硬编码 `--features`。
* 快速 Flutter 开发循环：`flutter/run.sh`（代码生成 + `cargo build --locked --features flutter` +
  `flutter run`）。
* 旧版 Sciter UI（已废弃）：`cargo run`；需要把 `sciter.dll` / `libsciter-gtk.so` /
  `libsciter.dylib` 放到 `target/debug/` 旁边。

### Flutter Rust 桥接代码生成

`src/flutter_ffi.rs` 是唯一事实来源；生成产物已入库。修改它之后，必须重新生成并提交，否则 Dart 与
Rust 两侧会静默漂移：

```sh
flutter_rust_bridge_codegen --rust-input ./src/flutter_ffi.rs \
  --dart-output ./flutter/lib/generated_bridge.dart \
  --c-output ./flutter/macos/Runner/bridge_generated.h
cp ./flutter/macos/Runner/bridge_generated.h ./flutter/ios/Runner/bridge_generated.h
```

生成物：`src/bridge_generated.rs`、`src/bridge_generated.io.rs`、`flutter/lib/generated_bridge.dart`、
`flutter/lib/generated_bridge.freezed.dart`，以及两个头文件。

### 测试

* Rust：`cargo test --locked --workspace --no-fail-fast -- --skip test_get_cursor_pos --skip test_get_key_state`
  （这两个用例会真实驱动键盘/光标状态，CI 中跳过）。没有根级 `tests/` 目录；测试是内联的
  `#[cfg(test)]` 模块。
* Flutter，在 `flutter/` 下：`flutter test --timeout 60s test/<file>.dart`。CI 只运行
  `test/cursor_size_test.dart`。
* CI 不运行 `cargo fmt --check` 或 `flutter analyze`（已禁用/缺失），因此没有可依赖的 lint 门禁 —
  请手动保持 diff 干净。

## Rust 规则

* 生产代码中避免 `unwrap()` / `expect()`。
* 例外：

  * 测试；
  * 锁获取失败意味着中毒（poisoning）而非正常控制流的场景。
* 其余情况优先用 `Result` + `?` 或显式处理。
* 不要静默忽略错误。
* 避免不必要的 `.clone()`。
* 实用时优先借用。
* 除非必要，不新增依赖。
* 保持代码简单、符合惯用法。

## Tokio 规则

* 假定 Tokio runtime 已存在。
* 绝不创建嵌套 runtime。
* 绝不在 Tokio / async 代码中调用 `Runtime::block_on()`。
* 不要把 runtime 的创建藏在辅助函数或库里。
* 不要跨 `.await` 持有锁。
* 优先使用 `.await`、`tokio::spawn`、channel。
* 阻塞型工作使用 `spawn_blocking` 或专用线程。
* 不要在 async 代码中使用 `std::thread::sleep()`。

## 编辑规范

* 只改必需的部分。
* 优先最小有效 diff。
* 不重构无关代码。
* 不做纯格式化改动。
* 命名/风格与邻近代码保持一致。

### 导入

* 每个 crate 一条 `use`。同一 crate 的所有内容放进一个花括号块，而不是每项一条语句：

  ```rust
  // no
  use base::fs;
  use base::message_proto::*;

  // yes
  use base::{fs, message_proto::*};
  ```

* 唯一需要拆分的理由是 `#[cfg(...)]` 不适用于整块 — 属性只作用于单个条目，因此不同门控的导入必须
  单独成句。`pub use` 重导出同样不能并入普通 `use`。

  ```rust
  #[cfg(not(feature = "flutter"))]
  use base::fs;
  use base::message_proto::*;
  ```

* 当某条现有 `use` 因部分条目移到别的 crate 而拆分时，把两侧分别并入各自 crate 已有的块，而不是留下
  第二条语句。

### 注释

* 除非用于说明不明显的原因、约束或变通，否则不加注释。
* 绝不复述代码在做什么；优先让代码更清晰。
* 代码本身已自解释时，不加注释。

### 尽量少侵入

* 优先纯增量改动：在现有代码周围叠加新的（`#[cfg]` 门控的）代码块或新函数，而不是重构它。修复的理想 diff 只加行，不改不删。
* 不要为了给自己的新代码让路而抽取或改造现有代码；寻找能让现有行保持不动的手段（例如隐藏/显示已有对象，而不是把它的构造重构进一个用于重建的辅助函数）。
* 宁可接受少量重复，也不要重构。新函数重复现有函数的几行，比改造原函数让两者共用更好。
* 把新逻辑放在它所属模块的自包含函数里（平台相关逻辑放 `src/platform/`，`use` 写在函数体内以避免改动共享导入块）。共享文件（`src/tray.rs`、`src/core_main.rs`、`src/server/connection.rs` 等）中的调用点应当是单行薄钩子。

### 改动共享代码前先做范围检查

* 在修改共享 trait、共享 struct 或广泛使用函数的签名前，先判断该 bug/功能是否只与某一条路径相关。若是，就把改动限制在该路径内，除非做不到，并在 PR 中说明原因。
* 若某个无关调用方仅仅为了满足你改过的签名而需要 `Default::default()`、`None` 或其它占位值，说明 diff 过宽：停下来重新设计。
* 修复的预期形态是：在功能自己的模块里加一个新函数，至多在它需要的共享代码中加一个字段或一个薄钩子。功能专属状态应放在该功能已有状态的旁边，而不是放进一个所有调用方都得重新学习的新抽象。

### 强制回归面检查

在认为任何实现完成之前，对最终 diff 做一次最小化检查。

* 检查每个被修改的现有文件和每条被修改的现有代码路径。每一处都必须是所请求改动严格必需的。回退那些仅仅属于清理、重构、一致性改进或修复既有问题的改动。
* 对于新功能，在功能关闭或不支持时，尽可能保留原有实现路径。`feature off` 应运行旧代码，而不是一个重写过的等价物。
* 不要仅仅为了与新功能共享代码，就把现有行为改道经过新抽象。宁可新增一个并行函数或少量重复，也不要改动一条已被验证的现有路径。
* 把新实现逻辑放在新的或功能专属的模块里。对共享/核心文件的改动通常应是薄钩子、能力检查或协议管道。
* 不要在同一个 PR 里修复无关的既有 bug。除非它直接阻塞所请求工作的正确性或安全性，否则拆成单独的改动。
* 更新子模块时，检查确切的 commit 范围，确保没有把无关改动带进父仓库 PR。
* 定稿前，明确报告回归面：列出行为发生变化的现有文件与现有运行时路径，并解释每处改动为何不可避免。
* 评审时，即使测试通过、重写后的行为看起来等价，也把无必要修改的旧路径视为一条评审问题。

## 评审 PR

* 只评审 diff 引入的内容。报告问题前先用 `gh pr diff` 确认归属 — 如果问题行是未改动的上下文，那它是既有问题，不属于本 PR。
* 把既有问题列在末尾的单独小节，或者略去那些不致命的。绝不要把它们混进作者必须修复的问题里。
* 重新评审前，先读作者的回复评论。不要重复提出他们已以范围为由拒绝的事项。
* 准确陈述问题的后果：区分「值会丢失」与「捷径无效但值仍会被保存」。

## 本地化（`src/lang/*.rs`）

每个文件是一个 `HashMap<key, translation>`。布局：

* `template.rs` 是所有键的主列表。翻译工作中**绝不修改它**。
* `en.rs` 只保存英文显示文本与键本身不同的键。
* 其它每个文件（`de.rs`、`fr.rs` 等）都带完整键集；未翻译的条目的值为空：`("key", "")`。
* `it.rs` 由它的译者手工维护。绝不填充或修改它的条目；新增键时以 `""` 追加，把翻译留给维护者。

### 查找某个键的英文原文

填充空条目时，用以下规则确定源英文文本：

* 若 `key` 在 `en.rs` 中**存在且值非空**，该值就是源文本（去 `en.rs` 里查）。
* 否则**键字符串本身就是源文本**（键已是纯英文）。

然后把该源文本翻译成文件的目标语言（根据文件已有的非空条目/文件名推断语言）。

### 翻译卫生

* 只填充空值。绝不修改键，也绝不触碰已有的非空翻译。
* 与源文本完全一致地保留占位符（`{}`）和转义序列（`\n`、`\"`）。
* 不翻译品牌或技术名词：`RustDesk`、`Socks5`、`TLS`、`UAC`、`Wayland`、`X11`、`TCP`、`UDP`、`2FA`、`RDP`、`D3D` 等。
* 逐字复制 URL 值（如 `doc_*` 键）自 `en.rs`。

### 新增键（功能开发）

* 新的英文文本键使用句首大写（sentence case），而非词首大写（Title Case）：`Use ID whitelisting`，**不是** `Use ID Whitelisting`。缩写（ID、IP、2FA…）保持大写。历史遗留的 Title-Case 键（如 `Use IP Whitelisting`）保持原样 — 不要重命名。
* 由于键本身就是英文显示文本，句首大写的键通常**不需要** `en.rs` 条目；仅当显示文本必须与键不同时（如 `*_tip` 键）才添加。
* 把每个新键追加到 `template.rs`（值为 `""`）以及每个 `src/lang/*.rs` 文件（已翻译，或不确定时用 `""`；`it.rs` 一律 `""`），追加在列表末尾。
