from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any


def run_cmd(cmd: list[str]) -> None:
    subprocess.check_call(cmd)


def append_black_tail(input_path: str, output_path: str, width: int = 1920, height: int = 1080, tail_seconds: int = 3) -> None:
    with tempfile.TemporaryDirectory() as tmpd:
        black_path = Path(tmpd) / "black.mp4"
        run_cmd(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=size={width}x{height}:duration={tail_seconds}:color=black", str(black_path)])
        run_cmd([
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-i",
            str(black_path),
            "-filter_complex",
            "[0:v][1:v]concat=n=2:v=1:a=0[outv]",
            "-map",
            "[outv]",
            "-c:v",
            "libx264",
            output_path,
        ])


def process_run_job(payload: dict[str, Any]) -> dict[str, Any]:
    # payload: job_id, user_id, model_name, prompt, duration_seconds, audio, input_url(s)
    # Заглушка: берём входной файл (не скачиваем), прогоняем постобработку и возвращаем фиктивный s3_key
    with tempfile.TemporaryDirectory() as tmpd:
        inp = Path(tmpd) / "in.mp4"
        outp = Path(tmpd) / "out.mp4"
        # создаём короткий цветной ролик как заглушку "входа"
        run_cmd(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=size=1920x1080:duration=1:color=blue", str(inp)])
        append_black_tail(str(inp), str(outp))
    return {"ok": True, "s3_key": "results/stub.mp4"}

