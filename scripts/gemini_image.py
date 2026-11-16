#!/usr/bin/env python3
"""OPTIONAL: generate a realistic test image with the Gemini API.

Use when a screen needs an image as sample data that the user does not have:
a person for a pose app, a meal for a food app, a skin photo for a dermatology
app, a product, a receipt, a room, or any other scene. The API key is read
from the environment and is never written anywhere.

  export GEMINI_API_KEY=...            # the user's own key; never put it in a file here
  gemini_image.py --list-models
  gemini_image.py --prompt "..." --out images/meal.png [--aspect 4:3]
                  [--reference images/first.png ...] [--model <id>]

Examples:
  gemini_image.py --prompt "Grilled salmon with rice on a white plate, from above, phone photo" \\
                  --aspect 4:3 --out images/meal.png
  gemini_image.py --prompt "A man in a living room raising his right arm overhead, full body" \\
                  --aspect 3:4 --out images/pose-1.png
  gemini_image.py --prompt "Same man, same room, arm out to the side" \\
                  --reference images/pose-1.png --out images/pose-2.png

--reference sends earlier images back so the same subject and setting carry
over (the same person, plate or room). The model comes from --model, else
$GEMINI_IMAGE_MODEL, else the first model the API lists with "image" in its
name. Each output gets a sidecar <name>.ai.json recording that it is
AI-generated, with the model and prompt, so the store's AI-content
declaration can be answered correctly later.
Uses only the Python standard library.
"""
import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request

API = "https://generativelanguage.googleapis.com/v1beta"


def call(method, url, key, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("x-goog-api-key", key)  # header, so the key never appears in a URL
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:600]
        sys.exit("Gemini API error %s: %s" % (e.code, detail))
    except urllib.error.URLError as e:
        sys.exit("Could not reach the Gemini API: %s" % e.reason)


def image_models(key):
    names, token = [], None
    while True:
        url = API + "/models?pageSize=200" + ("&pageToken=" + token if token else "")
        page = call("GET", url, key)
        for m in page.get("models", []):
            name = m.get("name", "").split("/")[-1]
            if "image" in name and "generateContent" in m.get("supportedGenerationMethods", []):
                names.append(name)
        token = page.get("nextPageToken")
        if not token:
            return names


def main():
    ap = argparse.ArgumentParser(
        description="Generate a realistic test image (person, meal, skin, product, scene) with the Gemini API. "
                    "Writes a .ai.json sidecar marking the image as AI-generated.")
    ap.add_argument("--prompt", help="what the image should show, described the way a user would photograph it")
    ap.add_argument("--out", help="output image path, for example images/meal.png")
    ap.add_argument("--aspect", help='aspect ratio such as "4:3", "3:4" or "9:16"')
    ap.add_argument("--reference", action="append", default=[], help="earlier image whose subject and setting should carry over (repeatable)")
    ap.add_argument("--model")
    ap.add_argument("--list-models", action="store_true")
    a = ap.parse_args()

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        sys.exit("Set GEMINI_API_KEY in your environment first (get a key at https://aistudio.google.com/apikey).")

    if a.list_models:
        for n in image_models(key):
            print(n)
        return
    if not a.prompt or not a.out:
        ap.error("--prompt and --out are required")

    model = a.model or os.environ.get("GEMINI_IMAGE_MODEL")
    if not model:
        found = image_models(key)
        if not found:
            sys.exit("No image-capable model found for this key. Pass --model.")
        model = found[0]
        print("using model %s (set GEMINI_IMAGE_MODEL or --model to choose)" % model)

    parts = []
    for ref in a.reference:
        mime = mimetypes.guess_type(ref)[0] or "image/png"
        with open(ref, "rb") as f:
            parts.append({"inlineData": {"mimeType": mime, "data": base64.b64encode(f.read()).decode()}})
    parts.append({"text": a.prompt})
    config = {"responseModalities": ["IMAGE"]}
    if a.aspect:
        config["imageConfig"] = {"aspectRatio": a.aspect}
    reply = call("POST", "%s/models/%s:generateContent" % (API, model), key,
                 {"contents": [{"role": "user", "parts": parts}], "generationConfig": config})

    image = None
    for cand in reply.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            blob = part.get("inlineData") or part.get("inline_data")
            if blob and blob.get("data"):
                image = blob
                break
        if image:
            break
    if not image:
        reason = (reply.get("candidates") or [{}])[0].get("finishReason") or reply.get("promptFeedback")
        sys.exit("The model returned no image (%s). Reword the prompt and try again." % reason)

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "wb") as f:
        f.write(base64.b64decode(image["data"]))
    side = os.path.splitext(a.out)[0] + ".ai.json"
    with open(side, "w") as f:
        json.dump({"ai_generated": True, "tool": "Gemini API", "model": model, "prompt": a.prompt,
                   "references": a.reference, "mime_type": image.get("mimeType") or image.get("mime_type")}, f, indent=2)
    print("wrote %s (%s) and %s" % (a.out, image.get("mimeType") or image.get("mime_type"), side))


if __name__ == "__main__":
    main()
