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

- 当检测到桌面版网易云音乐（通过窗口标题或进程名匹配）正在播放音乐时，刘海会向两侧展开并显示左侧歌名、右侧歌词（若检测不到歌词则显示“纯音乐”）；文本过长会以滚动字幕形式显示。提示期间点击刘海会尝试激活网易云音乐窗口。

注意：音乐与歌词检测使用窗口标题与进程名的启发式轮询（每秒），并不能保证在所有网易云音乐版本或安装路径下都能获得歌词或精确信息；如果需要更可靠的歌词和播放状态获取，请考虑集成官方 API 或使用 Windows 媒体会话接口（需额外依赖）。

注意：微信新消息检测采用窗口标题变化的启发式轮询（每秒），需在 Windows 上安装 `pywin32`（已列入 `requirements.txt`）。此方法对不同版本的微信行为可能有差异；如需更稳定的集成，需要使用微信的官方 API 或更复杂的系统钩子。
退出方式：
- 在普通模式下可按 `Esc` 或 `Ctrl+Q` 关闭窗口；或在终端按 `Ctrl+C`。
- 在点击穿透模式下，窗口不拦截鼠标，按 `Ctrl+C` 终止运行或从任务管理器结束进程。

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

