import argparse
import logging
from pathlib import Path
from freemocap.utilities.download_sample_data import download_sample_data
from freemocap.data_layer.recording_models.recording_info_model import RecordingInfoModel

logger = logging.getLogger(__name__)

from pathlib import Path
from typing import Union

# from freemocap.core_processes.capture_volume_calibration.anipose_camera_calibration.anipose_camera_calibrator import (
#     AniposeCameraCalibrator,
# )
from freemocap.core_processes.capture_volume_calibration.charuco_stuff.charuco_board_definition import (
    CharucoBoardDefinition,
)


# def headless_calibration(
#         path_to_folder_of_calibration_videos: Path,
#         charuco_board_object=CharucoBoardDefinition,
#         charuco_square_size: Union[int, float] = 39,
#         pin_camera_0_to_origin: bool = True,
# ):
#     anipose_camera_calibrator = AniposeCameraCalibrator(
#         charuco_board_object=charuco_board_object,
#         charuco_square_size=charuco_square_size,
#         calibration_videos_folder_path=path_to_folder_of_calibration_videos,
#         progress_callback=lambda *args, **kwargs: None,
#         # the empty callable is needed, otherwise calibration will cause an error
#     )

#     return anipose_camera_calibrator.calibrate_camera_capture_volume(pin_camera_0_to_origin=pin_camera_0_to_origin)


from freemocap.core_processes.capture_volume_calibration.run_anipose_capture_volume_calibration import run_anipose_capture_volume_calibration


class SessionInfo:              # unchanged
    sample_session_folder_path: str
    recording_info_model: RecordingInfoModel


def setup_session() -> Path:
    """Download sample data and run the calibration; return the TOML path."""
    logger.info("Downloading sample data…")
    SessionInfo.sample_session_folder_path = download_sample_data(
        sample_data_zip_file_url=(
            "https://github.com/aaroncherian/freemocap_fork_old/releases/download/v0.0.4-alpha/freemocap_test_data.zip"
        )
    )

    logger.info("Initializing recording model…")
    SessionInfo.recording_info_model = RecordingInfoModel(
        recording_folder_path=SessionInfo.sample_session_folder_path,
        active_tracker="mediapipe",
    )

    logger.info("Running headless calibration…")
    toml_path = run_anipose_capture_volume_calibration(
        calibration_videos_folder_path=get_sync_video_folder(),
        charuco_square_size=58,
        charuco_board_definition=CharucoBoardDefinition(),
        progress_callback=lambda _: None,  
    )
    return Path(toml_path)


def get_sync_video_folder() -> Path:
    return Path(SessionInfo.recording_info_model.synchronized_videos_folder_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Absolute or relative path (incl. filename) for the calibration .toml",
    )
    args = parser.parse_args()

    produced = setup_session()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    produced.rename(args.out)          # move/rename in one shot
    print(f"Saved → {args.out.resolve()}")