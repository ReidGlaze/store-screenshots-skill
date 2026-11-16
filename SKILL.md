---
name: store-screenshots
description: Make App Store and Google Play screenshots and the Play feature graphic for a mobile app. Captures real screens from the iOS simulator and Android emulator with sample data, then adds a colored background, captions and a phone frame at each required size, and checks dimensions before upload. Use when the user asks for store screenshots, listing images, a feature graphic, or to redo screenshots in a new color or caption.
---

# Store screenshots

Turns an app into finished store images in two independent parts:

1. **Capture** raw screens from the simulator and emulator (`xcrun simctl`, `adb`).
2. **Compose** each image: background, caption, framed phone, optional zoomed callout.

Part 2 only needs PNG captures, so it also works on screenshots the user already has.
Two steps are optional and never required: Rotato 3D frames, and Gemini-generated test images.

`$SKILL` below is this folder: `~/.claude/skills/store-screenshots`.

## Rules

- **Never upload or submit anything to App Store Connect or Play Console.** This skill ends at checked files on disk. Uploading is a separate request from the user.
- **Keep work files out of the app repo.** Use a scratch folder. Only the finished images go where the user asks (often a `store-screenshots/` folder), and nothing is committed unless asked.
- **Sample data must be honest.** Screens show the real app UI. Sample values are made up; say so to the user. Do not invent ratings, awards, reviews or medical claims in captions.
- **Never write an API key into any file.** Keys come from the environment only.

## Inputs to get first

Ask only for what the request and the project do not already answer.

| Input | Notes |
|---|---|
| App | iOS bundle id and `.app` or Xcode project; Android package, launch activity and APK or Gradle project |
| Screens | 3 to 8 screens, in order, each with a short name (`home`, `result`, ...) |
| Captions | One per screen, two or three short lines. Wrap the emphasized words in `<b>` |
| Accent color | Used for the `<b>` words. Take it from the app's own UI if not given, and check it reads on the background |
| Background | Any CSS background (default: light gray gradient) |
| Sizes | Default: App Store 6.9" (1320x2868) and Google Play phone (1440x2560), plus the 1024x500 feature graphic |
| Feature graphic | App name, icon file, headline |

## Part 1: Capture

### Sample data

A fresh install usually shows empty screens. Give the app a **temporary, debug-only hook** that jumps to a named screen with sample data, driven by a launch argument:

- iOS: read `UserDefaults.standard.string(forKey: "screenshots")`. Launch arguments `-screenshots result` set it.
- Android: read `intent.getStringExtra("shot")` in the launch activity. `--es shot result` sets it.

Keep the hook uncommitted and remove it when the captures are done; confirm with `git status` that the app repo is unchanged afterwards. If the user does not want any code touched, drive the real app to each screen by hand or with a UI test instead, and capture with the state `current`.

### Run

```bash
# iOS: boots the simulator, sets a clean 9:41 status bar, launches each state, saves <state>.png
$SKILL/scripts/capture.sh ios --device "iPhone 17 Pro Max" --bundle com.example.app \
  --app path/to/Debug-iphonesimulator/App.app --out work/raw/ios home result history

# Android: same idea through adb, with SystemUI demo mode for the status bar
$SKILL/scripts/capture.sh android --package com.example.app --activity .MainActivity \
  --apk app/build/outputs/apk/debug/app-debug.apk --out work/raw/android home result history
```

- Pick the simulator by the size you need: an iPhone 17 Pro Max captures 1320x2868 (6.9"), an iPhone 17 Pro 1206x2622 (6.3"). `xcrun simctl list devices available` lists them.
- Start the emulator first (`emulator -avd <name>`), and wait for `adb shell getprop sys.boot_completed` to print `1`.
- `--wait <seconds>` is how long to let each screen settle (default 4). Animated or network screens need more.
- `current` as a state captures whatever is on screen without relaunching.
- Look at every capture before composing. Recapture anything showing a spinner, a permission prompt or a keyboard.

## Part 2: Frame, caption, compose

Copy `templates/config.example.json` into the work folder and fill it in, then:

```bash
node $SKILL/scripts/compose.js work/config.json            # all sets and the feature graphic
node $SKILL/scripts/compose.js work/config.json 02-result  # only shots whose name matches
```

How it draws: each image is an HTML/CSS page (`templates/page.html`) screenshotted at the exact pixel size with Playwright in headless Chrome. The caption font comes from Google Fonts (Montserrat by default; set `"font"`, or `"fontUrl": false` to use system fonts offline). Playwright is found from a global install or the `playwright-skill` skill; otherwise `npm i playwright`.

Config fields:

- `accent`, `text`, `background`, `font`: the look, shared by every image.
- `sets[]`: one per output size. `width`/`height` are the final pixels, `rawDir` holds that platform's captures, `captionHeight` is the caption band as a fraction of height, `fontSize` a fraction of width.
- `shots[]`: `name` (output file name, numbered for store order), `source` (capture file name without `.png`), `caption`.
- `sets[].callouts`: optional, keyed by shot name. `crop` is `[x, y, w, h]` in raw-capture pixels; that region is enlarged over the phone. `dy` nudges it vertically (fraction of height), `radius` rounds it. Crops differ per platform because the captures differ.
- `feature`: the 1024x500 graphic: `appName`, `icon`, `headline`, `source`, and which `set` to take the phone from. Keep text and the phone away from the edges; Play can crop it and overlay a play button.

### Frames: code by default, Rotato when available

By default `compose.js` draws a plain phone frame in CSS around the capture. Nothing else is needed.

For a 3D device render, check for Rotato and use it only if it answers:

```bash
$SKILL/scripts/rotato_frame.sh --check     # exit 0 = available, 3 = not available
$SKILL/scripts/rotato_frame.sh --device "iPhone 17 Pro Max" --raw work/raw/ios --out work/framed/ios
```

Then add `"framedDir": "framed/ios"` to that set. `compose.js` trims each render to its visible pixels and places it; any shot without a render falls back to the plain frame. If the check or a render fails, carry on with plain frames and tell the user.

- The Rotato CLI ships inside the app (`/Applications/Rotato.app/Contents/Resources/rotato`) and must run outside a sandbox. Read `rotato skill show` before doing anything beyond this script.
- The device must exist in Rotato's catalog. If the wanted Android phone is missing, use plain frames for that set.
- Callouts on a Rotato frame assume the screen sits at `screenInset` `{ "x": 0.039, "y": 0.019, "w": 0.921 }` of the device (measured on iPhone 17 Pro Max and Pixel 10 front renders). If a callout lands off its target, set `screenInset` on the set.

### Optional: generated test images (Gemini API)

Only when a screen needs a realistic image as sample data and the user has none to give. It covers anything the app would normally get from a camera or photo library:

| App kind | Example image |
|---|---|
| Pose, fitness, rehab | A person doing the movement, full body |
| Food, nutrition | A plated meal from above |
| Skin, dermatology | A close-up of skin on a forearm |
| Shopping, scanning | A product on a table, a receipt, a label |
| Home, travel, plants | A room, a street, a houseplant |

```bash
export GEMINI_API_KEY=...        # the user's own key, set in their shell; never store it in a file
python3 $SKILL/scripts/gemini_image.py --list-models

# One image
python3 $SKILL/scripts/gemini_image.py --prompt "Grilled salmon with brown rice and broccoli on a white plate, from above, phone-camera photo, natural light" \
  --aspect 4:3 --out work/images/meal.png

# A series that must match: send the first image back as a reference
python3 $SKILL/scripts/gemini_image.py --prompt "A man in a living room raising his right arm overhead, full body, phone-camera photo" \
  --aspect 3:4 --out work/images/pose-1.png
python3 $SKILL/scripts/gemini_image.py --prompt "Same man, same room, arm out to the side" \
  --reference work/images/pose-1.png --out work/images/pose-2.png
```

- If `GEMINI_API_KEY` is not set, stop and ask the user to set it. Do not look for keys in files or use a browser session instead.
- Describe it the way the app's users would shoot it (phone camera, ordinary light, ordinary setting) so the result looks like real input, not a stock photo.
- `--reference` keeps the same subject and setting across images: the same person, the same plate, the same room. Mirroring an image is a cheap way to get a left/right variant.
- Put the image into the app the normal way (photo picker or the sample-data hook), then capture as in Part 1. What the app shows for it must be the app's real output for that image, or clearly sample data.
- Every output gets a `.ai.json` sidecar recording that it is AI-generated. Tell the user which finished images contain generated content. Google Play asks about AI-generated listing assets when they are uploaded; those images should be labelled there.
- Never present a generated person as a real user or patient, and never pass a generated image off as a real result, such as a real medical case or a real customer's order.
- This script has had less real-world use than the rest of the skill. Review its output closely the first time, and pass `--model` if the automatically chosen model is not the one you want.

## Sizes

Re-check these in App Store Connect and Play Console when a store rejects a size; they change every year or two.

**App Store** (PNG or JPEG, no alpha, 1 to 10 per size)

| Slot | Portrait sizes accepted |
|---|---|
| iPhone 6.9" / 6.7" / 6.5" | 1320x2868, 1290x2796, 1260x2736 |
| iPhone 6.3" / 6.1" | 1206x2622, 1179x2556 |
| iPad 13" | 2064x2752, 2048x2732 |

Landscape is the same numbers swapped. One iPhone set is enough: App Store Connect scales it to the other iPhone slots. iPad needs its own set only if the app runs on iPad.

**Google Play** (PNG or JPEG, no alpha)

| Asset | Requirement |
|---|---|
| Phone screenshots | 2 to 8, each side 320 to 3840 px, long side at most twice the short side, 9:16 recommended (1080x1920 or 1440x2560), up to 8 MB each |
| 7" and 10" tablet screenshots | Up to 8 each, same limits; 9:16 phone images are accepted |
| Feature graphic | Exactly 1024x500, up to 15 MB |
| Icon | 512x512 PNG |

## Check before handing over

```bash
python3 $SKILL/scripts/check.py appstore-iphone-6.9 out/app-store-6.9in-1320x2868
python3 $SKILL/scripts/check.py play-phone          out/google-play-1440x2560
python3 $SKILL/scripts/check.py play-feature        out/feature-graphic-1024x500.png
```

It checks pixel size, format, alpha channel, file size and count, and exits non-zero on any failure. Other kinds: `appstore-iphone-6.3`, `appstore-ipad-13`, `play-tablet`. Fix every failure before telling the user the set is ready.

Then look at the images yourself: build one contact sheet per set and read it, checking that captions are not clipped, the accent color reads on the background, callouts sit on the right part of the screen, and nothing shows debug UI or personal data.

## Finish

Tell the user where the files are, which sizes were made, which frames were used (plain or Rotato), whether any image contains generated content, and that the sample data is made up. Do not upload.
