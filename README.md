# Newark Drone Coders, examples 1

## Getting started

* First you need to download and install
  * Git: https://git-scm.com/downloads
  * PyCharm Community Edition: https://www.jetbrains.com/pycharm/download/

Most professional python developers use PyCharm or VSCode, we'll be using PyCharm).



* Then, clone (download) this code onto your computer by doing this
![guide/git-clone.png](guide/git-clone.png)

and please use the GitHub URL of this project: `git@github.com:epanov1602/nwk-drone-examples.git`



* When the code download ("git clone") is completed, you will see code files (modules) organized this way in your PyCharm:
![guide/project.png](guide/project.png)

^^ click on `requirements.txt`


* Once the requirements file opens, right-click on any of the lines in it (for example, `djitellopy2`) and you'll be offered to install all the packages that are needed for this code to work -- you can agree and install
![guide/requirements.png](guide/requirements.png)


* After that installation is done, you should be in good shape to run this drone code!


## Running the examples

* `car_main.py`, `copter_main.py` and `laptop_main.py` are modules (code files) that you can run in order to
  * drive a car with camera
  * fly a copter with camera
  * just play with your laptop camera

* we will be changing them in order to accomplish different things

* other modules contain various functions that are handy to have (for example, recognizing an AprilTag, or driving)


## Example 1D (flying the drone with buttons)

In `copter_main.py` replace everything with this code:

```
from djitellopy import Tello
import cv2

drone = Tello()
drone.connect()
drone.streamon()


while True:
    # if user pressed one of these buttons, do as said
    key = cv2.waitKey(1) & 0xFF
    if key == ord('l'):
        drone.land()  # L = land
    elif key == ord('t'):
        drone.takeoff()  # T = takeoff
    elif key == ord('w'):
        drone.move_forward(50)  # 50 centimeters
    elif key == ord('s'):
        drone.move_back(50)  # 50 centimeters

    # get a video frame and show it
    frame = drone.get_frame_read().frame
    if frame is None:
        continue  # try again, if nothing was read
    frame_width = frame.shape[1]
    cv2.imshow('drone video', frame)

if __name__ == "__main__":
    main()

```

## Example 1C (driving the car with buttons)

In `car_main.py` replace everything with this code:

```
import cv2
import videocar

videocar.start(simulation=False, motor_directions=(-1, -1), video_direction=-1)

while True:
    key = cv2.waitKey(1) & 0xFF
    if key == ord('a'):
        videocar.set_arcade_drive(forward_speed=0.3, right_turn_speed=-1)
    elif key == ord('d'):
        videocar.set_arcade_drive(forward_speed=0.3, right_turn_speed=1)
    elif key == ord(' '):
        videocar.set_arcade_drive(forward_speed=0, right_turn_speed=0)

    # get a video frame
    frame = videocar.get_video_frame()
    if frame is None:
        continue  # no frame

    # show it in a window
    cv2.imshow("car", frame)
    videocar.display_video_frame(frame)
```

## Example 2D (chasing an AprilTag with drone)

In `copter_main.py` replace everything with this code:

```
from djitellopy import Tello

import cv2
import pupil_apriltags as apriltags
from time import time

import detection
import videocopter

face_detector = cv2.CascadeClassifier('resources/haarcascade_frontalface_default.xml')
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

        ## WARNING: it is better to uncomment the code below to use tracker (so you don't lost track of object)
        #if time_last_seen != 0:
        #    x, y, w, h = detection.update_tracker(tracker, frame)
        #    if x is not None:
        #        time_last_seen = time()  # if track is not lost, update the "last time seen"
        #    elif time() > time_last_seen + 1.0:
        #        time_last_seen = 0  # if track was lost for more than 1s, assume we can no longer track it

        # -- detect a new object, if never saw it (or lost it)
        if x is None:
            x, y, w, h = detection.detect_biggest_apriltag(tag_detector, frame)
            # x, y, w, h = utils.detect_biggest_face(face_detector, frame)
            # x, y, w, h = utils.detect_yolo_object(model, frame, valid_classnames={"sports ball"}, lowest_conf=0.3)

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

```

* Try finding the "WARNING" in the code and uncommenting the tracker -- object tracking will become better

* Can you find a way to detect faces instead of AprilTag, using this code?
