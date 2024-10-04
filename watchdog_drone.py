from djitellopy import Tello
import detection
import cv2
import pupil_apriltags as apriltags
#from ultralytics import YOLO

# what kind of objects can we detect?
tracker = detection.TrackerState(detection.create_vit_tracker(), display_confidence=True)
face_detector = cv2.CascadeClassifier('resources/haarcascade_frontalface_default.xml')
tag_detector = apriltags.Detector(families="tag36h11", quad_sigma=0.2)
#model = YOLO("resources/yolov8s.pt")  # model to detect common objects like "person", "car", "cellphone" (see "COCO")


# start the drone
drone = Tello()
drone.connect()
drone.streamon()
x, y, w, h = None, None, None, None

# everything below happens in a loop
while True:
    # 0. which buttons did the user press?
    key = cv2.waitKey(1) & 0xFF
    if key == ord('l'):
        drone.land()  # L = land
    elif key == ord('t'):
        drone.takeoff()  # T = takeoff

    # 1. get one video frame from drone camera
    frame = drone.get_frame_read().frame

    # 2. detect an object on that frame
    x, y, w, h = detection.detect_biggest_apriltag(tag_detector, frame, tracker=tracker)
    #x, y, w, h = detection.detect_biggest_face(face_detector, frame, previous_xywh=(x, y, w, h), tracker=tracker)

    nx, ny, size = detection.to_normalized_x_y_size(frame, x, y, w, h, draw_box=True)
    cv2.imshow("drone video", frame)

    # 3. if the object is not detected, try again
    if nx is None:
        continue

    # 4. do we want the drone to move when it sees the object?
    up_down_velocity = 0
    forward_velocity = 0
    turn_velocity = 0
    roll_velocity = 0

    # when the object is too far to the left, be turning left
    if nx < -15:
        turn_velocity = -40

    # exercise 1: can you think of a way to turn the drone right when the object is too far to the right? (nx > 15)

    # exercise 2: can you think of a way to fly the drone up when the object is too far above? (ny > 20)

    # exercise 3: can you think of a way to fly the drone down when the object is too far below? (ny < -15)

    # exercise 4: can you think if a way to fly the drone forward when the object is right in front of us? (nx > -15 and nx < -15 and ny < 20 and ny > -15)

    drone.send_rc_control(roll_velocity, forward_velocity, up_down_velocity, turn_velocity)
