
from skellytracker.trackers.charuco_tracker.charuco_model_info import CharucoTrackingParams, CharucoModelInfo
from skellytracker.process_folder_of_videos import process_folder_of_videos
from pathlib import Path
from typing import Union

def get_charuco_2d_data(calibration_videos_folder_path: Union[str, Path], num_processes: int = 1):
    return process_folder_of_videos(
        model_info=CharucoModelInfo(),
        tracking_params=CharucoTrackingParams(),
        synchronized_video_path=Path(calibration_videos_folder_path),
        num_processes=num_processes,
    )