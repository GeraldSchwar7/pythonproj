import os
import cv2


IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".webp",
    ".gif"
}

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".m4v"
}


class MediaClip:

    def __init__(
        self,
        file_path,
        start_time=0.0,
        duration=None
    ):

        self.file_path = file_path

        # Position of this clip on the project timeline.
        self.start_time = max(
            0.0,
            float(start_time)
        )

        self.media_type = self._detect_type()

        # Video information.
        self.fps = 0.0
        self.frame_count = 0

        # Images default to five seconds.
        self.source_duration = 5.0

        if self.media_type == "video":
            self._read_video_metadata()

        if duration is None:

            if self.media_type == "video":
                duration = self.source_duration

            else:
                duration = 5.0

        self.duration = max(
            0.05,
            float(duration)
        )

    # ======================================================
    # MEDIA TYPE
    # ======================================================

    def _detect_type(self):

        extension = os.path.splitext(
            self.file_path
        )[1].lower()

        if extension in VIDEO_EXTENSIONS:
            return "video"

        return "image"

    # ======================================================
    # VIDEO METADATA
    # ======================================================

    def _read_video_metadata(self):

        capture = cv2.VideoCapture(
            self.file_path
        )

        if not capture.isOpened():
            return

        self.fps = float(
            capture.get(
                cv2.CAP_PROP_FPS
            ) or 0.0
        )

        self.frame_count = int(
            capture.get(
                cv2.CAP_PROP_FRAME_COUNT
            ) or 0
        )

        if (
            self.fps > 0
            and self.frame_count > 0
        ):

            self.source_duration = (
                self.frame_count
                / self.fps
            )

        capture.release()

    # ======================================================
    # END TIME
    # ======================================================

    @property
    def end_time(self):

        return (
            self.start_time
            + self.duration
        )

    # ======================================================
    # DISPLAY NAME
    # ======================================================

    @property
    def name(self):

        return os.path.basename(
            self.file_path
        )

    # ======================================================
    # CHECK CURRENT TIME
    # ======================================================

    def contains_time(
        self,
        project_time
    ):

        return (
            self.start_time
            <= project_time
            < self.end_time
        )

    # ======================================================
    # PROJECT TIME -> CLIP TIME
    # ======================================================

    def local_time(
        self,
        project_time
    ):

        return max(
            0.0,
            project_time
            - self.start_time
        )