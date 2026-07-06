<p align="center">
  <img src="assets/logo/logo.jpg" alt="Screenshot Plus logo" width="140">
</p>

<h1 align="center">Screenshot Plus</h1>

<p align="center">
  Screenshot tool for Windows: capture, annotate, pixelate, stitch long pages while scrolling,
  and present with live zoom and a laser pointer. A single portable executable, free and open source.
</p>

<p align="center">
  <a href="README.md">Español</a> · <a href="README.en.md">English</a>
</p>

<p align="center">
  <a href="https://github.com/Cris223511/screenshot-plus/releases/latest"><img src="https://img.shields.io/github/v/release/Cris223511/screenshot-plus?label=release&color=2f7df6" alt="latest release"></a>
  <a href="https://github.com/Cris223511/screenshot-plus/releases"><img src="https://img.shields.io/github/downloads/Cris223511/screenshot-plus/total?label=downloads&color=2f7df6" alt="downloads"></a>
  <img src="https://img.shields.io/badge/Windows-10%20%7C%2011-2f7df6" alt="windows 10 and 11">
  <img src="https://img.shields.io/badge/Python-3.10%2B-2f7df6" alt="python 3.10 or later">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT license"></a>
</p>

---

## Why

Taking a screenshot, marking it with an arrow and sending it should not require three programs or a subscription. The tools that do this well are usually paid, watermark your images or come stuffed with ads; the free ones fall short at annotating, capturing scrolling pages or presenting live. Screenshot Plus puts that whole workflow into a single portable executable, with no installation, no account and nothing paid inside.

## Downloads

| Version | File | Status |
| ------- | ---- | ------ |
| 1.0.0 | [ScreenshotPlus.exe](https://github.com/Cris223511/screenshot-plus/releases/download/v1.0.0/ScreenshotPlus.exe) | Available |

Just download the `.exe` and run it. There is no installer and no extra steps; every version lives in the [releases](https://github.com/Cris223511/screenshot-plus/releases) section.

> **About the Windows SmartScreen warning.** The first time you run the file, Windows may show "Windows protected your PC" with an unknown publisher. That is the normal behavior for any open source executable without a code signing certificate (a paid service); it does not indicate any problem with the application, whose full source code you can review in this repository. To continue: **More info → Run anyway**. The warning fades away over time as more people run the same file.

## Features

### Capture

- **Region** (Alt + A): the screen freezes, you drag over the area and on release the annotation editor opens. The selection itself can be moved and resized before you decide.
- **Full screen** (Alt + S) and **active window** (Alt + W): straight to the clipboard, with a notification.
- **Scrolling capture** (Alt + D): you pick the area, the rest of the screen gets locked behind a veil, and as you scroll the app stitches the content into one long image with a live preview. The stitching tolerates visual noise (font smoothing, blinking cursors) and discards repeated frames. When you finish, the image opens in a scrollable editor.
- Everything is captured at the **monitor's native resolution**, lossless, even with Windows scaling at 125 or 150 %.
- The app's own panel steps aside when capturing: it never shows up in your shots.

### Annotation editor

- **Shapes** (8): rectangle, rounded rectangle, ellipse, triangle, diamond, pentagon, hexagon and star.
- **Lines and arrows** with a configurable cap on each end independently (none, arrow, filled arrow, dot, square, diamond) and solid, dashed or dotted stroke.
- **Brush** for free drawing with adjustable thickness.
- **Text** with 25+ font families in a dropdown, size, bold, italic and color. You type directly on the image; double click reopens an existing text.
- **Pixelate** to hide emails, numbers or any sensitive data.
- **Everything stays editable**: any drawn element can be selected, moved, resized by its handles, and restyled (color, thickness, stroke) from the same toolbar, live.
- Undo (Ctrl + Z), delete element (Del), reset all, copy (Ctrl + C) and save (Ctrl + S).

### Presentation mode

Built for classes and meetings, with the screen **live**: nothing freezes, videos keep playing.

- **Floating side panel** with rounded corners, draggable to any edge and pinnable always on top.
- **Live zoom** (Z): magnifies what is happening around the cursor, with the wheel or the + and - keys.
- **Laser pointer** (L) with a fading trail; color, size and trail are configurable in Options.
- **Brush** (P), **highlighter** (R), **line** (I) and **arrow** (F) to mark over the screen; C clears everything.

### Application

- **Global hotkeys** that work even with the app in the tray, all customizable.
- **6 languages**: Spanish (default), English, Portuguese, French, German and Italian. Switching applies instantly, no restart.
- **Light and dark themes**, always-on-top pin, custom animated notifications.
- **Single instance**: running the `.exe` twice does not duplicate the app, it brings up the one already running.
- **Start with Windows** and start minimized to the tray, both optional.
- **Update checking** against this repository's releases, with no servers of its own and no telemetry.
- **Built-in user manual and about window**: nothing redirects you outside the application.
- The save folder is remembered between sessions; the last one you use is the next one to open.

## Default hotkeys

| Action | Hotkey |
| ------ | ------ |
| Capture region | Alt + A |
| Capture full screen | Alt + S |
| Capture current window | Alt + W |
| Scrolling capture | Alt + D |
| Presentation panel | Alt + Z |
| Show or hide the panel | Alt + Q |
| Copy / save in the editor | Ctrl + C / Ctrl + S |
| Undo / delete element | Ctrl + Z / Del |

Every global hotkey can be changed in Options → Hotkeys by pressing the new combination.

## Usage in 20 seconds

1. Open `ScreenshotPlus.exe`. The panel shows up and the app stays alive in the system tray.
2. Alt + A, drag over the area, annotate whatever you need with the toolbar.
3. Ctrl + C to copy or Ctrl + S to save. A notification confirms. Esc cancels at any point.

## Running from source

You only need Python 3.10 or later on Windows:

```
git clone https://github.com/Cris223511/screenshot-plus.git
cd screenshot-plus
pip install -r requirements.txt
python main.py
```

## Building the executable

```
scripts\build.bat
```

The script installs PyInstaller if needed, converts the logo to the Windows icon format and leaves `ScreenshotPlus.exe` in the `dist` folder.

## Technology

| Component | Library | Purpose |
| --------- | ------- | ------- |
| Interface | [PySide6](https://doc.qt.io/qtforpython-6/) (Qt) | Windows, overlays, animations, themes, tray |
| Capture | [mss](https://github.com/BoboTiG/python-mss) | Framebuffer reads at native resolution, multi-monitor |
| Imaging | [Pillow](https://python-pillow.org/) | Scroll stitching, export, icon |
| Global hotkeys | [pynput](https://github.com/moses-palmer/pynput) | Keys that work with the app in the background |
| Windows integration | [pywin32](https://github.com/mhammond/pywin32) + ctypes | Active window, registry, capture exclusion |
| Packaging | [PyInstaller](https://pyinstaller.org/) | The single portable executable |

One technical detail we are proud of: live zoom works because the app's windows are excluded from system capture (`WDA_EXCLUDEFROMCAPTURE`), which allows photographing the screen 25 times per second without the app seeing itself.

## Project structure

```
screenshot-plus/
├── main.py                     entry point, single instance control
├── assets/
│   ├── icons/                  the interface's own SVG icons
│   └── logo/                   application logo
├── docs/manual.md              user manual (shown inside the app)
├── scripts/build.bat           executable build script
└── src/
    ├── config/                 preferences, safe paths and hotkeys
    ├── core/                   capture, scroll stitching, clipboard, saving
    ├── i18n/                   translator and the 6 languages as json
    ├── ui/
    │   ├── overlays/           selection editor, presentation mode, floating panel
    │   ├── dialogs/            options, about, manual, language
    │   ├── widgets/            animated buttons, palette, icons
    │   └── themes/             light and dark themes (qss)
    └── utils/                  global hotkeys, single instance, autostart, updater
```

## Settings and data

- Preferences are stored in `%APPDATA%\ScreenshotPlus\settings.json`.
- Screenshots go by default to a `Screenshot Plus` subfolder inside your real Pictures folder (asked to Windows, works in any system language).
- The application collects no data and never connects to the internet, except when you ask it to check for updates (a single request to GitHub's public API).

## Contributing

Bug reports and ideas are welcome in the [issues](https://github.com/Cris223511/screenshot-plus/issues). If you want to contribute code, open a pull request; the project runs with `python main.py` and no extra setup.

## License

MIT © [Cris223511](https://github.com/Cris223511). Use it, modify it and share it freely; the full text is in [LICENSE](LICENSE).

If the application is useful to you, a star on the repository helps more people find it.
