from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from .providers import SceneRequest, VideoExpressBrowserProvider


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def duration(path: Path, fallback: float) -> float:
    """Use ffprobe when installed; retain planned duration for portable dry runs."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, check=True,
        )
        return round(float(result.stdout.strip()), 3)
    except (FileNotFoundError, subprocess.CalledProcessError, ValueError):
        return fallback


def init(args):
    root = Path(args.project).resolve()
    for rel in ("assets/video", "videoexpress_exports", "handoff/videoexpress", "artifacts"):
        (root / rel).mkdir(parents=True, exist_ok=True)
    scenes = [
        {"id": "scene_01", "prompt": "Cinematic opening that establishes the topic.", "narration": args.brief, "target_seconds": 6},
        {"id": "scene_02", "prompt": "Clear visual explanation with purposeful motion.", "narration": "Develop the central idea with one concrete visual beat.", "target_seconds": 6},
        {"id": "scene_03", "prompt": "Memorable closing image and call to action.", "narration": "Close with the key takeaway.", "target_seconds": 6},
    ]
    plan = {"version": "1.0", "title": args.title, "aspect_ratio": args.aspect_ratio, "scenes": scenes}
    write_json(root / "artifacts/scene_plan.json", plan)
    provider = VideoExpressBrowserProvider()
    for scene in scenes:
        provider.prepare(SceneRequest(scene["id"], scene["prompt"], scene["narration"], scene["target_seconds"], args.aspect_ratio), root / "handoff/videoexpress")
    print(f"Created {root}. Review artifacts/scene_plan.json, then run the official VideoExpress browser workflow.")


def ingest(args):
    root = Path(args.project).resolve()
    plan = read_json(root / "artifacts/scene_plan.json")
    scene_by_id = {s["id"]: s for s in plan["scenes"]}
    exports = root / "videoexpress_exports"
    assets = root / "assets/video"
    assets.mkdir(parents=True, exist_ok=True)
    manifest_assets, cuts, missing = [], [], []
    cursor = 0.0
    for scene_id, scene in scene_by_id.items():
        source = exports / f"{scene_id}.mp4"
        if not source.exists():
            missing.append(source.name)
            continue
        target = assets / source.name
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)
        seconds = duration(target, scene["target_seconds"])
        asset_id = f"videoexpress_{scene_id}"
        manifest_assets.append({"id": asset_id, "type": "video", "path": f"assets/video/{target.name}", "source_tool": "videoexpress_browser_workflow", "scene_id": scene_id, "prompt": scene["prompt"], "duration_seconds": seconds, "format": "mp4", "provider": "VideoExpress", "generation_summary": "Exported through the official, user-authorized browser workflow."})
        cuts.append({"id": f"cut_{scene_id}", "source": asset_id, "in_seconds": 0, "out_seconds": seconds, "speed": 1.0, "layer": "primary", "transition_in": "cut" if cursor else "none", "reason": f"VideoExpress export for {scene_id}"})
        cursor += seconds
    manifest = {"version": "1.0", "assets": manifest_assets, "total_cost_usd": 0, "metadata": {"bridge": "videobridge", "missing_exports": missing}}
    decisions = {"version": "1.0", "cuts": cuts, "render_runtime": "ffmpeg", "renderer_family": "cinematic-trailer", "metadata": {"title": plan["title"], "proposal_render_runtime": "ffmpeg", "bridge": "VideoExpress → OpenMontage"}}
    write_json(root / "artifacts/asset_manifest.json", manifest)
    write_json(root / "artifacts/edit_decisions.json", decisions)
    if missing:
        print("Imported available clips. Still waiting for: " + ", ".join(missing))
        return 2
    print(f"Imported {len(cuts)} MP4 clips; OpenMontage artifacts are ready in {root / 'artifacts'}.")


def validate(args):
    root = Path(args.project).resolve()
    plan = read_json(root / "artifacts/scene_plan.json")
    manifest = read_json(root / "artifacts/asset_manifest.json")
    decisions = read_json(root / "artifacts/edit_decisions.json")
    ids = {a["id"] for a in manifest.get("assets", [])}
    failures = []
    if manifest.get("version") != "1.0" or decisions.get("version") != "1.0": failures.append("artifact version must be 1.0")
    if decisions.get("render_runtime") not in {"ffmpeg", "remotion", "hyperframes"}: failures.append("invalid render runtime")
    if len(manifest["assets"]) != len(plan["scenes"]): failures.append("every planned scene needs an MP4 export")
    for cut in decisions["cuts"]:
        if cut["source"] not in ids or cut["out_seconds"] <= cut["in_seconds"]: failures.append(f"invalid cut: {cut['id']}")
    if failures:
        print("INVALID: " + "; ".join(failures)); return 1
    print(f"VALID: {len(manifest['assets'])} assets, {len(decisions['cuts'])} ordered cuts, OpenMontage artifact shapes ready.")


def main():
    parser = argparse.ArgumentParser(prog="videobridge")
    sub = parser.add_subparsers(required=True)
    p = sub.add_parser("init"); p.add_argument("project"); p.add_argument("--title", default="VideoExpress production"); p.add_argument("--brief", default="Introduce the subject with a confident opening."); p.add_argument("--aspect-ratio", default="9:16"); p.set_defaults(func=init)
    p = sub.add_parser("ingest"); p.add_argument("project"); p.set_defaults(func=ingest)
    p = sub.add_parser("validate"); p.add_argument("project"); p.set_defaults(func=validate)
    args = parser.parse_args(); return args.func(args) or 0


if __name__ == "__main__": sys.exit(main())
