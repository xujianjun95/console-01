# Console 01

Console 01 是一个运行在 Mac 本机的局域网中控台。手机或平板连到同一个 Wi-Fi 后，可以通过网页控制 Mac 的音量、亮度、音乐播放、锁屏/睡眠，并查看蓝牙设备电量。

界面风格参考 Braun 设备：奶白塑料机身、LCD 液晶屏、实体按键和低调橙色点缀。

## 功能

- 音量和亮度纵向推子。
- LCD 风格时钟和日期显示。
- 快捷操作：锁屏、睡眠、静音、Launchpad、Finder、夜间模式。
- Apple Music / Spotify 播放控制，支持当前曲目信息和封面。
- 蓝牙设备电量显示。
- PWA 配置，可添加到手机主屏幕。
- 夜间模式：压暗机身、LCD 和橙色点缀，并带柔和渐变动画。

## 运行要求

- macOS。
- Python 3。
- 可选：`brightness` 命令行工具，用于直接读取和设置屏幕亮度。
- 部分操作需要给终端或启动器授予“辅助功能”权限，例如亮度按键兜底、Launchpad 快捷键等。

服务端只使用 Python 标准库，不需要安装额外 Python 依赖。

## 启动

在项目目录运行：

```bash
python3 server.py
```

服务默认监听 `8765` 端口：

```text
http://<你的 Mac 局域网 IP>:8765/
```

这台机器当前常用地址是：

```text
http://192.168.3.11:8765/
```

手机需要和 Mac 在同一个 Wi-Fi 或局域网内。

## 夜间模式

右下角快捷键是 `Night`，它替代了原来的 `Search` 按钮。

- 点击 `Night` 可在白天模式和夜间模式之间切换。
- 当前主题会保存到 `localStorage`，刷新页面后保持。
- 切换时有渐变动画，像实体设备慢慢降亮，而不是瞬间变暗。
- 中间的 `I/O` 滑动开关仍然只负责中控台的电源/待机状态，不和主题混用。

## 实际运行目录

这个项目目录是源码目录，但本机常驻服务有时会从下面的运行目录启动：

```text
/Users/xujianjun/Library/Application Support/pmtools-console
```

如果你改了源码，但手机页面没有变化，通常是因为正在运行的服务读的是这个运行目录里的文件。可以选择：

- 把更新后的 `index.html` 和 `server.py` 同步到运行目录。
- 或者停止旧服务，直接从当前仓库目录重新启动 `python3 server.py`。

## HTTP 接口

- `GET /` 或 `GET /index.html`：返回中控台页面。
- `GET /api/status`：返回音量、亮度、静音状态、音乐状态和封面来源。
- `GET /api/bluetooth`：返回已连接蓝牙设备的电量信息。
- `GET /api/cover`：返回 Apple Music 当前封面。
- `POST /api/volume`：设置输出音量。
- `POST /api/mute`：设置静音状态。
- `POST /api/brightness`：设置或微调屏幕亮度。
- `POST /api/music`：发送播放/暂停、上一首、下一首。
- `POST /api/system`：发送系统操作，例如锁屏、睡眠、打开 Finder。
- `POST /api/claude`：给 Claude Code 权限菜单发送快捷键选择。

路由支持查询参数，所以 `/?v=night1` 这类用于破缓存的地址也会正常返回页面，不会再返回 `not found`。

## 常见问题

如果手机仍然显示旧界面：

1. 先刷新页面，或打开 `/?v=night1` 这类破缓存地址。
2. 如果是从手机主屏幕 PWA 图标进入，重大 UI 更新后可以删除旧图标再重新添加。
3. 确认当前服务实际读取的是源码目录还是运行目录。
4. 查看当前监听 `8765` 的进程：

```bash
lsof -nP -iTCP:8765 -sTCP:LISTEN
```

