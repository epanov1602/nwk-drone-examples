# simulated drone
drone_is_flying = False
drone_rc_control = (0, 0, 0, 0)

def drone_takeoff():
    global drone_is_flying
    if not drone_is_flying:
        drone_is_flying = True
        print("drone is flying")

def drone_land():
    global drone_is_flying
    if drone_is_flying:
        drone_is_flying = False
        print("drone has landed")

def drone_send_rc_control(leftright, fwd, updown, yaw):
    new_control = (leftright, forward_speed, updown, yaw)
    if new_control != drone_rc_control:
        print(f"drone rc: {leftright}(left), {fwd}(fwd), {updown}(up), {yaw}(yaw)")

# end of simulated drone


import pygame
pygame.init()

# our joystick will be called "j0"
j0 = pygame.joystick.Joystick(0)

# constants
kP_forward = 70.0

while True:
    joystick_input = pygame.event.get()
    if joystick_input:
        # first, see if there were buttons pressed (set == 1)
        button_a, button_b, button_y = j0.get_button(0), j0.get_button(1), j0.get_button(3)
        if button_y == 1:
            drone_takeoff()
        elif button_a == 1:
            drone_land()

        # second, if the drone is flying, we can take the axis input to control its speed
        if drone_is_flying:
            axis3 = j0.get_axis(3)  # axis can be: 0, 1, 2, 3

            forward_speed = int(axis3 * kP_forward)
            # ^^ "proportionally" (kP) convert axis value like 0.21 to speed like 15
            # (or axis value 0.42 to speed like 30)

            drone_send_rc_control(0, forward_speed, 0, 0)