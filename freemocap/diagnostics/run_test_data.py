import logging
from pathlib import Path

from freemocap.core_processes.process_motion_capture_videos.process_recording_headless import (
    process_recording_headless,
    find_calibration_toml_path,
)
from freemocap.data_layer.recording_models.recording_info_model import RecordingInfoModel
from freemocap.diagnostics.headless_calibration import headless_calibration
import os
# Configure logging
logger = logging.getLogger(__name__)

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


class SessionInfo:
    """
    Stores paths to key processed data files.
    """
    sample_session_folder_path: str
    recording_info_model: RecordingInfoModel

def setup_session():
    """
    Downloads sample data and processes it. 
    Stores all important paths for easy access.
    """
    logger.info("Downloading sample data...")
    # SessionInfo.sample_session_folder_path = Path(r'/home/runner/work/freemocap_fork/freemocap_fork/freemocap/freemocap_test_data')
    # if os.name == 'nt':
    #     SessionInfo.sample_session_folder_path = download_sample_data(sample_data_zip_file_url='https://github.com/aaroncherian/freemocap_fork/releases/download/v0.0.4-alpha/freemocap_test_data.zip')
    # elif os.name == 'posix':
    #     SessionInfo.sample_session_folder_path = download_sample_data()

    SessionInfo.sample_session_folder_path = download_sample_data(sample_data_zip_file_url='https://github.com/aaroncherian/freemocap_fork/releases/download/v0.0.4-alpha/freemocap_test_data.zip')


    # logger.info("Finding calibration file...")
    # calibration_toml_path = find_calibration_toml_path(SessionInfo.sample_session_folder_path)

    logger.info("Initializing recording model...")
    SessionInfo.recording_info_model = RecordingInfoModel(
        recording_folder_path=SessionInfo.sample_session_folder_path,
        active_tracker="mediapipe",
    )

    logger.info('Calibrating')
    calibration_toml_path = headless_calibration(path_to_folder_of_calibration_videos=get_synchronized_video_folder_path(),
                                                 charuco_square_size=58)
    calibration_toml_path = find_calibration_toml_path(SessionInfo.sample_session_folder_path)
    logger.info("Processing motion capture data...")
    process_recording_headless(
        recording_path=SessionInfo.sample_session_folder_path,
        path_to_camera_calibration_toml=calibration_toml_path,
        recording_info_model=SessionInfo.recording_info_model,
        run_blender=False,
        make_jupyter_notebook=False,
        use_tqdm=False,
    )
    logger.info("Session setup complete!")

def get_sample_session_path():
    return Path(SessionInfo.sample_session_folder_path)

def get_synchronized_video_folder_path():
    return Path(SessionInfo.recording_info_model.synchronized_videos_folder_path)

def get_data_folder_path():
    return Path(SessionInfo.recording_info_model.output_data_folder_path)

def get_raw_skeleton_data():
    return Path(SessionInfo.recording_info_model.raw_data_3d_npy_file_path)

def get_total_body_center_of_mass_data():
    return Path(SessionInfo.recording_info_model.total_body_center_of_mass_npy_file_path)

def get_image_tracking_data():
    return Path(SessionInfo.recording_info_model.data_2d_npy_file_path)

def get_reprojection_error_data():
    return Path(SessionInfo.recording_info_model.reprojection_error_data_npy_file_path)

# Run setup if executed directly
if __name__ == "__main__":
    setup_session()
