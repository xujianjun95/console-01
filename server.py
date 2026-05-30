#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MacBook 中控台 —— 局域网小服务
手机访问本机网页，控制音量 / 亮度 / 音乐 / 锁屏睡眠。
只用 Python 标准库，无需额外安装。
"""

import json
import os
import re
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8765
HERE = os.path.dirname(os.path.abspath(__file__))


def run(args):
    """执行命令，返回 (成功?, 输出文本)。"""
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=5)
        ok = out.returncode == 0
        return ok, (out.stdout if ok else out.stderr).strip()
    except Exception as e:
        return False, str(e)


def osa(script):
    """跑一段 AppleScript。"""
    return run(["osascript", "-e", script])


# ---------- 音量 ----------
def get_volume():
    ok, v = osa("output volume of (get volume settings)")
    return int(v) if ok and v.isdigit() else None


def get_muted():
    ok, v = osa("output muted of (get volume settings)")
    return v == "true" if ok else None


def set_volume(value):
    value = max(0, min(100, int(value)))
    return osa(f"set volume output volume {value}")[0]


def set_muted(muted):
    flag = "true" if muted else "false"
    return osa(f"set volume output muted {flag}")[0]


# ---------- 亮度 ----------
def _read_brightness_raw():
    """跑 brightness -l，解析出 0.0-1.0 的亮度值；失败返回 None。"""
    ok, out = run(["brightness", "-l"])
    if not ok:
        return None
    for line in out.splitlines():
        # 正常: "display 0: brightness 0.500000"；失败行解析不出数字
        if "display" in line and "brightness" in line:
            try:
                return float(line.strip().split()[-1])
            except Exception:
                pass
    return None


def probe_brightness():
    """启动时探测一次：brightness 工具是否真能读到亮度。
    Apple Silicon 新机型常因私有接口变动而失灵，此时退回按键方案。"""
    if not run(["which", "brightness"])[0]:
        return False
    return _read_brightness_raw() is not None


BRIGHTNESS_OK = probe_brightness()


def get_brightness():
    if not BRIGHTNESS_OK:
        return None
    v = _read_brightness_raw()
    return round(v * 100) if v is not None else None


def set_brightness(value):
    if not BRIGHTNESS_OK:
        return False
    value = max(0, min(100, int(value))) / 100.0
    return run(["brightness", f"{value:.2f}"])[0]


def nudge_brightness(up):
    """按键方案：模拟键盘亮度键，逐级增减（需辅助功能权限）。"""
    key = 144 if up else 145  # 144=调亮 145=调暗
    return osa(f'tell application "System Events" to key code {key}')[0]


_bri_accum = 0.0


def adjust_brightness_delta(delta_pct):
    """滑动条相对调节：把百分比变化换算成亮度键次数（工具失灵时用）。
    系统亮度约 16 级，余数累计避免误差。"""
    global _bri_accum
    _bri_accum += float(delta_pct) / 100.0 * 16.0
    steps = int(_bri_accum)
    _bri_accum -= steps
    for _ in range(min(abs(steps), 16)):
        nudge_brightness(steps > 0)
    return True


# ---------- 音乐 ----------
_app_cache = {"name": None, "ts": 0.0}


def _app_running(name):
    """快速判断 App 是否运行（不会启动它，比列进程快得多）。"""
    ok, out = osa(f'application "{name}" is running')
    return ok and out == "true"


def music_app():
    """优先 Spotify（在运行就用它），否则 Music。结果缓存 8 秒，避免每次按键都重新探测。"""
    now = time.time()
    if _app_cache["name"] and now - _app_cache["ts"] < 8:
        return _app_cache["name"]
    name = "Spotify" if _app_running("Spotify") else "Music"
    _app_cache["name"] = name
    _app_cache["ts"] = now
    return name


def music_control(action):
    app = music_app()
    cmd = {
        "playpause": "playpause",
        "next": "next track",
        "prev": "previous track",
    }.get(action)
    if not cmd:
        return False
    return osa(f'tell application "{app}" to {cmd}')[0]


COVER_PATH = "/tmp/mac-console-cover.dat"


def get_music():
    """聚合当前音乐信息：曲名、是否播放中、封面来源。只判断一次播放器。"""
    app = music_app()
    info = {"track": "—", "playing": False, "cover": None}
    script = (
        f'tell application "{app}"\n'
        '  if it is running then\n'
        '    try\n'
        '      return (player state as text) & linefeed & (name of current track) & " — " & (artist of current track)\n'
        '    end try\n'
        '  end if\n'
        '  return "off"\n'
        'end tell'
    )
    ok, out = osa(script)
    if ok and out and out != "off":
        parts = out.split("\n", 1)
        info["playing"] = parts[0].strip() == "playing"
        if len(parts) > 1 and parts[1].strip():
            info["track"] = parts[1].strip()
        if app == "Spotify":
            ok2, url = osa('tell application "Spotify" to artwork url of current track')
            info["cover"] = url if (ok2 and url.startswith("http")) else None
        else:
            info["cover"] = "/api/cover"
    return info


def export_music_cover():
    """导出 Apple Music 当前封面，返回 (图片字节, mime) 或 None。"""
    script = (
        'tell application "Music"\n'
        '  if it is running then\n'
        '    try\n'
        '      set d to data of artwork 1 of current track\n'
        f'      set p to (POSIX file "{COVER_PATH}")\n'
        '      set f to open for access p with write permission\n'
        '      set eof f to 0\n'
        '      write d to f\n'
        '      close access f\n'
        '      return "ok"\n'
        '    end try\n'
        '  end if\n'
        '  return "no"\n'
        'end tell'
    )
    ok, out = osa(script)
    if not ok or out != "ok":
        return None
    try:
        with open(COVER_PATH, "rb") as fp:
            raw = fp.read()
    except Exception:
        return None
    # AppleScript 的 data 会带类型头，找到真正的图片起点再返回
    for magic, mime in ((b"\xff\xd8\xff", "image/jpeg"), (b"\x89PNG", "image/png")):
        i = raw.find(magic)
        if i != -1:
            return raw[i:], mime
    return None


# ---------- 系统监控 ----------
_CPU_CORES = max(1, int(run(["sysctl", "-n", "hw.logicalcpu"])[1].strip() or 1))
_net_prev = {"ts": 0.0, "rx": 0, "tx": 0, "rx_speed": 0.0, "tx_speed": 0.0}


def get_cpu():
    ok, out = run(["ps", "-A", "-o", "%cpu"])
    if not ok:
        return None
    try:
        total = sum(float(x) for x in out.strip().split("\n")[1:] if x.strip())
        return min(round(total / _CPU_CORES), 100)
    except Exception:
        return None


def get_memory():
    ok, out = run(["vm_stat"])
    if not ok:
        return None
    try:
        stats = {m.group(1).strip(): int(m.group(2))
                 for m in re.finditer(r'"?([^":\n]+?)"?\s*:\s*(\d+)', out)}
        ok2, mem_str = run(["sysctl", "-n", "hw.memsize"])
        total_pages = int(mem_str.strip()) // 4096
        used = (stats.get("Pages active", 0) +
                stats.get("Pages wired down", 0) +
                stats.get("Pages occupied by compressor", 0))
        return min(round(used / total_pages * 100), 100) if total_pages else None
    except Exception:
        return None


def _net_bytes():
    ok, out = run(["netstat", "-ib"])
    if not ok:
        return 0, 0
    rx = tx = 0
    seen: set = set()
    for line in out.strip().split("\n")[1:]:
        parts = line.split()
        if len(parts) < 10:
            continue
        name = parts[0]
        if name in seen or name.startswith("lo"):
            continue
        seen.add(name)
        try:
            rx += int(parts[6])
            tx += int(parts[9])
        except (ValueError, IndexError):
            pass
    return rx, tx


def _fmt_speed(bps):
    if bps < 1024:
        return f"{int(bps)}B"
    if bps < 1024 * 1024:
        return f"{bps/1024:.0f}KB"
    return f"{bps/1024/1024:.1f}MB"


def get_net_speed():
    global _net_prev
    now = time.time()
    rx, tx = _net_bytes()
    dt = now - _net_prev["ts"]
    if dt > 0.5 and _net_prev["ts"] > 0:
        _net_prev["rx_speed"] = max(0, rx - _net_prev["rx"]) / dt
        _net_prev["tx_speed"] = max(0, tx - _net_prev["tx"]) / dt
    _net_prev.update({"ts": now, "rx": rx, "tx": tx})
    return _fmt_speed(_net_prev["rx_speed"]), _fmt_speed(_net_prev["tx_speed"])


def get_stats():
    rx_s, tx_s = get_net_speed()
    return {
        "cpu": get_cpu(),
        "mem": get_memory(),
        "net_rx": rx_s,
        "net_tx": tx_s,
    }


# ---------- 系统 ----------
def lock_screen():
    """用 macOS 私有锁屏接口，立即锁屏，无需辅助功能权限。"""
    try:
        import ctypes
        lib = ctypes.CDLL(
            "/System/Library/PrivateFrameworks/login.framework/Versions/Current/login"
        )
        lib.SACLockScreenImmediate()
        return True
    except Exception:
        # 兜底：模拟 Ctrl+Cmd+Q（需辅助功能权限）
        return osa('tell application "System Events" to keystroke "q" using {command down, control down}')[0]


def system_action(action):
    if action == "lock":
        return lock_screen()
    if action == "displaysleep":
        return run(["pmset", "displaysleepnow"])[0]
    if action == "sleep":
        return run(["pmset", "sleepnow"])[0]
    if action in ("app_terminal", "app_claude", "app_codex"):
        name = {"app_terminal": "Terminal", "app_claude": "Claude", "app_codex": "Codex"}[action]
        return run(["open", "-a", name])[0]
    return False


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # 安静点

    def _send(self, code, body, ctype="application/json"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        ct = ctype if ctype.startswith("image") else ctype + "; charset=utf-8"
        self.send_response(code)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False))

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            path = os.path.join(HERE, "index.html")
            try:
                with open(path, "rb") as f:
                    self._send(200, f.read(), "text/html")
            except FileNotFoundError:
                self._send(404, "index.html 缺失", "text/plain")
            return
        if self.path == "/api/status":
            m = get_music()
            self._json({
                "volume": get_volume(),
                "muted": get_muted(),
                "brightness": get_brightness(),
                "brightnessCli": BRIGHTNESS_OK,
                "track": m["track"],
                "playing": m["playing"],
                "cover": m["cover"],
            })
            return
        if self.path == "/api/stats":
            self._json(get_stats())
            return
        if self.path.startswith("/api/cover"):
            res = export_music_cover()
            if res:
                self._send(200, res[0], res[1])
            else:
                self._send(404, "no cover", "text/plain")
            return
        self._send(404, "not found", "text/plain")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
        except Exception:
            body = {}

        ok = False
        if self.path == "/api/volume":
            ok = set_volume(body.get("value", 0))
        elif self.path == "/api/mute":
            ok = set_muted(bool(body.get("muted")))
        elif self.path == "/api/brightness":
            if "value" in body:
                ok = set_brightness(body["value"])
            elif "delta" in body:
                ok = adjust_brightness_delta(body["delta"])
            elif "nudge" in body:
                ok = nudge_brightness(body["nudge"] == "up")
        elif self.path == "/api/music":
            ok = music_control(body.get("action", ""))
        elif self.path == "/api/system":
            ok = system_action(body.get("action", ""))
        else:
            self._send(404, "not found", "text/plain")
            return

        self._json({"ok": ok})


def main():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    ip = subprocess.run(
        ["ipconfig", "getifaddr", "en0"], capture_output=True, text=True
    ).stdout.strip() or "你的Mac-IP"
    print(f"中控台已启动 ✅  手机访问： http://{ip}:{PORT}")
    print("按 Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
