"""Controls for request counts and independent playback evidence fields."""
import hashlib
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "motion_review_report", Path(__file__).with_name("motion-review-report.py")
)
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


class ReportControls(unittest.TestCase):
    def test_counts_requests_separately_from_lifecycle_items(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)

            def lines(name, rows):
                path = root / name
                path.write_text("".join(json.dumps(row) + "\n" for row in rows))
                return path

            (root / "meta.json").write_text('{"model":"test","effort":"high"}')
            item = {"type": "command_execution", "id": "item_1", "status": "completed"}
            events = lines("events.jsonl", [
                {"type": "thread.started", "thread_id": "trial"},
                {"type": "item.started", "item": item},
                {"type": "item.completed", "item": item},
                {"type": "turn.completed", "usage": {
                    "input_tokens": 100, "cached_input_tokens": 75, "output_tokens": 7,
                }},
            ])
            requests = [{"type": "response_item", "payload": {
                "type": "custom_tool_call", "name": "exec", "input": code,
            }} for code in ("tools.exec_command(...)", "tools.write_stdin(...)",
                            "image(await tools.view_image(...))")]
            rollout = lines("rollout.jsonl", [
                {"type": "session_meta", "payload": {"id": "trial"}}, *requests,
            ])
            calls = lines("calls.jsonl", [{"tool": "frames", "code": 0, "wall_s": 3.0}])
            result = report.run_report(events, rollout, calls, [])
            self.assertEqual(result["agent_tool_requests"], 3)
            self.assertEqual(result["execution_items_by_type"], {"command_execution": 1})
            self.assertEqual(result["application_cli_calls"], 1)
            self.assertEqual(result["image_view_tool_requests"], 1)
            self.assertEqual(result["uncached_input_tokens"], 25)

            wrong = lines("wrong.jsonl", [{"type": "session_meta", "payload": {"id": "other"}}])
            with self.assertRaisesRegex(ValueError, "thread IDs differ"):
                report.run_report(events, wrong, calls, [])

    def test_playback_does_not_treat_media_duration_as_the_player_endpoint(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            video = root / "video.webm"
            video.write_bytes(b"synthetic recording bytes")
            receipt = root / "receipt.json"
            receipt.write_text(json.dumps({
                "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
                "width": 1280, "height": 720, "startup": {"work_sha256": "work"},
                "wasm_sha256": "wasm", "pointer": {"trusted": True},
                "diagnostic": {"status": "failed"},
            }))
            probe = {"streams": [{"width": 1280, "height": 720, "nb_read_frames": "169"}],
                     "format": {"duration": "10.56588"}}
            with patch.object(report.subprocess, "run", return_value=SimpleNamespace(stdout=json.dumps(probe))):
                result = report.playback_report(receipt, video, "10")
                unobserved = report.playback_report(receipt, video, None)
            self.assertEqual(result["player_end"]["observed_seconds"], 10)
            self.assertIsNone(unobserved["player_end"]["observed_seconds"])
            self.assertEqual(result["recording"]["mean_frames_per_s"], 15.99)
            self.assertEqual(result["paused_diagnostic_after_play"]["status"], "failed")
            video.write_bytes(b"other file")
            with patch.object(report.subprocess, "run", side_effect=AssertionError("probe called")):
                with self.assertRaisesRegex(ValueError, "Recording hash differs"):
                    report.playback_report(receipt, video, None)


if __name__ == "__main__":
    unittest.main()
