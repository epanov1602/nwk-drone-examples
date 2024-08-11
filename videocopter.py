from djitellopy import Tello
import numpy as np

import detection


def drone_follow_object_pids(drone: Tello, frame, bbox, target_width=0.2, kp_fwd=6.0, kp_turn=90, kp_updown=150):
    """
    Sets Tello speed to follow the detected object, using a very primitive PID logic
    :param drone: a djitellopy.Tello
    :param frame: frame of the video
    :param bbox: bounding box of the object to follow, on the frame
    :param target_width: how wide should the object be for the drone to stop approaching it
    :param kp_turn: kP gain for turns
    :param kp_fwd: kP gain for forward movement
    :param kp_updown: kP gain for up/down movement
    :return: None
    """
    # first of all, convert all pixel coordinates to relative coordinates:
    #  relative_x=-0.5 means object is all the way to the left, +0.5 means all the way to the right, 0 = middle
    #  relative_y=-0.5 means object is all the way to the bottom, +0.5 means all the way to the top, 0 = center
    x, y, w, h = bbox
    relative_x, relative_y, relative_width = detection.to_relative_xyw(frame, x, y, w, h)

    # turn right if X>0, turn left if X<0
    yaw_speed = relative_x * kp_turn
    left_speed = relative_x * kp_turn

    # go up if Y>0, go down if Y<0
    up_speed = relative_y * kp_updown

    forward_speed = 0
    if relative_width < 0.01 * target_width:
        forward_speed = 100  # full forward, we are very far from our object
    else:
        # if relative_width > target, we are too close => move back (for example, speed=-35 if relative_width=100%)
        # if relative_width < target, we are too far => move forward (for example, speed=96 if relative_width=5%)
        forward_speed = kp_fwd * (1 / relative_width - 1 / target_width)

    # last touches:
    #  - if the object is too far to the side of the video (right or left), going fast is not allowed
    if relative_x < -0.25 or relative_x > 0.25:
        forward_speed = min([25, forward_speed])
    #  - if going back, do it very aggressively to avoid collision
    if forward_speed < 0:
        forward_speed = forward_speed * 2

    drone.send_rc_control(
        int(np.clip(left_speed, -50, +50)),
        int(np.clip(forward_speed, -100, +100)),
        int(np.clip(up_speed, -50, +50)),
        int(np.clip(yaw_speed, -100, +100))
    )


def drone_follow_object_bang(drone: Tello, frame, bbox, target_width=0.2, max_up_speed=50, max_left_speed=40, max_fwd_speed=90):
    """
    Sets Tello speed to follow the detected object, using a very primitive PID logic
    :param drone: a djitellopy.Tello
    :param frame: frame of the video
    :param bbox: bounding box of the object to follow, on the frame
    :param target_width: how wide should the object be for the drone to stop approaching it
    :return: None
    """
    # first of all, convert all pixel coordinates to relative coordinates:
    #  relative_x=-0.5 means object is all the way to the left, +0.5 means all the way to the right, 0 = middle
    #  relative_y=-0.5 means object is all the way to the bottom, +0.5 means all the way to the top, 0 = center
    x, y, w, h = bbox
    relative_x, relative_y, relative_width = detection.to_relative_xyw(frame, x, y, w, h)

    # turn right if X>0, turn left if X<0
    yaw_speed, left_speed = 0, 0
    if relative_x > 0.25:
        yaw_speed, left_speed = max_left_speed, max_left_speed
    if relative_x < -0.25:
        yaw_speed, left_speed = -max_left_speed, -max_left_speed

    # go up if Y>0, go down if Y<0
    up_speed = 0
    if relative_y > 0.25:
        up_speed = max_up_speed
    if relative_y < -0.25:
        up_speed = -max_up_speed

    forward_speed = 0
    if relative_width < 0.5 * target_width:
        forward_speed = max_fwd_speed  # full forward, we are very far from our object
    if relative_width > 1.5 * target_width:
        forward_speed = -max_fwd_speed

    drone.send_rc_control(
        int(np.clip(left_speed, -50, +50)),
        int(np.clip(forward_speed, -100, +100)),
        int(np.clip(up_speed, -100, +100)),
        int(np.clip(yaw_speed, -100, +100))
    )

