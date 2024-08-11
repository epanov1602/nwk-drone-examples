from djitellopy import Tello

import pygame
pygame.init()

# our joystick will be called "j0"
j0 = pygame.joystick.Joystick(0)

drone = Tello()
drone.connect()

# constants
kP_forward = 70.0

while True:
    joystick_input = pygame.event.get()
    if joystick_input:
        # first, see if there were buttons pressed (set == 1)
        button_a, button_b, button_y = j0.get_button(0), j0.get_button(1), j0.get_button(3)
        if button_y == 1:
            drone.takeoff()
        elif button_a == 1:
            drone.land()

        # second, if the drone is flying, we can take the axis input to control its speed
        if drone.is_flying:
            axis3 = j0.get_axis(3)  # axis can be: 0, 1, 2, 3

            forward_speed = int(axis3 * kP_forward)
            # ^^ convert axis value like 0.21 to speed like 15 (or axis value 0.42 to speed like 30)

            drone.send_rc_control(0, forward_speed, 0, 0)
