import logging
from pathlib import Path

from freemocap.core_processes.capture_volume_calibration.run_anipose_capture_volume_calibration import run_anipose_capture_volume_calibration
from freemocap.core_processes.capture_volume_calibration.anipose_camera_calibration import (
    freemocap_anipose,
)
from freemocap.core_processes.capture_volume_calibration.charuco_stuff.charuco_board_definition import (
    CharucoBoardDefinition,
)
from freemocap.core_processes.capture_volume_calibration.triangulate_3d_data import triangulate_3d_data
from pathlib import Path
from freemocap.data_layer.recording_models.recording_info_model import RecordingInfoModel
from freemocap.diagnostics.download_data import download_test
from freemocap.diagnostics.calibration.calibration_utils import (
    get_charuco_2d_data,
)

import numpy as np
import json                                      

# Configure logging
logger = logging.getLogger(__name__)
download_test
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

    SessionInfo.sample_session_folder_path = download_test()

    logger.info("Initializing recording model...")
    SessionInfo.recording_info_model = RecordingInfoModel(
        recording_folder_path=SessionInfo.sample_session_folder_path,
        active_tracker="mediapipe",
    )
    
    logger.info('Calibrating')
    calibration_toml_path = run_anipose_capture_volume_calibration(
        charuco_board_definition=CharucoBoardDefinition(),
        calibration_videos_folder_path=get_synchronized_video_folder_path(),
        charuco_square_size=58, # its difficult not to hardcode this at this point, but we should consider adding metadata that we can pull from to get this
        progress_callback= lambda _: None) 
    
    charuco_2d_xy = get_charuco_2d_data(
        calibration_videos_folder_path=get_synchronized_video_folder_path(),
        num_processes=3
    )

    logger.info("Charuco 2d data detected successfully with shape: "
            f"{charuco_2d_xy.shape}")

    charuco_2d_xy = charuco_2d_xy.astype(np.float64)

    logger.info("Getting 3d Charuco data")
    anipose_calibration_object = freemocap_anipose.CameraGroup.load(str(calibration_toml_path))

    data_3d, *_ = triangulate_3d_data(
        anipose_calibration_object=anipose_calibration_object,
        image_2d_data=charuco_2d_xy
    )
    
    np.save(Path(SessionInfo.sample_session_folder_path) / "output_data"/"charuco_3d_xyz.npy", data_3d)

    board_info = {
        "square_size_mm": anipose_calibration_object.metadata["charuco_square_size"],
        "num_squares_height": CharucoBoardDefinition().number_of_squares_height,
        "num_squares_width": CharucoBoardDefinition().number_of_squares_width,
    }

    info_path = Path(SessionInfo.sample_session_folder_path) / "charuco_board_info.json"
    with open(info_path, "w", encoding="utf-8") as fh:
        json.dump(board_info, fh, indent=4)

    # stats = calculate_calibration_diagnostics(
    #     charuco_3d_data=data_3d,
    #     charuco_square_size_mm= anipose_calibration_object.metadata["charuco_square_size"],
    #     number_of_squares_height=CharucoBoardDefinition().number_of_squares_height,
    #     number_of_squares_width=CharucoBoardDefinition().number_of_squares_width
    # )
    

    # logger.info(f"Calibration diagnostics: {stats}")
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
