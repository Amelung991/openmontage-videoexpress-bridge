"""Provider contracts.  Nothing here calls an undocumented vendor endpoint."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SceneRequest:
    scene_id: str
    prompt: str
    narration: str
    target_seconds: float
    aspect_ratio: str


class SceneVideoProvider(ABC):
    """A provider may create a job, or explicitly require an approved hand-off."""

    name: str

    @abstractmethod
    def prepare(self, request: SceneRequest, handoff_dir: Path) -> Path:
        """Create a user-reviewable request artifact and return its path."""


class VideoExpressBrowserProvider(SceneVideoProvider):
    """Official browser-workflow adapter; it deliberately has no HTTP/API client."""

    name = "videoexpress_browser_workflow"

    def prepare(self, request: SceneRequest, handoff_dir: Path) -> Path:
        handoff_dir.mkdir(parents=True, exist_ok=True)
        path = handoff_dir / f"{request.scene_id}.md"
        path.write_text(
            "# VideoExpress scene hand-off\n\n"
            f"- Scene: `{request.scene_id}`\n"
            f"- Target duration: {request.target_seconds:g}s\n"
            f"- Aspect ratio: {request.aspect_ratio}\n"
            "- Mode: official VideoExpress browser workflow (user must be logged in)\n\n"
            "## Video prompt\n\n"
            f"{request.prompt}\n\n"
            "## Narration / lip-sync line\n\n"
            f"{request.narration}\n\n"
            "## Completion contract\n\n"
            f"Export one MP4 named `{request.scene_id}.mp4` to `videoexpress_exports/`. "
            "Do not enable public-gallery sharing.\n",
            encoding="utf-8",
        )
        return path


class ArtistlyProvider(SceneVideoProvider):
    """Reserved extension point for still-image generation."""
    name = "artistly"

    def prepare(self, request: SceneRequest, handoff_dir: Path) -> Path:
        raise NotImplementedError("Artistly adapter requires its documented integration contract.")


class CloneVoiceProvider(SceneVideoProvider):
    """Reserved extension point for voice; VideoExpress can own sync after setup."""
    name = "clonevoice"

    def prepare(self, request: SceneRequest, handoff_dir: Path) -> Path:
        raise NotImplementedError("CloneVoice is configured in VideoExpress by the user.")
