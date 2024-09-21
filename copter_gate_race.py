import cv2
from djitellopy import tello

drone = tello.Tello()
drone.connect()

print(f"battery: {drone.get_battery()}")

drone.takeoff()
drone.move_forward(200)
drone.rotate_clockwise(90)
drone.move_forward(100)

drone.land()
