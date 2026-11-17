import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import call, patch

import numpy as np

from main import Match, build_parser, monitor


class MonitorTest(unittest.TestCase):
    def test_beeps_and_saves_evidence_with_confirmation_and_cooldown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = build_parser().parse_args(
                ["monitor", "--region", "0,0,100,100", "--detections", directory]
            )
            frame = np.zeros((100, 100, 4), dtype=np.uint8)
            output = io.StringIO()
            beep_counts = []

            def finish_frame(_interval: float) -> None:
                beep_counts.append(beep.call_count)
                if len(beep_counts) == 6:
                    raise KeyboardInterrupt

            with (
                patch.dict(os.environ, {}, clear=True),
                patch("main.CaptchaDetector") as detector,
                patch("main.mss.mss") as screen,
                patch("main.time.monotonic", side_effect=[100, 101, 102, 103, 132, 133]),
                patch("main.time.sleep", side_effect=finish_frame),
                patch("main.winsound.Beep") as beep,
                redirect_stdout(output),
            ):
                detector.return_value.detected.return_value = Match(Path("capcha1.png"), 0.95)
                screen.return_value.__enter__.return_value.grab.return_value = frame
                self.assertEqual(monitor(args), 0)

            self.assertEqual(beep_counts, [0, 5, 5, 5, 10, 10])
            self.assertEqual(
                beep.call_args_list,
                [
                    call(1200, 250),
                    call(1500, 250),
                    call(1800, 250),
                    call(2100, 250),
                    call(2400, 250),
                ] * 2,
            )
            self.assertEqual(output.getvalue().count("CANH BAO CAPTCHA"), 2)
            self.assertIn("canh bao=beep", output.getvalue())
            self.assertTrue(list(Path(directory).glob("detection-*.png")))


if __name__ == "__main__":
    unittest.main()
