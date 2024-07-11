from flask import Flask, Response, request, json, render_template_string
from socket import gethostname
from time import time, sleep
from threading import Thread

import cv2
import pigpio
import atexit
import numpy as np

# these two lines must be found in /etc/rc.local on host "raspberrypi"
# (also socat must be installed, and pigpiod must be running as service)
"""
/usr/bin/socat tcp-listen:8887,reuseaddr,fork tcp:localhost:8888 &
/home/{username}/run_camera.sh &
"""

#, where the /home/{username}/run_camera.sh has mode 777 and contains
"""
#!/usr/bin/bash

while true;
do
  echo "Starting camera at `date` ..." > /var/log/libcamera-vid.log
  libcamera-vid -t 0 --codec mjpeg --framerate 20 --width 640 --height 480 --listen -o tcp://0.0.0.0:8000 >> /var/log/libcamera-vid.log 2>&1
done
"""


# actual interfaces


def set_arcade_drive(forward_speed, right_turn_speed):
    assert robot_container is not None, "videotank.start() must be called first"
    robot_container.set_arcade_drive(forward_speed, right_turn_speed)


def set_right_motor(speed):
    assert robot_container is not None, "videotank.start() must be called first"
    robot_container.set_right_motor(speed)


def set_left_motor(speed):
    assert robot_container is not None, "videotank.start() must be called first"
    robot_container.set_left_motor(speed)


def stop_all_motors():
    assert robot_container is not None, "videotank.start() must be called first"
    robot_container.stop_all_motors()


def display_video_frame(f, comment=None):
    assert robot_container is not None, "videotank.start() must be called first"
    robot_container.display_video_frame(f, comment)


def get_video_frame():
    assert robot_container is not None, "videotank.start() must be called first"
    return robot_container.get_video_frame()


def get_clicks():
    assert robot_container is not None, "videotank.start() must be called first"
    return robot_container.get_clicks()


def get_buttons():
    assert robot_container is not None, "videotank.start() must be called first"
    return robot_container.get_buttons()


def start(simulation=False, robot_hostname=None, motor_directions=(1, 1,), video_direction=1):
    global in_simulation, robot_container, webserver_thread
    assert in_simulation is None, "videotank.start() called twice"
    assert webserver_thread is None, "somehow starting webserver twice"

    webserver_thread = Thread(target=_run_webserver)
    webserver_thread.daemon = True
    webserver_thread.start()

    if simulation:
        in_simulation = True
        robot_container = RobotContainer(
            motor_directions=motor_directions,
            video_direction=video_direction,
            hostname=None)
        # no robot hostname, if running in simulation
    else:
        in_simulation = False
        if robot_hostname == "localhost":
            print(f"videocar.start(robot_hostname='localhost'): did you also start an SSH tunnel? (ssh -L 8887:{HOSTNAME}:8888 -L 8000:{HOSTNAME}:8000 cupcake@raspberrypi)")
        robot_container = RobotContainer(
            motor_directions=motor_directions,
            video_direction=video_direction,
            hostname=robot_hostname or HOSTNAME)

    # send motors a stop signal for 0.1s
    print("sending motors a stop signal")
    set_right_motor(0.0)
    set_left_motor(0.0)
    sleep(0.1)

    # fast-forward the camera to the latest frame
    print("camera {}".format("CONNECTED" if robot_container.camera.isOpened() else "NOT CONNECTED"))
    if robot_container.camera.isOpened():
        frame = robot_container.get_video_frame()
        print("obtained a frame from camera: {}".format(frame.shape if frame is not None else "(empty)"))


def _to_duty_cycle(setpoint):
    duty_cycle = ZERO_THROTTLE + (FULL_FORWARD - ZERO_THROTTLE) * setpoint
    return int(0.5 + duty_cycle)


def _run_webserver():
    webserver.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)


def _gen_frames():
    while True:
        if robot_container is None or robot_container.frame_to_display is None:
            sleep(0.25)
            continue
        success, jpg = cv2.imencode('.jpg', robot_container.frame_to_display)
        encoded = b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpg.tobytes() + b'\r\n'
        yield encoded


# we can maybe later have more than one robot_container, but we only have one webserver
webserver = Flask(__name__)
webserver_thread = None

@webserver.route('/')
def index():
    return render_template_string("""
<body>
<div class="container">
    <div class="row">
        <div class="col-lg-8  offset-lg-2">
            <img id="videobar" style="cursor: crosshair" src="{{ url_for('video_feed') }}" width="640">
        </div>
    </div>
</div>

{% autoescape false %}
{{ button_code }}
{% endautoescape %}

<p id="coordinates"></p>

<script>
var mouseDownX = null, mouseDownY = null;

function saveMouseDown(event) {
  mouseDownX = event.offsetX;
  mouseDownY = event.offsetY;
}

function sendSelectedRegion(event) {
  // Get the coordinates of the click relative to the document.
  var mouseUpX = event.offsetX;
  var mouseUpY = event.offsetY;
  var w = Math.abs(mouseDownX - mouseUpX); // width
  var h = Math.abs(mouseDownY - mouseUpY); // height
  var x = Math.min(mouseDownX, mouseUpX);
  var y = Math.min(mouseDownY, mouseUpY);
  //document.getElementById("coordinates").innerHTML = "x: " + x + ", y: " + y + ", w: " + w + " h: " + h;
  response = fetch("{{ url_for('click') }}", {method:"POST", body: JSON.stringify({ x: x, y: y, w: w, h: h })});
}

function sendButtonClick(text) {
  response = fetch("{{ url_for('button') }}", {method:"POST", body: JSON.stringify({ text: text })});
}

// add event listeners for clicks and drags
document.getElementById('videobar').ondragstart = function() { return false; };
document.getElementById("videobar").addEventListener("mousedown", saveMouseDown);
document.getElementById("videobar").addEventListener("mouseup", sendSelectedRegion);
document.getElementById("videobar").addEventListener("touchstart", saveMouseDown);
document.getElementById("videobar").addEventListener("touchend", sendSelectedRegion);

</script>
</body>
""", button_code="\n".join(
        f"<button onclick=\"sendButtonClick('{btn}')\"> {btn}</button>" for btn in ["follow", "stop"]
    ))


@webserver.route('/video_feed')
def video_feed():
    return Response(_gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@webserver.route('/click', methods=['GET', 'POST'])
def click():
    try:
        point = json.loads(request.get_data())
        robot_container.points_clicked.append(point)
    except:
        print("WARNING: got a click, but could not decode it")
    return ""


@webserver.route('/button', methods=['GET', 'POST'])
def button():
    try:
        pressed = json.loads(request.get_data())
        robot_container.buttons_clicked.append(pressed["text"])
    except:
        print("WARNING: got a click, but could not decode it")
    return ""


# constants
RIGHT_MOTOR_PIN = 12
LEFT_MOTOR_PIN = 13
PWM_FREQUENCY = 50
ZERO_THROTTLE = 75000
FULL_FORWARD = 100000
HOSTNAME = 'raspberrypi'
THIS_HOST = gethostname()

GREEN = (0, 255, 127)
WHITE = (255, 255, 255)
FPS_WINDOW_SECONDS = 5.0  # measure FPS over this window of time


# state
class RobotContainer:

    def __init__(self, hostname, motor_directions=(1, 1), video_direction=1):
        assert len(motor_directions) == 2, "we have two motors and must have two directions"
        assert motor_directions[0] != 0 and motor_directions[1] != 0, f"{motor_directions}"
        self.motor_directions = (np.sign(motor_directions[0]), np.sign(motor_directions[1]))
        self.video_direction = video_direction
        self.right_speed = 0.0
        self.left_speed = 0.0
        self.recent_fps = 0.0
        self.last_get_video_frame_time = 0.0
        if hostname is None:
            self.camera = cv2.VideoCapture(0)
            print("pins not connected, because we are in simulation")
            self.pins = None
        else:
            self.pins = pigpio.pi() if THIS_HOST == hostname else pigpio.pi(hostname, 8887)
            print("pins {}".format("CONNECTED" if self.pins.connected else "NOT CONNECTED"))
            self.camera = cv2.VideoCapture("tcp://" + hostname + ":8000")
            assert self.pins.connected, "pins were not connected successfully"
        self.frame_to_display = None
        self.points_clicked = []
        self.buttons_clicked = []
        atexit.register(self.stop_all_motors)

    def set_left_motor(self, speed):
        self.left_speed = np.clip(speed, -1.0, +1.0)
        if self.pins is not None:
            signal = self.left_speed * self.motor_directions[0]
            return self.pins.hardware_PWM(LEFT_MOTOR_PIN, PWM_FREQUENCY, _to_duty_cycle(signal))

    def set_right_motor(self, speed):
        self.right_speed = np.clip(speed, -1.0, +1.0)
        if self.pins is not None:
            signal = self.right_speed * self.motor_directions[1]
            return self.pins.hardware_PWM(RIGHT_MOTOR_PIN, PWM_FREQUENCY, _to_duty_cycle(signal))

    def set_arcade_drive(self, forward_speed, right_turn_speed):
        # make sure the speeds are realistic
        # (the left and right motor speeds should not exceed 1.0 in absolute value,
        #  and forward speed must be reduced if a sharper turn speed is requested)
        right_turn_speed = np.clip(right_turn_speed, -1.0, +1.0)
        max_forward_speed = 1 - abs(right_turn_speed)
        forward_speed = np.clip(forward_speed, -max_forward_speed, max_forward_speed)
        # now set those realistic speeds
        self.set_left_motor(forward_speed + right_turn_speed)
        self.set_right_motor(forward_speed - right_turn_speed)

    def stop_right_motor(self):
        self.set_right_motor(0)

    def stop_left_motor(self):
        self.set_left_motor(0)

    def stop_all_motors(self):
        self.stop_left_motor()
        self.stop_right_motor()
        if self.pins is not None:  # then, if supported, send a hard stop signal (no pulses)
            print("mandatory 0.1s pause when stopping all motors")
            sleep(0.1)  # but let the regular stop signal get there first
            self.pins.hardware_PWM(LEFT_MOTOR_PIN, 0, 0)
            self.pins.hardware_PWM(RIGHT_MOTOR_PIN, 0, 0)

    def display_video_frame(self, frame, comment):
        self.frame_to_display = frame
        text = f"mtr%: {int(100 * self.left_speed)} {int(100 * self.right_speed)}"
        text += f", cam: {int(self.recent_fps)} fps"
        cv2.putText(self.frame_to_display, text, (5, 30), cv2.FONT_HERSHEY_DUPLEX, 1, WHITE, 1)
        if comment is not None:
            cv2.putText(self.frame_to_display, comment, (5, frame.shape[0] - 10), cv2.FONT_HERSHEY_DUPLEX, 0.5, WHITE, 1)


    def get_clicks(self):
        result = self.points_clicked
        self.points_clicked = []
        return result


    def get_buttons(self):
        result = self.buttons_clicked
        self.buttons_clicked = []
        return result


    def get_video_frame(self):
        # update the fps counter
        now = time()
        dt = (now - self.last_get_video_frame_time) / FPS_WINDOW_SECONDS
        self.recent_fps = self.recent_fps / (1 + dt) + 1 / FPS_WINDOW_SECONDS
        self.last_get_video_frame_time = now

        # if in simulation, do not bother fast-forwarding to the latest frame
        if in_simulation:
            self.camera.grab()
            success, frame = self.camera.retrieve()
            if not success:
                return None
            if self.video_direction == -1:
                frame = cv2.flip(frame, -1)  # 180 degree flip (if camera is installed upside down)
            return frame

        # otherwise, catch up by discarding the old frames sitting in the queue
        t = time()
        while True:
            self.camera.grab()
            after = time()
            if after - t > 0.010:
                break  # if this took us more than 10ms to get next frame, it was fresh
            t = after
        success, frame = self.camera.retrieve()  # and decode just that last frame
        if success:
            if self.video_direction == -1:
                frame = cv2.flip(frame, -1)  # 180 degree flip (if camera is installed upside down)
            return frame


robot_container = None
in_simulation = None

