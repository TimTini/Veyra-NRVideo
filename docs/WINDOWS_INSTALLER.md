# Veyra Windows 安装包

安装向导使用 Veyra 的日落背景、Logo 和图标。默认安装到当前用户的 %LOCALAPPDATA%\Programs\Veyra (NVIDIA) 或 Veyra (AMD)。可以浏览或输入其他本地目录。桌面快捷方式和完成时启动都是可选项。开始菜单包含 Veyra 和卸载入口，Windows「已安装的应用」也会显示对应版本。

安装目录的 Veyra.exe 是固定启动入口。程序及运行组件位于 versions 子目录，安装到当前用户的可写目录。

同一套安装包可在原位置修复安装。此分支不包含应用内更新，安装时不会把旧程序登记为自动回退版本。卸载会移除已安装的程序、快捷方式、版本目录及更新缓存，保留根目录 runtime_local 下的用户配置和 LUT，以及根目录中用户放置的其他文件。versions 和 .veyra-update 是程序管理的目录。虚拟摄像机仍通过播放器内的组件入口进行系统注册和卸载。

## 构建

用 Inno Setup 7.1.1 x64、Python 3.11 及 Pillow。安装器从已审计的单一 GPU stage 制作。程序和启动器来自同一构建，构建脚本核对载荷路径、大小和 SHA-256。编译器许可证随包放在版本目录的 licenses 内。[官方编译器下载及验签](https://jrsoftware.org/inno-setup/downloads/verify)

```powershell
py -3.11 -X utf8 -B -I scripts/package-windows-installer.py --stage <GPU-stage> --build <build> --iscc <ISCC.exe> --output <artifacts> --work-dir <tmp> --log <compile-log> --local-test
```

本地验证使用 --local-test。正式分发使用通过发行审核的 stage 和对应源码。配置正式 Authenticode 时，将签名命令传给 --sign-tool。该命令使用 Inno Setup 的 $f 文件参数，分别签署 Setup 和包内的卸载程序。当前本地测试产物未签名。[Inno Setup SignTool](https://jrsoftware.org/inno-setup/documentation/topic_setup_signtool.htm)

公开发布与现有便携 ZIP 一样，从同一构建分别准备 NVIDIA 和 AMD 成品及相应源码和许可证。
