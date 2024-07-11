import cv2
import pupil_apriltags as apriltags
from time import time, sleep

import detection
import videocar

tracker = detection.create_vit_tracker()
face_detector = cv2.CascadeClassifier('resources/haarcascade_frontalface_default.xml')
tag_detector = apriltags.Detector(families="tag36h11", quad_sigma=0.2)

#from ultralytics import YOLO
#model = YOLO("resources/yolov8s.pt")


videocar.start(
    simulation=False,
    motor_directions=(-1, -1),
    video_direction=-1,
    #robot_hostname="localhost",  # if you want to use SSH tunnel (to go around firewall)
)

chasing = False
tracking = False

last_seen_rel_x = None
last_seen_time = 0  # never saw


while True:
    key = cv2.waitKey(1) & 0xFF
    if key == ord('a'):
        videocar.set_arcade_drive(forward_speed=0.3, right_turn_speed=-1)
    elif key == ord('d'):
        videocar.set_arcade_drive(forward_speed=0.3, right_turn_speed=1)
    elif key == ord(' '):
        videocar.set_arcade_drive(forward_speed=0, right_turn_speed=0)
        chasing = False
    elif key == ord('c'):
        chasing = True

    frame = videocar.get_video_frame()
    if frame is None:
        continue  # no frame

    clicks = videocar.get_clicks()
    if clicks:
        last_click = clicks[-1]  # the last of all clicks
        bbox = last_click['x'], last_click['y'], last_click['w'], last_click['h']  # bounding box selected by the click
        tracker.init(frame, bbox)
        tracking = True

    buttons = videocar.get_buttons()
    for button in buttons:
        if button == "follow":
            chasing = True
        if button == "stop":
            videocar.set_arcade_drive(0, 0)
            chasing = False

    frame_width = frame.shape[1]

    x, y, w, h = None, None, None, None

    # try to use our tracker, if it is set
    if tracking:
        x, y, w, h = detection.update_tracker(tracker, frame)
        if x is not None:
            last_seen_time = time()
        elif time() > last_seen_time + 2:
            tracking = False  # if not tracking for >2s, assume we lost it

    if x is None:
        x, y, w, h = detection.detect_biggest_apriltag(tag_detector, frame)
        detection.print_relative_xw(frame, x, y, w, h)

    if chasing:
        rel_x, rel_y, rel_w = detection.to_relative_xyw(frame, x, y, w, h)

        if rel_x is not None:
            # 1. if we see the object now, drive towards it
            forward_speed = 1.0 if rel_w < 0.3 else 0.0
            turn_speed = -0.75 if rel_x < -0.15 else +0.75 if rel_x > 0.15 else 0  # turn if it is too far to the side
            videocar.set_arcade_drive(forward_speed, turn_speed)
            last_seen_rel_x = rel_x
            last_seen_time = time()

        elif last_seen_rel_x is not None and time() < last_seen_time + 2.0:
            # 2. if we saw the object withing 2 seconds before, turn towards where it was
            forward_speed = 0.2
            turn_speed = -0.7 if last_seen_rel_x < 0 else +0.7
            videocar.set_arcade_drive(forward_speed, turn_speed)

        else:
            # 3. if we have not seen it in a while, stop
            videocar.set_arcade_drive(0, 0)

    status = "CHASING (press SPACE to stop)" if chasing else "NOT CHASING (press C to chase)"
    cv2.putText(frame, status, (5, frame.shape[0] - 15), cv2.FONT_HERSHEY_PLAIN, 2, detection.GREEN, 2)

    videocar.display_video_frame(frame)
    cv2.imshow("car", frame)

