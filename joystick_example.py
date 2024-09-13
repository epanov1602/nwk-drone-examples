MAXIMUM_FORWARD_SPEED = 70  # can be as high as 100
MAXIMUM_TURN_SPEED = 100  # can be as high as 100

import cv2
from djitellopy import tello
import pygame; pygame.init()

drone = tello.Tello()
drone.connect()
drone.streamon()
print(f"battery: {drone.get_battery()}")

j0 = pygame.joystick.Joystick(0)

while True:
    frame = drone.get_frame_read().frame
    cv2.imshow("drone video", frame)
    cv2.waitKey(1)

    joystick_input = pygame.event.get()
    if joystick_input:
        y_button = j0.get_button(3)
        a_button = j0.get_button(0)

        if y_button: # did someone press "Y"? take off!
            drone.takeoff()
            drone.send_rc_control(0, 0, 0, 0)  # set speed to zero after takeoff (hang in one point)
            continue

        if a_button: # did someone press "A"? land!
            drone.land()
            continue

        if drone.is_flying:
            forward_speed = MAXIMUM_FORWARD_SPEED * -j0.get_axis(3)
            up_down_speed = MAXIMUM_FORWARD_SPEED * -j0.get_axis(1)
            side_roll_speed = MAXIMUM_TURN_SPEED * j0.get_axis(2)
            yaw_turn_speed = MAXIMUM_TURN_SPEED * j0.get_axis(0)
            drone.send_rc_control(int(side_roll_speed), int(forward_speed), int(up_down_speed), int(yaw_turn_speed))
