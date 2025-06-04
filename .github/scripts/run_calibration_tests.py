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

import io
import logging
import zipfile
from pathlib import Path

import requests

from freemocap.system.paths_and_filenames.file_and_folder_names import (
    FIGSHARE_SAMPLE_ZIP_FILE_URL,
    FREEMOCAP_SAMPLE_DATA_RECORDING_NAME,
    FREEMOCAP_TEST_DATA_RECORDING_NAME,
    FIGSHARE_TEST_ZIP_FILE_URL,
)
from freemocap.system.paths_and_filenames.path_getters import get_recording_session_folder_path

logger = logging.getLogger(__name__)


def get_sample_data_path(download_if_needed: bool = True) -> str:
    sample_data_path = str(Path(get_recording_session_folder_path()) / FREEMOCAP_TEST_DATA_RECORDING_NAME)
    if not Path(sample_data_path).exists():
        if download_if_needed:
            download_sample_data()
        else:
            raise Exception(f"Could not find sample data at {sample_data_path} (and `download_if_needed` is False)")

    return sample_data_path


def download_sample_data(sample_data_zip_file_url: str = FIGSHARE_TEST_ZIP_FILE_URL) -> str:
    try:
        logger.info(f"Downloading sample data from {sample_data_zip_file_url}...")

        recording_session_folder_path = Path(get_recording_session_folder_path())
        recording_session_folder_path.mkdir(parents=True, exist_ok=True)

        r = requests.get(sample_data_zip_file_url, stream=True, timeout=(5, 60))
        r.raise_for_status()  # Check if request was successful

        z = zipfile.ZipFile(io.BytesIO(r.content))
        z.extractall(recording_session_folder_path)

        if sample_data_zip_file_url == FIGSHARE_TEST_ZIP_FILE_URL:
            figshare_sample_data_path = recording_session_folder_path / FREEMOCAP_TEST_DATA_RECORDING_NAME
        elif sample_data_zip_file_url == FIGSHARE_SAMPLE_ZIP_FILE_URL:
            figshare_sample_data_path = recording_session_folder_path / FREEMOCAP_SAMPLE_DATA_RECORDING_NAME
        else:
            figshare_sample_data_path = recording_session_folder_path / FREEMOCAP_TEST_DATA_RECORDING_NAME
        logger.info(f"Sample data extracted to {str(figshare_sample_data_path)}")
        return str(figshare_sample_data_path)

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise e
    except zipfile.BadZipFile as e:
        logger.error(f"Failed to unzip the file: {e}")
        raise e

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
    import shutil
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
    shutil.move(produced, args.out)      
    print(f"Saved → {args.out.resolve()}")