# store-screenshots

A [Claude Code](https://claude.com/claude-code) skill that makes App Store and Google Play screenshots, and the Play feature graphic, for a mobile app.

It captures real screens from the iOS simulator and Android emulator, then puts each one on a colored background with a caption and a phone frame at the sizes the stores require, and checks the files before you upload them.

**It never uploads or submits anything to either store.** It stops at checked image files on disk.

## What it does

1. **Capture.** Boots the simulator or emulator, sets a clean 9:41 status bar, launches each screen you name and saves a PNG. Uses plain `xcrun simctl` and `adb`.
2. **Compose.** Draws each store image from a small JSON config: background, caption with accent-colored words, framed phone, and an optional zoomed callout of one part of the screen. Also draws the 1024x500 Google Play feature graphic.
3. **Check.** Confirms pixel size, format, no alpha channel, file size and file count against the App Store and Google Play requirements.

Two steps are optional:

- **Rotato frames.** If [Rotato](https://rotato.app) is installed and reachable, the phone can be a 3D device render. Otherwise a plain frame is drawn in code, which is the default.
- **Generated test images.** If a screen needs a realistic image as sample data that you don't have (a person for a pose app, a meal for a food app, a skin photo for a dermatology app, a product, a room), a script can generate one with the Gemini API using your own key.

## Requirements

| Need | For |
|---|---|
| macOS | Everything |
| Xcode with an iOS simulator | iOS captures |
| Android SDK platform-tools (`adb`) and an emulator | Android captures |
| Node.js 18+ and [Playwright](https://playwright.dev) | Composing the images |
| Python 3 | The check script and the optional Gemini script |
| Rotato (optional) | 3D device frames |
| `GEMINI_API_KEY` environment variable (optional) | Generated test images used as sample data |

You only need the tools for the parts you use. Composing works on any PNG screenshots you already have.

Install Playwright once if you don't have it:

```bash
npm install -g playwright
```

The compose script uses your installed Google Chrome if there is one, and Playwright's bundled Chromium otherwise (`npx playwright install chromium`).

## Install

Clone it into your personal skills folder:

```bash
git clone https://github.com/ReidGlaze/store-screenshots-skill.git ~/.claude/skills/store-screenshots
```

Update later with `git -C ~/.claude/skills/store-screenshots pull`.

## Run

In Claude Code, type `/store-screenshots`, or just ask:

> Make App Store and Google Play screenshots for my app. Five screens: home, result, history, settings, privacy. Accent color #00838F.

Claude asks for anything it still needs (app, screens, captions, colors), captures the screens, composes the images and runs the checks.

You can also run the scripts yourself:

```bash
SKILL=~/.claude/skills/store-screenshots

# 1. Capture
$SKILL/scripts/capture.sh ios --device "iPhone 17 Pro Max" --bundle com.example.app \
  --out work/raw/ios home result history
$SKILL/scripts/capture.sh android --package com.example.app --activity .MainActivity \
  --out work/raw/android home result history

# 2. Compose (copy templates/config.example.json to work/config.json and edit it first)
node $SKILL/scripts/compose.js work/config.json

# 3. Check
python3 $SKILL/scripts/check.py appstore-iphone-6.9 work/store-screenshots/app-store-6.9in-1320x2868
python3 $SKILL/scripts/check.py play-phone          work/store-screenshots/google-play-1440x2560
python3 $SKILL/scripts/check.py play-feature        work/store-screenshots/feature-graphic-1024x500.png
```

Each state name (`home`, `result`, ...) is passed to your app at launch, so the app needs a small debug-only hook that shows that screen with sample data. [SKILL.md](SKILL.md) explains the hook, the config fields, the size lists and the optional steps.

## Good to know

- **Sample data.** The screens are your real app, but the values in them are sample data. Don't add invented ratings, awards or reviews to captions.
- **Generated images.** The Gemini script writes a `.ai.json` file next to each image it makes. Google Play asks whether listing assets are AI-generated; label those images when you upload them.
- **Keys.** The Gemini key is read from your environment and is never written to a file.
- **Fonts.** Captions use Montserrat from Google Fonts by default, which needs a network connection. Set `"fontUrl": false` in the config to use system fonts.
- **Store sizes change.** The size lists were correct when written. If a store rejects a size, check its current requirements and update `scripts/check.py`.

## License

MIT. See [LICENSE](LICENSE).
