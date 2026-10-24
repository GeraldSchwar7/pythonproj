import cv2

# ============================================================
# CAMERA MANAGER
# ============================================================

class CameraManager:

    def __init__(self):
        self.cap = None
        self.camera_index = None

    def find_available_cameras(self, max_cameras=10):

        cameras = []

        for index in range(max_cameras):

            cap = cv2.VideoCapture(index)

            if cap.isOpened():

                ret, _ = cap.read()

                if ret:
                    cameras.append(index)

            cap.release()

        return cameras

    def open_camera(self, camera_index):

        self.release()

        self.camera_index = camera_index
        self.cap = cv2.VideoCapture(camera_index)

        return self.cap.isOpened()

    def read_frame(self):

        if self.cap is None:
            return False, None

        if not self.cap.isOpened():
            return False, None

        return self.cap.read()

    def release(self):

        if self.cap is not None:
            self.cap.release()
            self.cap = None
