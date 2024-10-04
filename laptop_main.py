import cv2
from time import time
import pupil_apriltags as apriltags
from ultralytics import YOLO
import detection

# what kind of objects can we detect?
face_detector = cv2.CascadeClassifier('resources/haarcascade_frontalface_default.xml')
model = YOLO("resources/yolov8s.pt")  # model to detect common objects like "person", "car", "cellphone" (see "COCO")
tag_detector = apriltags.Detector(families="tag36h11", quad_sigma=0.2)

tracker = detection.TrackerState(detection.create_vit_tracker(), display_confidence=True)


camera = cv2.VideoCapture(0)
success, frame = camera.read()


detecting = True
time_last_seen = 0

# location of the target
x, y, w, h = None, None, None, None

while True:
    success, frame = camera.read()
    if not success:
        continue

    if detecting:
        #x, y, w, h = detection.detect_biggest_face(face_detector, frame, tracker=tracker, previous_xywh=(x, y, w, h))
        x, y, w, h = detection.detect_biggest_apriltag(tag_detector, frame, tracker=tracker)
        #x, y, w, h = detection.detect_yolo_object(model, frame, valid_classnames={"cell phone"}, lowest_conf=0.3)
        #x, y, w, h = detection.detect_yolo_object(model, frame, tracker=tracker, valid_classes={"cell phone"}, lowest_conf=0.3)

    nx, ny, size = detection.to_normalized_x_y_size(frame, x, y, w, h, draw_box=True)
    cv2.imshow("camera", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('d'):
        detecting = True
    elif key == ord('t'):
        detecting = False

