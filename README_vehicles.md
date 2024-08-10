# All examples here are in `simulation=True`
(you can set `simulation=False` for the code to run on real vehicle)

## Example 1 (courtesy of Eddy)

```python
import cv2
import pupil_apriltags as apriltags
import detection
import videocar


# what kind of objects can we detect? faces and tags
face_detector = cv2.CascadeClassifier('resources/haarcascade_frontalface_default.xml')
tag_detector = apriltags.Detector(families="tag36h11", quad_sigma=0.2)
tracker = detection.create_vit_tracker()


videocar.start(
    simulation=True,
    motor_directions=(-1, -1),
    video_direction=1,
    robot_hostname="localhost",  # if you want to use SSH tunnel (to go around firewall)
)

# the main loop
while True:
    # 1. get the video frame
    frame = videocar.get_video_frame()
    if frame is None:
        print("no video => trying again")
        continue  # no video frame

    # 2. detect object and display on the website
    #x, y, w, h = detection.detect_biggest_apriltag(tag_detector, frame, only_these_ids=[0, 1, 2, 3])
    x, y, w, h = detection.detect_biggest_face(face_detector, frame)
    videocar.display_web_video_frame(frame)

    cv2.imshow("videofeed", frame); cv2.waitKey(1)

    # 3. if no object detected, stop the car and continue back to getting a video frame
    if x is None:
        videocar.set_arcade_drive(-0.1, 0.15)
        print("no tag => slowly turning")
        continue

    # 4. if the object is there, calculate its center X (remember, the frame is 640 pixels wide)
    center = x + w / 2

    # 5. and follow the center of this object
    if center > 440:  # if object is on the right, turn right towards it
        videocar.set_arcade_drive(0.1, -0.15)
        print("turning right, because center =", center)

    elif center < 200:  # if object is on the left, turn left towards it
        videocar.set_arcade_drive(0.1, 0.15)
        print("turning left, because center =", center)

    else:  # otherwise the object is neither to the right, nor to the left -- we can go to it
        videocar.set_arcade_drive(0.0, 0.0)
        print("going forward, because center =", center)

```

## Example 2
We can extract the object-following code into a `follow_object()` function

```python
import cv2
import pupil_apriltags as apriltags
import detection
import videocar


# what kind of objects can we detect? faces and tags
face_detector = cv2.CascadeClassifier('resources/haarcascade_frontalface_default.xml')
tag_detector = apriltags.Detector(families="tag36h11", quad_sigma=0.2)
tracker = detection.create_vit_tracker()

# connect to the car
videocar.start(
    simulation=True,
    motor_directions=(-1, -1),
    video_direction=1,
    robot_hostname="localhost",  # if you want to use SSH tunnel (to go around firewall)
)


# a little function to follow an object
def follow_object(x, y, w, h):
    # calculate its center X (remember, the frame is 640 pixels wide)
    center = x + w / 2
    
    # and follow the center of this object
    if center > 440:  # if object is on the right, turn right towards it
        videocar.set_arcade_drive(0.1, -0.15)
        print("turning right, because center =", center)
    
    elif center < 200:  # if object is on the left, turn left towards it
        videocar.set_arcade_drive(0.1, 0.15)
        print("turning left, because center =", center)
    
    else:  # otherwise the object is neither to the right, nor to the left -- we can go to it
        videocar.set_arcade_drive(0.0, 0.0)
        print("going forward, because center =", center)


# the main loop
while True:
    # 1. get the video frame
    frame = videocar.get_video_frame()
    if frame is None:
        print("no video => trying again")
        continue  # no video frame

    # 2. detect object and display on the website
    #x, y, w, h = detection.detect_biggest_apriltag(tag_detector, frame, only_these_ids=[0, 1, 2, 3])
    x, y, w, h = detection.detect_biggest_face(face_detector, frame)
    videocar.display_web_video_frame(frame)

    cv2.imshow("videofeed", frame); cv2.waitKey(1)

    # 3. if no object detected, stop the car and continue back to getting a video frame
    if x is None:
        videocar.set_arcade_drive(-0.1, 0.15)
        print("no tag => slowly turning")
        continue

    # 4. call the function to follow the object
    follow_object(x, y, w, h)

```


## Example 3
This allows us to improve our object detection to "track the last detected"
```python
import cv2
import pupil_apriltags as apriltags
from time import time
import detection
import videocar


# what kind of objects can we detect? faces and tags
face_detector = cv2.CascadeClassifier('resources/haarcascade_frontalface_default.xml')
tag_detector = apriltags.Detector(families="tag36h11", quad_sigma=0.2)
tracker = detection.create_vit_tracker()

# connect to the car
videocar.start(
    simulation=True,
    motor_directions=(-1, -1),
    video_direction=1,
    robot_hostname="localhost",  # if you want to use SSH tunnel (to go around firewall)
)


# a little function to follow an object
def follow_object(x, y, w, h):
    # calculate its center X (remember, the frame is 640 pixels wide)
    center = x + w / 2

    # and follow the center of this object
    if center > 440:  # if object is on the right, turn right towards it
        videocar.set_arcade_drive(0.1, -0.15)
        print("turning right, because center =", center)

    elif center < 200:  # if object is on the left, turn left towards it
        videocar.set_arcade_drive(0.1, 0.15)
        print("turning left, because center =", center)

    else:  # otherwise the object is neither to the right, nor to the left -- we can go to it
        videocar.set_arcade_drive(0.0, 0.0)
        print("going forward, because center =", center)


# if we want to use tracking, we need these three variables
tracking = False
last_seen_time = 0
last_seen_x = None

# the main loop
while True:
    # 1. get the video frame
    frame = videocar.get_video_frame()
    if frame is None:
        print("no video => trying again")
        continue  # no video frame

    x, y, w, h = None, None, None, None

    # 2a. keep tracking the object on this video frame, if we were tracking it before
    if tracking:
        x, y, w, h = detection.update_tracker(tracker, frame)
        if x is not None:
            last_seen_time = time()
        elif time() > last_seen_time + 2:
            tracking = False  # if not seen for >2s, assume we lost it

    # 2b. and only if we do not see it with a tracker (x is None), try detecting it again
    if x is None:
        #x, y, w, h = detection.detect_biggest_apriltag(tag_detector, frame, only_these_ids=[0, 1, 2, 3])
        x, y, w, h = detection.detect_biggest_face(face_detector, frame)
        if x is not None:
            tracker.init(frame, (x, y, w, h))
            tracking = True

    videocar.display_web_video_frame(frame)
    cv2.imshow("videofeed", frame); cv2.waitKey(1)

    # 3. if no object detected, stop the car and continue back to getting a video frame
    if x is None:
        videocar.set_arcade_drive(-0.1, 0.15)
        print("no tag => slowly turning")
        continue

    follow_object(x, y, w, h)

```
