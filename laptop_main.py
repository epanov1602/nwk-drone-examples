import cv2
from time import time
import pupil_apriltags as apriltags
import detection

face_detector = cv2.CascadeClassifier('resources/haarcascade_frontalface_default.xml')
tag_detector = apriltags.Detector(families="tag36h11", quad_sigma=0.2)

#from ultralytics import YOLO
#model = YOLO("resources/yolov8s.pt")

tracker = detection.create_vit_tracker()


camera = cv2.VideoCapture(0)
success, frame = camera.read()


detecting = True
time_last_seen = 0

while True:
    success, frame = camera.read()
    if not success:
        continue

    # location of the target
    x, y, w, h = None, None, None, None

    if detecting:
        x, y, w, h = detection.detect_biggest_apriltag(tag_detector, frame)
        #x, y, w, h = object_detection.detect_biggest_face(face_detector, frame)
        #x, y, w, h = object_detection.detect_yolo_object(model, frame, valid_classnames={"cell phone"}, lowest_conf=0.3)
        if x is not None:  # if detected something, feed it into the tracker
            tracker.init(frame, (x, y, w, h))
            time_last_seen = time()

    if time_last_seen != 0:
        x, y, w, h = detection.update_tracker(tracker, frame)
        if x is not None:
            time_last_seen = time()
        elif time() > time_last_seen + 3.0:
            time_last_seen = 0  # assume we can no longer track our detection.py, if we have not tracked it for 3s

    status = "DETECTING..." if detecting else "TRACKING..." if time_last_seen != 0 else "LOST!"
    cv2.putText(frame, status, (5, 25), cv2.FONT_HERSHEY_PLAIN, 2, detection.GREEN, 2)
    cv2.imshow("camera", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('d'):
        detecting = True
    elif key == ord('t'):
        detecting = False

