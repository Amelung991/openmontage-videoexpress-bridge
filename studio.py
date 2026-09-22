#!/usr/bin/env python3
"""Local UI for the safe VideoExpress → OpenMontage bridge."""
from __future__ import annotations

import base64
import json
import re
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

from videobridge.cli import ingest, init, validate

ROOT = Path(__file__).resolve().parent
PROJECTS = ROOT / "projects"


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    return slug[:64] or "untitled-production"


def read_json(path: Path, fallback):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


class StudioHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "web"), **kwargs)

    def send_json(self, body, status=HTTPStatus.OK):
        payload = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload))); self.end_headers(); self.wfile.write(payload)

    def body(self):
        return json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))

    def project(self, project_id: str) -> Path:
        path = (PROJECTS / safe_slug(project_id)).resolve()
        if PROJECTS.resolve() not in path.parents: raise ValueError("Invalid project")
        return path

    def status(self, project_id: str):
        root = self.project(project_id)
        plan = read_json(root / "artifacts/scene_plan.json", {})
        manifest = read_json(root / "artifacts/asset_manifest.json", {})
        decisions = read_json(root / "artifacts/edit_decisions.json", {})
        scenes = plan.get("scenes", [])
        clips = []
        for scene in scenes:
            clip = root / "assets/video" / f"{scene['id']}.mp4"
            clips.append({"scene_id": scene["id"], "ready": clip.exists(), "bytes": clip.stat().st_size if clip.exists() else 0})
        complete = bool(scenes) and all(clip["ready"] for clip in clips)
        return {"id": project_id, "title": plan.get("title", project_id), "plan": plan, "clips": clips,
                "manifest_ready": bool(manifest), "timeline_ready": bool(decisions) and complete,
                "cut_count": len(decisions.get("cuts", [])), "complete": complete}

    def do_GET(self):
        if self.path.startswith("/api/projects/"):
            try: return self.send_json(self.status(self.path.rsplit("/", 1)[-1]))
            except Exception as error: return self.send_json({"error": str(error)}, HTTPStatus.NOT_FOUND)
        return super().do_GET()

    def do_POST(self):
        try:
            data = self.body()
            if self.path == "/api/projects":
                project_id = safe_slug(data.get("title", "")); root = self.project(project_id)
                init(SimpleNamespace(project=str(root), title=data.get("title", "Untitled production"),
                    brief=data.get("brief", ""), aspect_ratio=data.get("aspect_ratio", "9:16")))
                return self.send_json(self.status(project_id), HTTPStatus.CREATED)
            match = re.fullmatch(r"/api/projects/([^/]+)/clips", self.path)
            if match:
                root = self.project(match.group(1)); scene_id = safe_slug(data["scene_id"]).replace("-", "_")
                if not re.fullmatch(r"scene_\d+", scene_id): raise ValueError("Choose a valid scene")
                raw = base64.b64decode(data["content"], validate=True)
                if not raw.startswith(b"\x00\x00\x00") and b"ftyp" not in raw[:64]: raise ValueError("Only MP4 files are accepted")
                destination = root / "videoexpress_exports" / f"{scene_id}.mp4"; destination.parent.mkdir(parents=True, exist_ok=True); destination.write_bytes(raw)
                return self.send_json(self.status(match.group(1)))
            match = re.fullmatch(r"/api/projects/([^/]+)/assemble", self.path)
            if match:
                root = self.project(match.group(1)); ingest(SimpleNamespace(project=str(root)))
                return self.send_json(self.status(match.group(1)))
            self.send_json({"error": "Unknown endpoint"}, HTTPStatus.NOT_FOUND)
        except Exception as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)


if __name__ == "__main__":
    PROJECTS.mkdir(exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 8765), StudioHandler)
    print("VideoBridge Studio: http://127.0.0.1:8765")
    server.serve_forever()
