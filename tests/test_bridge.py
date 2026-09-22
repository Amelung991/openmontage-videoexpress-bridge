import json
import tempfile
import unittest
from pathlib import Path

from videobridge.cli import init, ingest, validate


class Args:
    def __init__(self, **kwargs): self.__dict__.update(kwargs)


class BridgeTest(unittest.TestCase):
    def test_import_creates_openmontage_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "production"
            init(Args(project=str(root), title="Test", brief="A test brief", aspect_ratio="9:16"))
            for scene in json.loads((root / "artifacts/scene_plan.json").read_text())["scenes"]:
                (root / "videoexpress_exports" / f"{scene['id']}.mp4").write_bytes(b"not-a-real-video")
            self.assertIsNone(ingest(Args(project=str(root))))
            self.assertIsNone(validate(Args(project=str(root))))
            manifest = json.loads((root / "artifacts/asset_manifest.json").read_text())
            self.assertEqual(3, len(manifest["assets"]))
            self.assertEqual("videoexpress_browser_workflow", manifest["assets"][0]["source_tool"])

