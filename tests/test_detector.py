import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from main import CaptchaDetector, Match, build_parser, parse_region


class CaptchaDetectorTest(unittest.TestCase):
    ALERT_REGIONS = {
        "capcha1.png": (765, 348, 1212, 745),
        "capcha2.png": (195, 470, 405, 651),
        "capcha4.png": (454, 327, 739, 557),
        "capcha5.png": (388, 219, 841, 547),
        "capcha6.png": (1015, 408, 1295, 673),
        "elite-boss-curse.png": (304, 215, 808, 267),
        "lie-detector-title.png": (286, 196, 729, 517),
        "lie-detector-activated.png": (197, 238, 355, 299),
    }

    def _require_local_samples(self, paths: list[Path]) -> None:
        missing = [path.name for path in paths if not path.is_file()]
        if missing:
            self.skipTest(
                "Thieu anh kiem thu cuc bo (khong phat hanh len GitHub): "
                + ", ".join(missing)
            )

    def test_detects_embedded_template_and_rejects_plain_image(self) -> None:
        template = np.zeros((30, 40), dtype=np.uint8)
        cv2.rectangle(template, (3, 3), (36, 26), 255, 2)
        cv2.putText(template, "C", (12, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 255, 2)

        with tempfile.TemporaryDirectory() as directory:
            templates_dir = Path(directory)
            cv2.imwrite(str(templates_dir / "captcha.png"), template)
            detector = CaptchaDetector(templates_dir, threshold=0.9)

            positive = np.zeros((120, 160), dtype=np.uint8)
            positive[50:80, 70:110] = template
            negative = np.full((120, 160), 127, dtype=np.uint8)

            self.assertIsNotNone(detector.detected(positive))
            self.assertIsNone(detector.detected(negative))

    def test_default_threshold_accepts_boundary_match(self) -> None:
        templates = Path(__file__).resolve().parents[1] / "templates"
        args = build_parser().parse_args(["monitor", "--window", "MapleStory"])
        image = np.zeros((1, 1), dtype=np.uint8)
        for detector in (
            CaptchaDetector(templates),
            CaptchaDetector(templates, args.threshold),
        ):
            with self.subTest(threshold=detector.threshold):
                below = Match(Path("captcha.png"), 0.799)
                boundary = Match(Path("captcha.png"), 0.8)
                with patch.object(detector, "match", side_effect=[below, boundary]):
                    self.assertIsNone(detector.detected(image))
                    self.assertEqual(detector.detected(image), boundary)

    def test_parse_region(self) -> None:
        self.assertEqual(
            parse_region("10,20,800,600"),
            {"left": 10, "top": 20, "width": 800, "height": 600},
        )

    def test_real_maple_alert_assets(self) -> None:
        project_dir = Path(__file__).resolve().parents[1]
        detector = CaptchaDetector(project_dir / "templates")

        positive_paths = [
            project_dir / "samples" / "captcha" / name
            for name in self.ALERT_REGIONS
        ]
        self.assertEqual(
            {path.name for path, _ in detector.templates},
            set(self.ALERT_REGIONS) | {"lie-detector-activated.yellow.png"},
        )
        negative_paths = [
            project_dir / "samples" / "normal" / "screen-normal-example.png",
        ]
        self._require_local_samples(positive_paths + negative_paths)

        for path in positive_paths:
            with self.subTest(path=path.name):
                image = cv2.imread(str(path), cv2.IMREAD_COLOR)
                self.assertIsNotNone(image)
                match = detector.detected(image)
                self.assertIsNotNone(match)
                self.assertEqual(match.template.name, path.name)

        for path in negative_paths:
            with self.subTest(path=path.name):
                image = cv2.imread(str(path), cv2.IMREAD_COLOR)
                self.assertIsNotNone(image)
                self.assertIsNone(detector.detected(image))

    def test_minigame_detection_survives_instruction_and_answer_changes(self) -> None:
        project_dir = Path(__file__).resolve().parents[1]
        detector = CaptchaDetector(project_dir / "templates", threshold=0.8)
        path = project_dir / "samples" / "captcha" / "lie-detector-title.png"
        self._require_local_samples([path])
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        self.assertIsNotNone(image)
        image[217:254, 296:718] = 0
        image[263:448, 301:713] = 0
        match = detector.detected(image)
        self.assertIsNotNone(match)
        self.assertEqual(match.template.name, "lie-detector-title.png")

    def test_activated_message_ignores_countdown_and_click_instructions(self) -> None:
        project_dir = Path(__file__).resolve().parents[1]
        cases = [
            (
                "lie-detector-activated.png",
                (197, 238, 355, 299),
                (230, 198, 315, 235),
                (150, 310, 405, 382),
            ),
            (
                "lie-detector-activated-overlap.png",
                (585, 139, 760, 203),
                (640, 100, 705, 135),
                (540, 214, 810, 282),
            ),
        ]
        samples = project_dir / "samples" / "captcha"
        self._require_local_samples([samples / name for name, *_ in cases])
        detector = CaptchaDetector(project_dir / "templates")

        for name, message, countdown, instructions in cases:
            image = cv2.imread(str(samples / name), cv2.IMREAD_COLOR)
            self.assertIsNotNone(image)
            for changing_text_removed in (False, True):
                with self.subTest(sample=name, changing_text_removed=changing_text_removed):
                    frame = image.copy()
                    if changing_text_removed:
                        for left, top, right, bottom in (countdown, instructions):
                            frame[top:bottom, left:right] = 0
                    match = detector.detected(frame)
                    self.assertIsNotNone(match)
                    self.assertEqual(match.template.name, "lie-detector-activated.yellow.png")
                    self.assertGreaterEqual(match.confidence, 0.8)

            with self.subTest(sample=name, message_removed=True):
                left, top, right, bottom = message
                image[top:bottom, left:right] = 0
                self.assertIsNone(detector.detected(image))

    def test_yellow_text_survives_different_backgrounds(self) -> None:
        templates = Path(__file__).resolve().parents[1] / "templates"
        mask = cv2.imread(
            str(templates / "lie-detector-activated.yellow.png"), cv2.IMREAD_GRAYSCALE
        )
        self.assertIsNotNone(mask)
        detector = CaptchaDetector(templates)
        height, width = mask.shape
        for color in ((20, 20, 20), (240, 240, 240), (200, 60, 200), (255, 100, 10)):
            with self.subTest(background=color):
                frame = np.full((height + 60, width + 80, 3), color, dtype=np.uint8)
                region = frame[30:30 + height, 40:40 + width]
                region[mask > 0] = (0, 255, 255)
                match = detector.detected(frame)
                self.assertIsNotNone(match)
                self.assertEqual(match.template.name, "lie-detector-activated.yellow.png")
                self.assertGreaterEqual(match.confidence, 0.8)

    def test_yellow_text_rejects_partial_messages_and_unrelated_yellow_shapes(self) -> None:
        templates = Path(__file__).resolve().parents[1] / "templates"
        mask = cv2.imread(
            str(templates / "lie-detector-activated.yellow.png"), cv2.IMREAD_GRAYSCALE
        )
        self.assertIsNotNone(mask)
        detector = CaptchaDetector(templates)
        height, width = mask.shape
        for content in ("empty", "solid", "first_line", "second_line", "other_text"):
            with self.subTest(content=content):
                frame = np.zeros((height + 60, width + 80, 3), dtype=np.uint8)
                region = frame[30:30 + height, 40:40 + width]
                if content == "solid":
                    region[:] = (0, 255, 255)
                elif content in ("first_line", "second_line"):
                    partial = mask.copy()
                    if content == "first_line":
                        partial[24:] = 0
                    else:
                        partial[:34] = 0
                    region[partial > 0] = (0, 255, 255)
                elif content == "other_text":
                    for y in (45, 85):
                        cv2.putText(
                            frame, "Reward Dashboard", (40, y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA,
                        )
                self.assertIsNone(detector.detected(frame))

    def test_rejects_scenes_with_alert_regions_masked(self) -> None:
        project_dir = Path(__file__).resolve().parents[1]
        detector = CaptchaDetector(project_dir / "templates", threshold=0.8)
        self._require_local_samples(
            [project_dir / "samples" / "captcha" / name for name in self.ALERT_REGIONS]
        )

        for name, (left, top, right, bottom) in self.ALERT_REGIONS.items():
            with self.subTest(path=name):
                path = project_dir / "samples" / "captcha" / name
                image = cv2.imread(str(path), cv2.IMREAD_COLOR)
                self.assertIsNotNone(image)
                image[top:bottom, left:right] = 0
                self.assertIsNone(detector.detected(image))

if __name__ == "__main__":
    unittest.main()
