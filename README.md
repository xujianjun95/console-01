# Console 01

Console 01 is a local Mac control panel for phones and tablets on the same LAN.
It serves a Braun-inspired web console that can control volume, brightness,
music playback, sleep/lock actions, and show Bluetooth battery status.

## Features

- Volume and brightness faders with physical-console styling.
- LCD clock and calendar display.
- Quick actions for lock, sleep, Launchpad, Finder, mute, and night mode.
- Music controls for Apple Music or Spotify, including current track and cover art.
- Bluetooth battery readout for connected accessories.
- PWA manifest and icons for adding the console to a phone home screen.
- Night mode with a dimmed plastic body, darker LCD, muted accent colors, and a soft transition animation.

## Requirements

- macOS.
- Python 3.
- Optional: the `brightness` command-line tool for direct brightness reads/writes.
- Accessibility permission for actions that simulate keyboard input, such as brightness fallback keys and Launchpad.

The server uses only the Python standard library.

## Run

From the project directory:

```bash
python3 server.py
```

The server listens on port `8765`:

```text
http://<your-mac-lan-ip>:8765/
```

On this machine the current LAN address has been:

```text
http://192.168.3.11:8765/
```

Your phone must be on the same Wi-Fi or local network as the Mac.

## Night Mode

The lower-right quick key is `Night`. It replaces the old `Search` key.

- Tap `Night` to toggle between day and night themes.
- The selected theme is saved in `localStorage`.
- The transition is animated so the console dims like a physical device instead of switching abruptly.
- The center `I/O` switch is still only for console power or standby behavior.

## Runtime Copy

The running local service may be launched from:

```text
/Users/xujianjun/Library/Application Support/pmtools-console
```

When testing changes through the always-on local service, make sure the updated
`index.html` and `server.py` are also present in that runtime directory, or restart
the service from this repository directory.

## HTTP Routes

- `GET /` or `/index.html` serves the console UI.
- `GET /api/status` returns volume, brightness, mute state, music state, and cover source.
- `GET /api/bluetooth` returns connected Bluetooth accessory battery data.
- `GET /api/cover` returns Apple Music cover art when available.
- `POST /api/volume` sets output volume.
- `POST /api/mute` toggles output mute.
- `POST /api/brightness` sets or nudges brightness.
- `POST /api/music` sends play/pause, next, or previous.
- `POST /api/system` sends system actions.
- `POST /api/claude` sends Claude Code permission menu keystrokes.

Query strings are supported on routes, so cache-busting URLs such as `/?v=night1`
still serve the console instead of returning `not found`.

## Troubleshooting

If the phone still shows an old UI:

1. Refresh the page or open a cache-busting URL such as `/?v=night1`.
2. If using a home-screen PWA, remove and re-add the icon after major UI changes.
3. Confirm that the running service is using the same directory you edited.
4. Check the active listener with:

```bash
lsof -nP -iTCP:8765 -sTCP:LISTEN
```

