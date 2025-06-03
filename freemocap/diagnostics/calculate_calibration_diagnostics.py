from pathlib import Path
from freemocap.core_processes.capture_volume_calibration.charuco_stuff.charuco_board_definition import (
    CharucoBoardDefinition,
)
from freemocap.diagnostics.calibration.calibration_utils import (
    get_neighbor_distances,
    get_neighbor_stats
)
import numpy as np
import json

def run(path_to_recording: Path,
        freemocap_version: str):
    
    path_to_3d_data = path_to_recording/"output_data"/"charuco_3d_xyz.npy"
    charuco_3d_data = np.load(path_to_3d_data)

    path_to_json = path_to_recording/"charuco_board_info.json"
    with open(path_to_json, "r", encoding="utf-8") as fh:
        charuco_board_info = json.load(fh)

    charuco_square_size_mm = charuco_board_info["square_size_mm"]
    number_of_squares_height = charuco_board_info["num_squares_height"]
    number_of_squares_width = charuco_board_info["num_squares_width"]

    distances_between_squares = get_neighbor_distances(
        charuco_3d_data=charuco_3d_data,
        number_of_squares_width=number_of_squares_width,
        number_of_squares_height=number_of_squares_height,
    )
    
    square_stats = get_neighbor_stats(
        distances=distances_between_squares,
        charuco_square_size_mm=charuco_square_size_mm
    )

    print(square_stats)


if __name__ == "__main__":
    # Use environment detection to handle different runners
    import sys

    if sys.platform.startswith('win'):
        path_to_recording = Path(r"C:\Users\runneradmin\freemocap_data\recording_sessions\freemocap_test_data")
    elif sys.platform.startswith('linux'):
        path_to_recording = Path("/home/runner/freemocap_data/recording_sessions/freemocap_test_data")
    elif sys.platform.startswith('darwin'): 
        path_to_recording = Path("/Users/runner/freemocap_data/recording_sessions/freemocap_test_data")
    else:
        raise RuntimeError(f"Unsupported OS: {sys.platform}")

    freemocap_version = 'current'
    run(path_to_recording=path_to_recording,
        freemocap_version=freemocap_version)

