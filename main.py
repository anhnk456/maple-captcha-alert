from __future__ import annotations

import argparse
import time
import winsound
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import mss
import numpy as np
from mss.exception import ScreenShotError

from game_window import WindowLookupError, find_game_region


IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}


@dataclass(frozen=True)
class Match:
    template: Path
    confidence: float


class CaptchaDetector:
    def __init__(self, templates_dir: Path, threshold: float = 0.8) -> None:
        self.threshold = threshold
        self.templates = self._load_templates(templates_dir)
        if not self.templates:
            raise ValueError(f"Khong tim thay template anh trong: {templates_dir}")

    @staticmethod
    def _load_templates(templates_dir: Path) -> list[tuple[Path, np.ndarray]]:
        templates: list[tuple[Path, np.ndarray]] = []
        for path in sorted(templates_dir.iterdir()):
            if path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if image is not None:
                if path.stem.endswith(".yellow"):
                    image = CaptchaDetector._prepare_yellow_text(image)
                templates.append((path, image))
        return templates

    @staticmethod
    def _prepare_yellow_text(image: np.ndarray) -> np.ndarray:
        if image.ndim == 3:
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            image = cv2.inRange(hsv, (18, 150, 160), (40, 255, 255))
        # Tolerate small italic and antialiasing differences between text frames.
        return cv2.GaussianBlur(image, (7, 7), 0)

    def match(self, image: np.ndarray) -> Match | None:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        yellow_text: np.ndarray | None = None
        best: Match | None = None

        for path, template in self.templates:
            if gray.shape[0] < template.shape[0] or gray.shape[1] < template.shape[1]:
                continue
            if path.stem.endswith(".yellow"):
                if image.ndim != 3:
                    continue
                if yellow_text is None:
                    yellow_text = self._prepare_yellow_text(image)
                result = cv2.matchTemplate(yellow_text, template, cv2.TM_CCORR_NORMED)
            else:
                result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
            confidence = float(result.max())
            if best is None or confidence > best.confidence:
                best = Match(path, confidence)

        return best

    def detected(self, image: np.ndarray) -> Match | None:
        match = self.match(image)
        return match if match and match.confidence >= self.threshold else None


def parse_region(value: str) -> dict[str, int]:
    try:
        left, top, width, height = (int(part.strip()) for part in value.split(","))
    except ValueError as error:
        raise argparse.ArgumentTypeError("Region phai co dang left,top,width,height") from error
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("Width va height phai lon hon 0")
    return {"left": left, "top": top, "width": width, "height": height}


def alert(match: Match) -> None:
    print(
        f"\n[{datetime.now():%H:%M:%S}] CANH BAO CAPTCHA "
        f"({match.template.name}, confidence={match.confidence:.3f})"
    )
    for frequency in (1200, 1500, 1800, 2100, 2400):
        winsound.Beep(frequency, 250)


def check_images(args: argparse.Namespace) -> int:
    detector = CaptchaDetector(args.templates, args.threshold)
    image_paths = [
        path
        for path in args.images.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    if not image_paths:
        print(f"Khong tim thay anh trong: {args.images}")
        return 1

    for path in sorted(image_paths):
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            print(f"[BO QUA] {path}")
            continue
        match = detector.match(image)
        confidence = match.confidence if match else 0.0
        status = "PHAT HIEN" if match and confidence >= args.threshold else "BINH THUONG"
        template_name = match.template.name if match else "-"
        print(f"[{status}] {path} | {template_name} | {confidence:.3f}")
    return 0


def monitor(args: argparse.Namespace) -> int:
    detector = CaptchaDetector(args.templates, args.threshold)
    consecutive_hits = 0
    last_alert_at = 0.0
    args.detections.mkdir(parents=True, exist_ok=True)

    target = (
        f"cua so '{args.window}' (chi khi o phia truoc)"
        if args.window
        else f"region={args.region}"
    )
    print(
        f"Dang giam sat {target}, canh bao=beep, nguong khop={args.threshold:g}. "
        "Nhan Ctrl+C de dung."
    )
    waiting_for_window = False
    with mss.mss() as screen:
        try:
            while True:
                region = args.region
                if args.window:
                    try:
                        region = find_game_region(args.window)
                    except (WindowLookupError, OSError) as error:
                        print(f"[LOI CUA SO] {error}")
                        return 1
                    if region is None:
                        if not waiting_for_window:
                            print(
                                f"[{datetime.now():%H:%M:%S}] [TAM DUNG] "
                                "Game chua mo, dang thu nho hoac khong o phia truoc. "
                                "Mo/khoi phuc va chon cua so game de tiep tuc."
                            )
                        waiting_for_window = True
                        consecutive_hits = 0
                        time.sleep(args.interval)
                        continue
                    if waiting_for_window:
                        print(
                            f"[{datetime.now():%H:%M:%S}] [TIEP TUC] "
                            "Cua so game da o phia truoc. Dang theo doi CAPTCHA."
                        )
                        waiting_for_window = False
                try:
                    frame = np.asarray(screen.grab(region))[:, :, :3]
                except ScreenShotError as error:
                    if not args.window:
                        raise
                    print(f"[LOI CHUP] {error}. Dang thu lai.")
                    consecutive_hits = 0
                    time.sleep(args.interval)
                    continue
                if args.window:
                    try:
                        current_region = find_game_region(args.window)
                    except (WindowLookupError, OSError) as error:
                        print(f"[LOI CUA SO] {error}")
                        return 1
                    if current_region != region:
                        consecutive_hits = 0
                        time.sleep(args.interval)
                        continue
                match = detector.detected(frame)
                consecutive_hits = consecutive_hits + 1 if match else 0
                now = time.monotonic()

                if (
                    match
                    and consecutive_hits >= args.confirm_frames
                    and now - last_alert_at >= args.cooldown
                ):
                    output = args.detections / f"detection-{datetime.now():%Y%m%d-%H%M%S}.png"
                    cv2.imwrite(str(output), frame)
                    alert(match)
                    print(f"Da luu bang chung: {output}")
                    last_alert_at = now
                    consecutive_hits = 0

                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nDa dung giam sat.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Phat hien mau CAPTCHA tren anh/man hinh va phat canh bao."
    )
    parser.add_argument("--templates", type=Path, default=Path("templates"))
    parser.add_argument("--threshold", type=float, default=0.8)
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check", help="Kiem tra cac anh co san")
    check_parser.add_argument("images", type=Path)
    check_parser.set_defaults(handler=check_images)

    monitor_parser = subparsers.add_parser("monitor", help="Giam sat mot vung man hinh")
    capture_group = monitor_parser.add_mutually_exclusive_group(required=True)
    capture_group.add_argument(
        "--region",
        type=parse_region,
        help="Vung chup theo dang left,top,width,height",
    )
    capture_group.add_argument(
        "--window",
        help="Chi theo doi cua so o phia truoc; MapleStory gom ca MapleStory N",
    )
    monitor_parser.add_argument("--interval", type=float, default=0.75)
    monitor_parser.add_argument("--cooldown", type=float, default=30.0)
    monitor_parser.add_argument("--confirm-frames", type=int, default=2)
    monitor_parser.add_argument("--detections", type=Path, default=Path("detections"))
    monitor_parser.set_defaults(handler=monitor)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not 0.0 <= args.threshold <= 1.0:
        parser.error("Threshold phai nam trong khoang 0..1")
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())