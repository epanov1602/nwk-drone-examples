import cv2
from ultralytics import YOLO
import detection

# some settings to play with, the goal is to not lose track -- can you tune them?
MAX_FRAMES_WITHOUT_TRACKER_OBJECT_OBSERVED = 40
VALID_OBJECT_CLASSES = {"airplane", "bird"}

# which video to download
downloaded = detection.download_video("https://www.youtube.com/watch?v=IwrfLEw_aTw")


# which tools do we use for detection and tracking?
model = YOLO("resources/yolov8s.pt")  # model to detect common objects like "person", "car", "cellphone" (see "COCO")
tracker = detection.create_vit_tracker()


camera = cv2.VideoCapture(downloaded)
assert camera.isOpened(), "cannot read from downloaded file"


tracking = False
time_last_seen = 0


frame_count = 0
while True:
    success, frame = camera.read()
    if not success:
        continue

    frame_count += 1
    if frame_count < 1600:
        continue  # skip the first 1600 frames of the video
    frame = cv2.resize(frame, (1920 // 2, 1080 // 2))

    x, y, w, h = None, None, None, None

    if tracking:
        x, y, w, h = detection.update_tracker(tracker, frame, lowest_allowed_score=0.4)
        if x is None:
            if frame_count > time_last_seen + MAX_FRAMES_WITHOUT_TRACKER_OBJECT_OBSERVED:
                tracking = False

    if frame_count > time_last_seen + 2:
        warning_text = f"not seen for {frame_count - time_last_seen} frames"
        cv2.putText(frame, warning_text, (50, 30), cv2.FONT_HERSHEY_PLAIN, fontScale=1.25, color=(0, 200, 0), thickness=1)
    cv2.imshow("video", frame)
    key = cv2.waitKey(1) & 0xFF

    if not tracking or key == ord(' '):
        x, y, w, h = detection.detect_yolo_object(model, frame, valid_classnames=VALID_OBJECT_CLASSES)
        cv2.imshow("video", frame)
        key = cv2.waitKey(1) & 0xFF
        if x is None:
            cv2.putText(frame,
                        f"re-detection failed (classes: {VALID_OBJECT_CLASSES}), please select manually", (50, 60),
                        cv2.FONT_HERSHEY_PLAIN, fontScale=1.25, color=(0, 200, 0), thickness=1)
            x, y, w, h = cv2.selectROI("video", frame, False)
        if x is not None:
            tracker.init(frame, (x, y, w, h))
            tracking = True

    if x is not None:
        time_last_seen = frame_count
