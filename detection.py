import typing

import cv2
import time
import numpy as np


GREEN = (127, 255, 0)
WHITE = (255, 255, 255)
RED = (0, 0, 255)
PURPLE = (255, 0, 255)
BLUE = (255, 0, 127)


COCO_CLASSNAMES = [
    'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat', 'traffic light', 'fire hydrant',
    'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe',
    'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat',
    'baseball glove', 'skateboard', 'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl',
    'banana', 'apple', 'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch', 'potted plant',
    'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
    'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
]



def detect_biggest_apriltag(detector, frame, only_these_ids=None, tracker=None):
    return detect_or_track(frame, tracker, lambda: _detect_biggest_apriltag(detector, frame, only_these_ids))

def detect_biggest_face(face_detector, frame, previous_xywh=None, tracker=None):
    return detect_or_track(frame, tracker, lambda: _detect_biggest_face(face_detector, frame, previous_xywh=previous_xywh))

def detect_yolo_object(yolo_model, frame, valid_classes=("person", "car"), lowest_conf=0.4, tracker=None):
    return detect_or_track(frame, tracker, lambda: _detect_yolo_object(yolo_model, frame, valid_classes, lowest_conf))


class TrackerState(object):
    def __init__(self,
                 tracker: cv2.TrackerVit,
                 display_confidence: bool = True,
                 tracker_reinit_interval: int = 40,
                 tracker_max_frames_without_object: int = 40,
                 tracker_lowest_allowed_score: float = 0.6):
        assert tracker is not None
        self.tracker = tracker
        self.tracking = False
        self.time_last_seen = 0
        self.time_last_reinit = 0
        self.frame_count = 0
        self.tracker_comments = None
        self.full_detection_reason = None
        self.display_confidence = display_confidence
        self.tracker_reinit_interval = tracker_reinit_interval
        self.tracker_max_frames_without_object = tracker_max_frames_without_object
        self.tracker_lowest_allowed_score = tracker_lowest_allowed_score

    def init(self, frame, bbox):
        self.tracker.init(frame, bbox)
        self.time_last_seen = self.frame_count
        self.time_last_reinit = self.frame_count
        self.tracking = True

    def update(self, frame):
        self.frame_count += 1

        if not self.tracking:
            return False, (None, None, None, None)

        x, y, w, h, cmt = update_tracker(self.tracker, frame, lowest_allowed_score=self.tracker_lowest_allowed_score)
        reason = "missing"
        if x is not None:
            self.time_last_seen = self.frame_count
            reason = None
        if self.frame_count >= self.time_last_reinit + self.tracker_reinit_interval:
            self.time_last_reinit = self.frame_count
            reason = "tracker_reinit_interval"
        if self.frame_count > self.time_last_seen + self.tracker_max_frames_without_object:
            self.tracking = False
            reason = "tracker_max_frames_without_object"
        self.tracker_comments = cmt
        self.full_detection_reason = reason
        can_skip_full_detection = reason is None
        return can_skip_full_detection, (x, y, w, h)


def create_vit_tracker(model_file="resources/object_tracking_vittrack_2023sep.onnx") -> cv2.TrackerVit:
    """
    Create a tracker that uses VIT
    """
    params = cv2.TrackerVit.Params()
    params.net = model_file
    return cv2.TrackerVit.create(params)


def update_tracker(tracker, frame, lowest_allowed_score=0.6):
    """
    Update a tracker (with a new videoframe), assuming that the tracker has been initialized to track something
    :param tracker: the tracker to update
    :param frame: new video frame
    :param lowest_allowed_score: if the tracker confidence score is lower than this, do not use its output
    :return: bounding box in format (x, y, w, h), or if track is lost then (None, None, None, None)
    """
    # will the tracker give us the updated bounding box?
    located, (tx, ty, tw, th) = tracker.update(frame)
    if located and tracker.getTrackingScore() >= lowest_allowed_score:

        # if tracking almost full screen now, assume that the tracker diverged
        frame_width, frame_height = frame.shape[1], frame.shape[0]

        # do we see any problems with the detection?
        comments = None
        if th > 0.75 * frame_height or tw > 0.75 * frame_width:
            comments = "trk_error: diverged"  # looks too big, our tracker has diverged
        else:
            comments = "trk_conf: {:.2}".format(tracker.getTrackingScore())
            return tx, ty, tw, th, comments

    # otherwise return (None, None, None, None)
    return None, None, None, None, None


def _detect_biggest_apriltag(detector, frame, only_these_ids=None):
    # make a grayscale image, so apriltags can be found on it
    grayscale = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    april_tags = detector.detect(grayscale)

    if len(april_tags) > 0:
        biggest_tag_size = 0
        boxes = []

        # put all boxes into the list
        for tag in april_tags:
            contour = tag.corners.astype(int)
            x, y, w, h = cv2.boundingRect(contour)
            id_location = int(x + w - 10), int(y - 10)
            cv2.polylines(frame, [contour], isClosed=True, color=BLUE, thickness=10)
            cv2.putText(frame, str(tag.tag_id), id_location, cv2.FONT_HERSHEY_SIMPLEX, 1, BLUE, thickness=2)
            if only_these_ids is not None and tag.tag_id not in only_these_ids:
                continue  # skip, because we are only supposed to look at tags with `only_these_ids`
            size = max([w, h])
            biggest_tag_size = max([biggest_tag_size, size])
            boxes.append((x, y, w, h))

        # return the biggest box
        for (x, y, w, h) in boxes:
            size = max([w, h])
            if size == biggest_tag_size:
                return x, y, w, h

    # if nothing was found, return None, None, None, None
    return None, None, None, None


def detect_or_track(frame, tracker: typing.Union[TrackerState, None], detector):
    # 1. try using tracker
    skip_detection = False
    tx, ty, tw, th = None, None, None, None
    if frame is None:
        return tx, ty, tw, th
    if tracker is not None:
        skip_detection, (tx, ty, tw, th) = tracker.update(frame)

    # 2. if this didn't work perfectly, re-detect
    if not skip_detection:
        dx, dy, dw, dh = detector()
        if dx is not None:
            tx, ty, tw, th = dx, dy, dw, dh
            if tracker is not None:
                tracker.init(frame, (dx, dy, dw, dh))
                _, (tx, ty, tw, th) = tracker.update(frame)

    # 3. if we must explain ourselves, do it now
    if tracker.display_confidence and tracker.tracker_comments:
        text = tracker.tracker_comments
        location = (int(tx) + 10, int(ty + th) + 15)
        cv2.putText(frame, text, location, cv2.FONT_HERSHEY_SIMPLEX, 0.5, PURPLE, 2)

    return tx, ty, tw, th


def _detect_biggest_face(face_detector, frame, draw_boxes=False, previous_xywh=None):
    """
    Use HAAR cascade detector to detect faces (picks the widest one, if many found)
    :param frame: a video frame, color or grayscale
    :param face_detector: cascade face detector
    :return: (x, y, w, h) bounding box or (None, None, None, None)
    """
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_detector.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=9)
    if previous_xywh is not None and previous_xywh[0] is None: previous_xywh = None

    biggest_w = 0  # this will be the width of the biggest face
    nearest_distance = None
    biggest_face = None
    nearest_face = None
    for index, (x, y, w, h) in enumerate(faces):
        if w > biggest_w:
            biggest_w = w
            biggest_face = x, y, w, h
        if previous_xywh is not None:
            px, py, pw, ph = previous_xywh
            distance = abs((x + w * 0.5) - (px + pw * 0.5)) + abs((y + 0.5 * h) - (py + ph * 0.5))
            if nearest_distance is None or distance < nearest_distance:
                nearest_distance = distance
                nearest_face = x, y, w, h

    if draw_boxes:
        for (x, y, w, h) in faces:
            # is this the biggest face seen? green box for it, otherwise red for smaller
            if w == biggest_w:
                cv2.rectangle(frame, (x, y), (x + w, y + h), GREEN, thickness=2)
            else:
                cv2.rectangle(frame, (x, y), (x + w, y + h), RED, thickness=2)

    if nearest_face is not None:
        return nearest_face
    if biggest_face is not None:
        return biggest_face
    # if there were no faces, return (None, None, None, None)
    return None, None, None, None


def _detect_yolo_object(yolo_model, frame, valid_classes=("person", "car"), lowest_conf=0.3):
    """
    Detect an object using a YOLO model (if multiple objects detected, picks the widest)
    :return: either (x, y, w, h) for the bounding box, or (None, None, None, None)
    """
    boxes = []
    biggest_width = 0
    results = yolo_model.predict(frame)

    for result in results:
        for bbox in result.boxes:
            class_name = result.names[int(bbox.cls[0])]
            conf = float(bbox.conf)
            x, y, x2, y2 = bbox.xyxy[0]
            if class_name in valid_classes and conf > lowest_conf:
                width, height = int(x2 - x), int(y2 - y)
                boxes.append([int(x), int(y), width, height])
                if width > biggest_width:
                    biggest_width = width
            text = "{}@{:.2}".format(class_name, conf)
            location = (int(x2) + 10, int(y) + 15)
            cv2.rectangle(frame, (int(x), int(y)), (int(x2), int(y2)), RED, 2)
            cv2.putText(frame, text, location, cv2.FONT_HERSHEY_SIMPLEX, 0.5, WHITE, 1)

    for (x, y, w, h) in boxes:
        if w == biggest_width:
            cv2.rectangle(frame, (x, y), (x + w, y + h), GREEN, 4)
            return x, y, w, h

    # otherwise, nothing found
    return None, None, None, None


def print_relative_xw(frame, x, y, w, h, color=BLUE):
    if x is not None and frame is not None:
        frame_width, frame_height = frame.shape[1], frame.shape[0]
        relative_x = (x + w // 2) / frame_width - 0.5  # can be between -0.5 and +0.5
        relative_width = w / frame_width
        text = f"x:{relative_x:.2}, w:{relative_width:.2}"
        cv2.putText(frame, text, (x, y - 10), cv2.FONT_HERSHEY_PLAIN, 0.9, color)


def to_normalized_x_y_size(frame, x, y, w, h, draw_box=False):
    """
    Convert the x, y, width and height of a detected object into [-0.5; +0.5] space,
    so robot can use them in navigation
    :param frame: frame from the camera (colored or grayscale), numpy ndarray
    :param x: X of the upper left corner of the detected object bounding box (in pixels)
    :param y: Y of the upper left corner of the detected object bounding box (in pixels)
    :param w: width of the detected object box (in pixels)
    :param h: height of the detected object box (in pixels)
    :param draw_box: annotate the frame with the bounding box
    :return: (X, Y, Size), with X and Y remapped to [-50; +50] space (X, Y = center of the box), Size between 0 and 100
    """
    if x is None:
        return None, None, None
    frame_width, frame_height = frame.shape[1], frame.shape[0]
    norm_x = 100 * ((x + w // 2) / frame_width - 0.5)  # can be between -0.5 and +0.5
    norm_y = 100 * ((y + h // 2) / frame_height - 0.5)  # can be between -0.5 and +0.5
    norm_size = 100 * max((w / frame_width, h / frame_height))
    norm_y = -norm_y  # flip the sign, so that when object is above Y is positive

    if draw_box:
        text = "nx:{:.0f}, ny:{:.0f}, size: {:.0f}".format(norm_x, norm_y, norm_size)
        cv2.putText(frame, text, (x, y - 10), cv2.FONT_HERSHEY_PLAIN, 1.0, WHITE, 2)
        cv2.rectangle(frame, (int(x), int(y)), (int(x + w), int(y + h)), GREEN, thickness=2)

    return norm_x, norm_y, norm_size

def to_relative_xyw_deprecated(frame, x, y, w, h):
    """
    Convert the x, y, width and height of a detected object into [-0.5; +0.5] space,
    so robot can use them in navigation
    :param frame: frame from the camera (colored or grayscale), numpy ndarray
    :param x: X of the upper left corner of the detected object bounding box (in pixels)
    :param y: Y of the upper left corner of the detected object bounding box (in pixels)
    :param w: width of the detected object box (in pixels)
    :param h: height of the detected object box (in pixels)
    :return: X, Y, W remapped to [-0.5; +0.5] space -- where X, Y are center of the object
    """
    if x is None:
        return None, None, None
    frame_width, frame_height = frame.shape[1], frame.shape[0]
    relative_x = (x + w // 2) / frame_width - 0.5  # can be between -0.5 and +0.5
    relative_y = (y + h // 2) / frame_height - 0.5  # can be between -0.5 and +0.5
    relative_y = -relative_y  # flip the sign, so that when object is above Y is positive
    relative_width = w / frame_width

    relative_y = relative_y - 0.1  # when copter is flying forward, nose is tilted down a bit, account for it
    return relative_x, relative_y, relative_width


def download_video(url):
    import tempfile
    import ytdlpy
    import os
    file = "./" + url.split("=")[-1].split("/")[-1] + ".mp4"
    if os.path.exists(file):
        return file
    with tempfile.TemporaryDirectory() as tempdir:
        ytdlpy.ytdlpy(tempdir, "mp4", url)
        files = [os.path.join(tempdir, f) for f in os.listdir(tempdir) if f.endswith(".mp4")]
        if len(files) == 0:
            return None
        os.rename(files[-1], file)
        return file
