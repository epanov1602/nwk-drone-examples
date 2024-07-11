import cv2
from ultralytics import YOLO
import detection

# what kind of objects can we detect?
model = YOLO("resources/yolov8s.pt")  # model to detect common objects like "person", "car", "cellphone" (see "COCO")
tracker = detection.create_vit_tracker()

# if we see more than 40 frames without tracker object, consider it lost
MAX_FRAMES_WITHOUT_TRACKER_OBJECT = 40

downloaded = detection.download_video("https://www.youtube.com/watch?v=4lqVYtuOR84")

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
    x, y, w, h = None, None, None, None

    if tracking:
        x, y, w, h = detection.update_tracker(tracker, frame, lowest_allowed_score=0.4)
        if x is None:
            if frame_count > time_last_seen + MAX_FRAMES_WITHOUT_TRACKER_OBJECT:
                tracking = False

    cv2.imshow("video", frame)
    key = cv2.waitKey(1) & 0xFF

    if not tracking or key == ord(' '):
        x, y, w, h = detection.detect_yolo_object(model, frame, valid_classnames={"airplane"})
        cv2.imshow("video", frame)
        key = cv2.waitKey(1) & 0xFF
        if x is None:
            x, y, w, h = cv2.selectROI("video", frame, False)
        if x is not None:
            tracker.init(frame, (x, y, w, h))
            tracking = True

    if x is not None:
        time_last_seen = frame_count