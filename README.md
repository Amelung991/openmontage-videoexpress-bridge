# OpenMontage × VideoExpress bridge

This is a safe local prototype for: **brief → scene plan/prompts → VideoExpress → MP4 exports → OpenMontage edit artifacts → render**.

It does not call an undocumented VideoExpress API, inspect private network traffic, scrape the app, or bypass a login. The `VideoExpressBrowserProvider` only creates a reviewable hand-off pack and imports MP4 files the signed-in user/export workflow has produced.

## Why this design

OpenMontage stores an asset manifest and edit decisions as plain JSON. This bridge writes those two documented artifact shapes, with each source clip explicitly attributed to `videoexpress_browser_workflow`. It therefore fits the local-first OpenMontage project model and can be rendered by its `video_compose` using the `ffmpeg` runtime.

VideoExpress's official Workflow Library also publishes a browser-agent workflow for Codex/ChatGPT. Use that official path for in-browser automation after you log in; its own instructions say the agent must stop for login and avoid public-gallery sharing. The hand-off files here make each generated scene deterministic and traceable.

## macOS quick start

Requires Python 3.10+. FFmpeg is optional for the bridge, but required by OpenMontage for rendering.

```bash
cd /path/to/openmontage-videoexpress-prototype
python3 -m videobridge.cli init ~/Movies/my-video --title "My video" --brief "A 30-second introduction to a solar-powered bike"
```

1. Inspect and edit `~/Movies/my-video/artifacts/scene_plan.json` and the individual `handoff/videoexpress/*.md` files.
2. Log in yourself at `app.videoexpress.ai` in the browser that your agent controls. Use the official VideoExpress workflow page, or paste each hand-off prompt into the appropriate official VideoExpress creation flow. Confirm credits/purchases yourself.
3. Export one MP4 for each scene into `~/Movies/my-video/videoexpress_exports/`, named exactly `scene_01.mp4`, `scene_02.mp4`, and so on. Keep the files private.
4. Import and validate:

```bash
python3 -m videobridge.cli ingest ~/Movies/my-video
python3 -m videobridge.cli validate ~/Movies/my-video
```

5. Copy `assets/` and `artifacts/asset_manifest.json` plus `artifacts/edit_decisions.json` into an OpenMontage project. Ask OpenMontage to compose using those artifacts (the initial runtime is `ffmpeg` for concatenated source footage), then render locally.

## Automation boundary

| Step | Status |
| --- | --- |
| Make scene plan, prompt hand-offs | automatic |
| Drive VideoExpress browser UI | supported through its official browser-agent workflow; requires user login and active browser session |
| Login, purchases/credits, CAPTCHA/security checks | manual user authorization |
| MP4 import, provenance manifest, ordered timeline decisions | automatic after exports arrive |
| OpenMontage composition/render | local; requires OpenMontage and FFmpeg installed |
| CloneVoice | later: configure its official API key inside VideoExpress, then use the Narrative Video workflow |
| Artistly | later: supply consistent images through its documented integration; provider seam already reserved |

## Tests

Run `python3 -m unittest discover -s tests -v`. The test suite uses a mocked MP4 export and confirms that the produced artifacts validate without requiring a vendor account, a browser, or network access.
