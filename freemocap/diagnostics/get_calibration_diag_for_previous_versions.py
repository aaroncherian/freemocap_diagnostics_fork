"""
build_calibration_dataset.py  ·  FreeMoCap diagnostics helper
----------------------------------------------------------------
Given a folder full of calibration_*.toml files (one per OS/version),
triangulate the ChArUco board for each and save:

  <output_root>/<OS>/<version>/
        ├── calibration.toml                (copied)
        ├── charuco_3d_xyz.npy              (triangulated board points)
        └── charuco_3d_stats.csv            (one-row CSV of board metrics)

Plus a master CSV at  <output_root>/summary.csv  with one row per calibration.

Uses a fixed board:  7 × 5 squares, square-size 58 mm.
----------------------------------------------------------------
"""
from __future__ import annotations
import csv, json, logging, re, shutil
from pathlib import Path
from typing import Dict, List

import numpy as np

from freemocap.utilities.download_sample_data import download_sample_data
from freemocap.data_layer.recording_models.recording_info_model import RecordingInfoModel
from freemocap.core_processes.capture_volume_calibration.charuco_stuff.charuco_board_definition import (
    CharucoBoardDefinition,
)
from freemocap.diagnostics.calibration.calibration_utils import (
    get_charuco_2d_data,
)

from freemocap.core_processes.capture_volume_calibration.anipose_camera_calibration import (
    freemocap_anipose,
)
from freemocap.core_processes.capture_volume_calibration.triangulate_3d_data import triangulate_3d_data

from freemocap.diagnostics.calibration.calibration_utils import (
    get_neighbor_distances,
    get_neighbor_stats
)

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
from dataclasses import asdict   
# --------------------------------------------------------------------
# Constants for the test board (adapt here if you use a different one)
# --------------------------------------------------------------------
BOARD_SQUARE_SIZE_MM = 58
BOARD_NUM_WIDTH  = 7
BOARD_NUM_HEIGHT = 5


def _parse_filename(toml_path: Path) -> tuple[str, str]:
    """
    Parse 'calibration_<OS>_<version>.toml' → ("Windows", "1.5.4")
    """
    m = re.match(r"calibration_(.+)_(\d+\.\d+\.\d+)\.toml$", toml_path.name)
    if not m:
        raise ValueError(f"Unexpected file name: {toml_path.name}")
    return m.group(1), m.group(2)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------
# Main public helper
# --------------------------------------------------------------------
def build_calibration_dataset(
    calibration_folder: Path,
    output_root: Path,
    sample_data_url: str = "https://github.com/aaroncherian/freemocap_fork/releases/download/v0.0.4-alpha/freemocap_test_data.zip",
) -> None:
    """
    Build per-calibration 3-D outputs **and** a master CSV summary.

    Parameters
    ----------
    calibration_folder : Path
        Folder containing calibration tomls named
        'calibration_<OS>_<version>.toml'.
    output_root : Path
        Where to create <OS>/<version>/… subfolders and 'summary.csv'.
    sample_data_url : str
        Zip containing synchronized videos of the board (unchanged across runs).
    """
    calibration_folder = calibration_folder.expanduser().resolve()
    output_root        = output_root.expanduser().resolve()
    _ensure_dir(output_root)

    # ----------------------------------------------------------------
    # 1. Download sample data and detect 2-D corners (once)
    # ----------------------------------------------------------------
    log.info("Downloading sample data …")
    session_path = Path(
        download_sample_data(sample_data_zip_file_url=sample_data_url)
    )
    model = RecordingInfoModel(recording_folder_path=session_path,
                               active_tracker="mediapipe")

    log.info("Detecting Charuco corners (2-D) …")
    charuco_2d_xy = get_charuco_2d_data(
        calibration_videos_folder_path=Path(model.synchronized_videos_folder_path),
        num_processes=3,
    ).astype(np.float64)

    # ----------------------------------------------------------------
    # 2. Iterate over every calibration toml
    # ----------------------------------------------------------------
    summary_rows: List[Dict[str, str | float]] = []

    for toml_path in sorted(calibration_folder.glob("calibration_*.toml")):
        os_name, version = _parse_filename(toml_path)
        log.info(f"Processing {toml_path.name} …")

        # Output layout
        run_out = output_root / os_name / version
        _ensure_dir(run_out / "output_data")

        # a) copy the toml for traceability
        shutil.copy2(toml_path, run_out / "calibration.toml")

        # b) Triangulate 3-D
        calib = freemocap_anipose.CameraGroup.load(str(toml_path))
        data_3d, *_ = triangulate_3d_data(
            anipose_calibration_object=calib,
            image_2d_data=charuco_2d_xy,
        )
        npy_path = run_out / "output_data" / "charuco_3d_xyz.npy"
        np.save(npy_path, data_3d)

        # c) Statistics
        distances = get_neighbor_distances(
            charuco_3d_data           = data_3d,
            number_of_squares_width   = BOARD_NUM_WIDTH,
            number_of_squares_height  = BOARD_NUM_HEIGHT,
        )
        stats = asdict(                # <- change here
            get_neighbor_stats(
                distances             = distances,
                charuco_square_size_mm= BOARD_SQUARE_SIZE_MM,
            )
        )

        # d) Save per-run CSV
        csv_path = run_out / "charuco_3d_stats.csv"
        with open(csv_path, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=stats.keys())
            writer.writeheader()
            writer.writerow(stats)

        # e) Add row to summary buffer
        row: Dict[str, str | float] = {"os": os_name, "version": version}
        row.update(stats)
        summary_rows.append(row)

    # ----------------------------------------------------------------
    # 3. Write / append to summary.csv (wide format: one row per calibration)
    # ----------------------------------------------------------------
    summary_csv = output_root / "summary.csv"
    fieldnames  = summary_rows[0].keys() if summary_rows else []

    write_header = not summary_csv.exists()
    with open(summary_csv, "a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerows(summary_rows)

    log.info(f"✓ Finished – per-calibration folders plus summary.csv written to {output_root}")
    
if __name__ == "__main__":
    # Example usage
    calibration_folder = Path(r"D:\diagnostics\calibration_diagnostics\calibration")
    output_root = Path(r"D:\diagnostics\calibration_diagnostics")

    # Ensure the paths are absolute
    calibration_folder = calibration_folder.expanduser().resolve()
    output_root = output_root.expanduser().resolve()

    build_calibration_dataset(calibration_folder, output_root)