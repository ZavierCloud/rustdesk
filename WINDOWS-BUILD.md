# Windows 构建环境（RD Client）

目标：在 Windows 上产出 `RDClient.exe`、`librd_client.dll`、`rd_client-portable-packer.exe` 与 MSI 安装包。

## 1. 必装工具

| 工具 | 版本/说明 | 验证命令 |
| --- | --- | --- |
| Visual Studio 2022 Build Tools | 勾选「使用 C++ 的桌面开发」+「Windows 11 SDK (10.0.22621+)」 | `cl` 有输出 |
| Rust (rustup) | stable-msvc，`rustup default stable-x86_64-pc-windows-msvc` | `rustc -V`、`cargo -V` |
| LLVM | 18+（`rust-bindgen` 需要 `libclang.dll`） | `clang --version` |
| Flutter SDK | **3.24.5**（与 CI 一致；Windows arm64 才是 3.44.9），`flutter config --enable-windows-desktop` | `flutter doctor` 无 Windows 错误 |
| vcpkg | 建议 `C:\vcpkg`，设置 `VCPKG_ROOT` 与 `VCPKG_DEFAULT_TRIPLET=x64-windows-static` | `vcpkg version` |
| Perl | Strawberry Perl（OpenSSL 构建需要） | `perl -v` |
| CMake / Ninja | VS 自带也可 | `cmake --version` |
| Python 3 | 3.10+，供 `build.py` / `res/msi/preprocess.py` | `python --version` |
| Git | 用于子模块与依赖 | `git --version` |

## 2. vcpkg 依赖（关键，缺一必失败）

```powershell
vcpkg install libvpx:x64-windows-static libyuv:x64-windows-static opus:x64-windows-static aom:x64-windows-static
vcpkg integrate install
```

`libs/scrap/build.rs` 在 Windows 上通过 `VCPKG_ROOT` 找静态库；若报 `Could not find package`，检查 triplet 是否为 `x64-windows-static` 且 `VCPKG_ROOT` 已设为**系统级**环境变量。

## 3. 拉代码与子模块

```powershell
git clone <你的 rustdesk fork> rd_client
cd rd_client
git submodule update --init --recursive   # libs/hbb_common 指向 ZavierCloud/hbb_common 的 rd-client 分支
```

确认子模块：

```powershell
git submodule status    # 应为 f2e726e... libs/hbb_common
```

## 3.5 生成 flutter_rust_bridge 代码（Windows 首次构建必做）

`src/bridge_generated.rs`、`src/bridge_generated.io.rs`、`flutter\lib\generated_bridge.dart`、`flutter\macos\Runner\bridge_generated.h` 都是**被 gitignore 的生成产物**，仓库里没有。直接 `cargo build --features flutter` 会报：

```
error[E0583]: file not found for module `bridge_generated`
error[E0277]: the trait bound `EventToUI: IntoIntoDart<_>` is not satisfied
```

生成步骤（与 CI 的 `generate-bridge` job 一致）：

```powershell
cargo install cargo-expand --version 1.0.95 --locked
cargo install flutter_rust_bridge_codegen --version 1.80.1 --features uuid --locked

cd flutter
flutter pub get
cd ..

flutter_rust_bridge_codegen --rust-input ./src/flutter_ffi.rs `
  --dart-output ./flutter/lib/generated_bridge.dart `
  --c-output ./flutter/macos/Runner/bridge_generated.h

copy flutter\macos\Runner\bridge_generated.h flutter\ios\Runner\bridge_generated.h
```

注意：**版本必须匹配**——macOS / Windows x64 用 **3.24.5**，Windows arm64 用 **3.44.9**。用 3.47 等更新版本会在 Dart 编译期报 `DialogTheme` 与 `DialogThemeData` 不兼容、`extended_text` 缺 `_SelectableFragment` 实现等错误（本项目源码未提交 3.44 的 API 适配，CI 用 `apply_flutter_3.44_source_patches.sh` 在 arm64 job 里临时打补丁）。

## 4. 构建

```powershell
# 仅 Rust 核心（快速自检）
cargo check --lib

# 完整 Flutter + Windows 产物
python build.py --flutter
```

产物位置：

| 文件 | 路径 |
| --- | --- |
| 主程序 | `target\release\RDClient.exe` |
| 核心库 | `target\release\librd_client.dll` |
| 便携版打包器 | `target\release\rd_client-portable-packer.exe` |
| Flutter 构建目录 | `flutter\build\windows\x64\runner\Release\` |

## 5. MSI 安装包

```powershell
cd res\msi
python preprocess.py -d ..\..\target\release --app-name RDClient --manufacturer ZavierCloud
# 之后用 WiX 工程（Package\*.wxs）编译，或走上游 CI 的 MSI 步骤
```

要点：`--app-name` 必须与 exe 名一致（`RDClient`），否则 `preprocess.py` 找不到 `RDClient.exe` 会把它当普通文件插入导致 WiX 报重复键。

## 6. 验收（产物静态特征）

```powershell
# PowerShell 等价于 strings | grep
Select-String -Path target\release\RDClient.exe -Pattern "rustdesk" -SimpleMatch -Encoding Byte -AllMatches
# 或安装 Sysinternals strings:
strings64.exe target\release\RDClient.exe | Select-String -Pattern "rustdesk"
```

期望：**0 命中**。白名单项（改了会坏功能）：`RustDeskIddDriver Device`、`RustDeskPrinterDriver`、`github.com/rustdesk*` 依赖源、`Copyright Purslane`（AGPL 归属）。

## 7. 常见坑

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `Could not find package in ...libyuv` | vcpkg 未装或 triplet 不对 | 见第 2 节 |
| `LINK : fatal error LNK1181: 无法打开输入文件 libvpx.lib` | 用了动态 triplet | 必须 `x64-windows-static` |
| `flutter build windows` 找不到 `librd_client.dll` | CMake 未拷贝新命名的库 | 检查 `flutter\windows\CMakeLists.txt` 的 `RD_CLIENT_LIB` 路径 |
| 启动报 `Failed to load librd_client.dll` | dll 与 exe 不同目录 | 把 dll 放 exe 同目录 |
| 安装后服务起不来 | 服务名/路径不一致 | 服务名应为 `RDClient`（`sc query RDClient`） |
| 杀软/Defender 拦截 | 无代码签名 | 见第 8 节 |

## 8. 签名（决定能否过 SmartScreen）

- **OV/EV 代码签名证书**：DigiCert / Sectigo / GlobalSign，约 3000–6000 元/年；EV 需硬件 token 或云签名
- **Azure Trusted Signing**：按月订阅，门槛低于 EV，适合个人/小团队
- 签名对象：`RDClient.exe`、`librd_client.dll`、`rd_client-portable-packer.exe`、MSI
- 命令示例：`signtool sign /fd SHA256 /tr <timestamp-url> /td SHA256 /a <file>`

> 改名只消除静态特征。**没有签名，SmartScreen 与多数杀软仍会拦截**；远控类软件还会被行为检测命中，必要时需向厂商提交白名单。


---

## 9. 在新设备 clone 后接续（重要）

```bash
git clone git@github.com:ZavierCloud/rustdesk.git rd_client
cd rd_client
git submodule update --init --recursive     # 必须，libs/hbb_common 指向 ZavierCloud/hbb_common 的 rd-client 分支
git submodule status                        # 期望：f2e726e... libs/hbb_common
```

仓库里**没有**以下生成物（被 .gitignore 忽略），首次构建必须自己生成：

- `src/bridge_generated.rs` / `src/bridge_generated.io.rs` / `flutter/lib/generated_bridge.dart`
  / `flutter/lib/generated_bridge.freezed.dart` / `flutter/macos/Runner/bridge_generated.h`
- `flutter/lib/*.freezed.dart`（build_runner 产物）

生成步骤见本文 3.5 节，必须**先做**，否则 `cargo build --features flutter` 直接报 E0583。

### 当前改造状态（截至本次提交）

| 项 | 状态 |
| --- | --- |
| 品牌/产物改名（rd_client、RDClient.exe、com.spidercloude.rdclient、端口 +10） | ✅ 已提交 |
| 内置服务器 `net.spidercloude.com` + 公钥 `C8Rv...` | ✅ 已提交（hbb_common 子模块） |
| 图标（png/ico/icns/mipmap/svg） | ✅ 已提交 |
| macOS 产物构建与启动验证 | ✅ `RDClient.app` 62MB，ad-hoc 签名后可运行 |
| **Windows 产物** | ❌ 未构建（需要 Windows 环境，见本文 1–7 节） |
| macOS 正式签名/公证 | ❌ 未做（`codesign -dv` 显示 adhoc） |
| Windows 代码签名 | ❌ 未做（决定能否过 SmartScreen） |

### 构建前必须核对的三处一致性

1. `flutter/macos/Runner/Configs/AppInfo.xcconfig` 里有 `#include "../../Pods/..."`（CocoaPods 注入），`pod install` 后再构建
2. `flutter/macos/Runner.xcodeproj/project.pbxproj` 的 `OTHER_LDFLAGS` 必须含 `"$(inherited)"`，否则插件 framework 不参与链接
3. `MainMenu.xib` 的 `customModule` 必须是 `RDClient`（与 `PRODUCT_NAME` 一致），否则启动即崩

### 已知坑清单

| # | 现象 | 原因/修复 |
| --- | --- | --- |
| 1 | `E0583 file not found for module bridge_generated` | 未生成 bridge，见 3.5 节 |
| 2 | `IntoIntoDart` 未实现 | 同上（bridge 缺失的连带错误） |
| 3 | `Undefined symbols: _vmaf_*` | Homebrew `aom` 需要额外 `-lvmaf`，已修在 `libs/scrap/build.rs` |
| 4 | `cp liblibrd_client.dylib` 失败 | 已改成 `true`（产物名本身正确） |
| 5 | Dart 报 `DialogTheme`/`DialogThemeData`、`_SelectableFragment` 缺实现 | Flutter 版本过新，降到 **3.24.5** |
| 6 | Swift `rustdesk_core_main` 未定义 | 已改 `rd_client_core_main`，MethodChannel 改 `com.spidercloude.rdclient/host` |
| 7 | App 启动即崩（AppDelegate 无法实例化） | `MainMenu.xib` 的 `customModule` 已改 `RDClient` |
| 8 | `Undefined symbols: FileSelectorPlugin` 等 | Pods xcconfig 未被 include + `OTHER_LDFLAGS` 缺 `$(inherited)` |
| 9 | 启动报 `different Team IDs` | 未签名 app 加载已签名 framework，需 `codesign --force --deep --sign -`（正式发布用 Developer ID） |

### 验收命令

```powershell
# Windows
strings64.exe target\release\RDClient.exe | Select-String "rustdesk"
```

```bash
# macOS
strings -a RDClient.app/Contents/MacOS/RDClient | grep -ci rustdesk
strings -a RDClient.app/Contents/Frameworks/librd_client.dylib | grep -ci rustdesk
```

期望：`RDClient` 与 `service` 为 0；`librd_client.dylib` 仅剩 7 处白名单命中（`https://rustdesk.com/docs/...` 3 条、编译期路径 1 条、`rustdesk_`/`_rustdesk_` 符号 2 条）。
