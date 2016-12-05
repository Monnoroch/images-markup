from __future__ import print_function

from PIL import Image, ImageDraw, ImageFont
import modchooser
import argparse
import os
import cv2
import numpy as np

def all_files(dir):
    for subdir, _, files in os.walk(dir):
        for f in files:
            yield os.path.join(subdir, f)

def all_files_after(files, after_file):
    skip = after_file is not None
    for file in files:
        if skip:
            if file == after_file:
                skip = False
            continue
        yield file

def rect_to_square(rect):
    start_pos, end_pos = rect
    x, y = end_pos
    w = x - start_pos[0]
    h = y - start_pos[1]
    if abs(w) > abs(h):
        return (start_pos, (start_pos[0] + w, start_pos[1] + w))
    else:
        return (start_pos, (start_pos[0] + h, start_pos[1] + h))

def move_rect(rect, dx, dy, w, h):
    if rect[0][0] + dx < 0:
        dx += -(rect[0][0] + dx)
    if rect[1][0] + dx < 0:
        dx += -(rect[1][0] + dx)
    if rect[0][0] + dx > w:
        dx += w - (rect[0][0] + dx)
    if rect[1][0] + dx > w:
        dx += w - (rect[1][0] + dx)

    if rect[0][1] + dy < 0:
        dy += -(rect[0][1] + dy)
    if rect[1][1] + dy < 0:
        dy += -(rect[1][1] + dy)

    if rect[0][1] + dy > h:
        dy += h - (rect[0][1] + dy)
    if rect[1][1] + dy > h:
        dy += h - (rect[1][1] + dy)

    return (
        (rect[0][0] + dx, rect[0][1] + dy),
        (rect[1][0] + dx, rect[1][1] + dy)
    )

def between(x, x1, x2):
    return (x > x1 and x < x2) or (x < x1 and x > x2)

def is_inside_box(point, box):
    x, y = point
    (x1, y1), (x2, y2) = box
    return between(x, x1, x2) and between(y, y1, y2)

class Editor(object):
    def __init__(self, file, output, window_name):
        self.file = file
        self.output = output
        self.window_name = window_name
        self.image = None
        self.rects = []
        self.start_pos = None
        self.start_pos_move = None
        self.selection = None
        self.start_rect_move = None

    def load(self):
        self.image = cv2.imread(self.file, 0)
        if self.image is None:
            raise ValueError("Could not load image " + self.file)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
        return self

    def _get_rect(self, point):
        for i in range(0, len(self.rects)):
            if is_inside_box(self.start_pos_move, self.rects[i]):
                return i
        return None

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if self.start_pos is not None:
                raise ValueError("Things are bad. Left button down had been called twice without button up.")
            self.start_pos = (x, y)
            self.selection = rect_to_square((self.start_pos, self.start_pos))
        elif event == cv2.EVENT_LBUTTONUP:
            if self.start_pos is None:
                raise ValueError("Things are bad. Left button up happened before button down.")
            self.rects.append(rect_to_square((self.start_pos, (x, y))))
            self.selection = None
            self.start_pos = None
        elif event == cv2.EVENT_RBUTTONDOWN:
            if self.start_pos_move is not None:
                raise ValueError("Things are bad. Right button down had been called twice without button up.")
            self.start_pos_move = (x, y)
            rect_num = self._get_rect(self.start_pos_move)
            if rect_num is None:
                print("Trying to move an unexisting rect.")
                return
            self.start_rect_move = self.rects[rect_num]
            self.rects = self.rects[:rect_num] + self.rects[rect_num+1:]
            self.selection = self.start_rect_move
        elif event == cv2.EVENT_RBUTTONUP:
            if self.start_pos_move is None:
                print("Things are bad. Right button up happened before button down.")
                return
            start_pos_move = self.start_pos_move
            self.start_pos_move = None
            if self.start_rect_move is None:
                # This is not an exceptoion because of right click + d combination.
                print("Trying to move an unexisting rect.")
                return
            self.rects.append(move_rect(self.start_rect_move, x - start_pos_move[0], y - start_pos_move[1], self.image.shape[1], self.image.shape[0]))
            self.selection = None
            self.start_rect_move = None
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.start_pos is not None:
                self.selection = rect_to_square((self.start_pos, (x, y)))
            if self.start_pos_move is not None:
                if self.start_rect_move is None:
                    print("Trying to move an unexisting rect.")
                    return
                self.selection = move_rect(self.start_rect_move, x - self.start_pos_move[0], y - self.start_pos_move[1], self.image.shape[1], self.image.shape[0])
        else:
            # Ignore all other events
            return
        self._redraw()

    def _redraw(self):
        img = np.copy(self.image)
        for rect in self.rects:
            cv2.rectangle(img, rect[0], rect[1], (0, 255, 0, 128), 2)
        if self.selection is not None:
            cv2.rectangle(img, self.selection[0], self.selection[1], (255, 0, 0, 128), 2)
        cv2.imshow(self.window_name, img)

    def _finish(self):
        self.output.write(self.file + "\n")
        for rect in self.rects:
            self.output.write(str(rect) + "\n")

    def run(self):
        self._redraw()
        while True:
            key = cv2.waitKey(100) & 0xFF
            if key == 255:
                continue
            if key == 27: # ESC key
                self._finish()
                return
            if key == 100: # d key
                if self.start_rect_move is not None:
                    self.start_pos_move = None
                    self.selection = None
                    self.start_rect_move = None
            self._redraw()

def main_mark_images(args):
    parser = argparse.ArgumentParser(description="Markup gaps on images.")
    parser.add_argument("--images", required=True, help="A directory with all the images. This directory has to ONLY contail images.")
    parser.add_argument("--description", required=True, help="A resulting text file with metadata.")
    parser.add_argument("--rewrite", action="store_true", default=False, help="Rewrite the description file rather than append to it.")
    parser.add_argument("--start-after", dest="start_after", required=False, help="An image to start from. "
        + "If specified, all the images before and inclusive this one will be ignored. Useful to continue marking up after stopping the precess.")
    args = parser.parse_args(args)

    print("Starting the image editor.")
    print()
    print("To mark an area just click the left mouse key and move the cursor as if selecting it.")
    print("The selected rectangle automatically gets normalized to a square.")
    print()
    print("To move a selection click on it with the right mouse key and move the cursor whule holding it pressed.")
    print()
    print("To delete a selection, click on it with the right mouse key and while pressing it hit the 'd' key on the keyboard.")
    print()
    print("To finish editing selections and dump them to a file press ESC.")
    print()

    try:
        window_name = "frame"
        cv2.namedWindow(window_name)
        if args.rewrite:
            result = open(args.description, "w")
        else:
            result = open(args.description, "a")
        for file in all_files_after(all_files(args.images), args.start_after):
            Editor(file, result, "frame").load().run()
    finally:
        cv2.destroyWindow(window_name)
        result.close()

if __name__ == '__main__':
    (modchooser.ModChooser("Tools for the gaps detection project.")
        .add("mark_images", main_mark_images, "Iterate images and give tools to mark gaps to the user.")
        .main())
