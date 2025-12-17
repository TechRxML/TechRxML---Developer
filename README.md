```markdown
# Windows 顶部刘海覆盖

这是一个简单的 Python 脚本，使用 PyQt5 在 Windows 屏幕顶部居中绘制一个模拟 MacBook 新系列的“刘海”覆盖层。

主要功能：
- 自动检测主显示器分辨率并将刘海居中显示
- 固定刘海尺寸：`420x36`（3072x1920分辨率下已确认并要求保留此尺寸）
- 顶部为平直，底部带圆角，保持处于最上方
- 鼠标移入时带有平滑的微放大动画（enter/leave 动画）
- 可选“点击穿透”模式（`--clickthrough`），使覆盖层不拦截鼠标事件（仅 Windows 有效）

依赖：
```
PyQt5>=5.15.0
```

安装（在 PowerShell 中）：
```powershell
python -m pip install -r requirements.txt
```

运行：
```powershell
# 普通模式（窗口可接收鼠标/键盘，用 Esc 关闭）
python windwoslh.py

# 点击穿透模式（覆盖不会阻止鼠标事件）
python windwoslh.py --clickthrough
```

打包为 EXE
-----

仓库提供了一个简单的 PowerShell 打包脚本 `build_exe.ps1`，它会为打包创建一个局部虚拟环境并调用 PyInstaller：

在项目根目录运行：

```powershell
.\build_exe.ps1
```

脚本会在 `.venv_build` 中创建虚拟环境、安装 `pyinstaller`，并使用 `pyinstaller --onefile --windowed --name windwoslh windwoslh.py` 构建单文件 EXE。打包结果位于 `dist\windwoslh.exe`。

注意事项：
- 点击穿透仅在 Windows 平台可用，使用了窗口扩展样式。
- README 之前包含的微信/网易云音乐及三击快捷功能已被移除，当前版本仅保留视觉与交互（悬停放大）功能。

```
# Windows 顶部刘海覆盖

这是一个简单的 Python 脚本，使用 PyQt5 在 Windows 屏幕顶部居中绘制一个模拟 MacBook 新系列的“刘海”覆盖层。

主要功能：
- 自动检测主显示器分辨率并计算居中刘海尺寸
- 透明背景、无边框、始终置顶
- 可选“点击穿透”模式（`--clickthrough`），使覆盖层不拦截鼠标事件

依赖：
```
PyQt5>=5.15.0
```

安装（在 PowerShell 中）：
```powershell
python -m pip install -r requirements.txt
```

运行：
```powershell
# 普通模式（窗口可接收鼠标/键盘，用 Esc 关闭）
python windwoslh.py

# 点击穿透模式（覆盖不会阻止鼠标事件）
python windwoslh.py --clickthrough

注意：
- 点击穿透利用了 Windows 窗口扩展样式，默认仅在 Windows 平台上有效。
- 若需更复杂的样式（阴影、圆角细节、系统托盘控制或全屏刘海），我可以继续扩展。

打包为 EXE
-----

仓库提供了一个简单的 PowerShell 打包脚本 `build_exe.ps1`，它会为打包创建一个局部虚拟环境并调用 PyInstaller：

在项目根目录（含 `windwoslh.py`）运行：

```powershell
.\build_exe.ps1
```

脚本做的事情：
- 在 `.venv_build` 中创建/复用虚拟环境
- 安装 `pyinstaller`
- 使用 `pyinstaller --onefile --windowed --name windwoslh windwoslh.py` 构建单文件 EXE

也可以手动运行（已安装 pyinstaller 时）：

```powershell
python -m pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name windwoslh windwoslh.py
```

注意事项：
- PyInstaller 对 PyQt5 通常能自动打包 Qt 平台插件，但如果运行时出现诸如找不到 Qt 平台插件 ("xcb" / "windows") 的错误，你可能需要把插件目录显式包含到打包里（使用 `--add-data`）。
- 打包结果位于 `dist\windwoslh.exe`。


