from djitellopy import Tello

import cv2
import pupil_apriltags as apriltags
#from ultralytics import YOLO

from time import time

import detection
import videocopter

# what kind of objects can we detect?
face_detector = cv2.CascadeClassifier('resources/haarcascade_frontalface_default.xml')
#model = YOLO("resources/yolov8s.pt")  # model to detect common objects like "person", "car", "cellphone" (see "COCO")
tag_detector = apriltags.Detector(families="tag36h11", quad_sigma=0.2)
tracker = detection.create_vit_tracker()


drone = Tello()
drone.connect()
drone.streamon()


def main():
    last_seen_x = None
    time_last_seen = 0

    while True:
        # 0. if user pressed one of these buttons, obey
        key = cv2.waitKey(1) & 0xFF
        if key == ord('l'):
            drone.land()  # L = land
        elif key == ord('t'):
            drone.takeoff()  # T = takeoff
        elif key == ord('w'):
            drone.move_forward(50)  # 50 centimeters
        elif key == ord('s'):
            drone.move_back(50)  # 50 centimeters


        # 1. read one video frame from the camera
        frame = drone.get_frame_read().frame
        if frame is None:
            continue  # try again, if nothing was read
        frame_width = frame.shape[1]

        # 2. locate the object
        x, y, w, h = None, None, None, None

        # -- if saw it before and didn't lose it, just track the existing object by updating the tracker
        #if time_last_seen != 0:
        #    x, y, w, h = detection.update_tracker(tracker, frame)
        #    if x is not None:
        #        time_last_seen = time()  # if track is not lost, update the "last time seen"
        #    elif time() > time_last_seen + 1.0:
        #        time_last_seen = 0  # if track was lost for more than 1s, assume we can no longer track it

        # -- detect a new object, if never saw it (or lost it)
        if x is None:
            x, y, w, h = detection.detect_biggest_apriltag(tag_detector, frame)
            # x, y, w, h = detection.detect_biggest_face(face_detector, frame)
            # x, y, w, h = detection.detect_yolo_object(model, frame, valid_classnames={"sports ball"}, lowest_conf=0.3)

            if x is not None:  # if detected something, reset the tracker with this new object to track
                tracker.init(frame, (x, y, w, h))
                time_last_seen = time()

        # 3. make decisions
        status = ""
        if x is not None:
            # if object is seen, set speed towards it
            status = "CHASING"
            videocopter.drone_follow_object_pids(drone, frame, bbox=(x, y, w, h))
            last_seen_x = x
        elif last_seen_x is not None:
            # if not seen, try to slowly turn (ideally, in the direction where object was last seen)
            status = "SEEKING"
            seek_turn_speed = +50  # seek to the right by default
            if last_seen_x is not None and last_seen_x < frame_width / 2:
                seek_turn_speed = -50  # seek left if last saw it on the left
            drone.send_rc_control(0, 0, 0, seek_turn_speed)

        # 4. print the status info on the video frame, and then show that frame
        status = f"bat: {drone.get_battery()}%, alt: {drone.get_distance_tof()}, width: {w}, " + status
        cv2.putText(frame, status, (5, 25), cv2.FONT_HERSHEY_PLAIN, 2, detection.GREEN, 2)
        cv2.imshow('drone video', frame)


if __name__ == "__main__":
    main()
