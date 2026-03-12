import argparse
import math
import os
import sys
import time
from multiprocessing import Manager, Pool, Process

import cv2
import numpy as np
import pymupdf

from qrgrader.code import Code
from qrgrader.code_set import CodeSet, PageCodeSet
from qrgrader.utils import pix2np, get_patches, threshold, get_codes, compute_similarity_transform, \
    get_similarity_transform


class PageProcessor(Process):

    def __init__(self, semaphore, filename, index, generated, result, **kwargs):
        super().__init__()
        self.filename = filename
        self.index = index
        self.generated = generated
        self.result = result
        self.semaphore = semaphore

        self.dpi = kwargs.get("dpi", 400)
        self.thresholds = kwargs.get("thresholds", [50, 55, 60, 65, 70, 75, 80])
        self.matrix = pymupdf.Matrix(self.dpi / 72, self.dpi / 72)
        self.show_patches = kwargs.get("show_patches", False)
        self.resize = kwargs.get("resize", 1.0)
        self.dir_images = kwargs.get("dir_images", "../..")

        self.ppm = self.dpi / 25.4

    def run(self):

        # Render the image
        doc = pymupdf.open(self.filename)
        page = doc[self.index]
        image = pix2np(page.get_pixmap(matrix=self.matrix))  # noqa
        doc.close()


        # Find page, orientation and rotate page
        rotation = None
        detected = PageCodeSet()
        h, w = image.shape[:2]

        for th in self.thresholds:

            ne = threshold(image[0:500, w - 500:w], th)
            for text, cx, cy, cw, ch in get_codes(ne):
                if text.startswith("P"):
                    rotation = -1
                elif text.startswith("Q"):
                    rotation = cv2.ROTATE_180
                detected.append(Code(text, cx, cy, cw, ch))

            if rotation is None:
                nw = threshold(image[0:500, 0:500], th)
                for text, cx, cy, cw, ch in get_codes(nw):
                    if text.startswith("P"):
                        rotation = cv2.ROTATE_90_CLOCKWISE
                    elif text.startswith("Q"):
                        rotation = cv2.ROTATE_90_COUNTERCLOCKWISE
                    detected.append(Code(text, cx, cy, cw, ch))

            if rotation is None:
                sw = threshold(image[h - 500:h, 0:500], th)
                for text, cx, cy, cw, ch in get_codes(sw):
                    if text.startswith("P"):
                        rotation = cv2.ROTATE_180
                    elif text.startswith("Q"):
                        rotation = -1
                    detected.append(Code(text, cx, cy, cw, ch))

            if rotation is None:
                se = threshold(image[h - 500:h, w - 500:w], th)
                for text, cx, cy, cw, ch in get_codes(se):
                    if text.startswith("P"):
                        rotation = cv2.ROTATE_90_COUNTERCLOCKWISE
                    elif text.startswith("Q"):
                        rotation = cv2.ROTATE_90_CLOCKWISE
                    detected.append(Code(text, cx, cy, cw, ch))

            if rotation is not None:
                break

        if rotation is not None and rotation != -1:
            image = cv2.rotate(image, rotation)

        # Get the page number if we got it
        page = detected.get_page()

        # Clear the detected because the
        # page may have been rotated
        detected.clear()

        # Process the page and extract the detected
        for th in self.thresholds:
            th_image = threshold(image, th)
            patches = get_patches(th_image, self.ppm, 8)

            for px, py, pw, ph in patches:
                patch = image[py:py + ph, px:px + pw]

                if self.show_patches:
                    cv2.rectangle(image, (px, py), (px + pw, py + ph), (0, 0, 255), 1)

                for text, cx, cy, cw, ch in get_codes(patch):
                    detected.append(Code(text, px + cx, py + cy, cw, ch, page, self.index))

        # Try again with the whole page
        page = detected.get_page() if page is None else page
        exam = detected.get_exam_id()

        # If we did not find the page number, try to find it in the generated detected
        if page is None:
            if len(detected) > 0:
                page = self.generated.get(detected.first()).page
                for code in detected:
                    code.set_page(page)

        if self.resize != 1.0:
            image = cv2.resize(image, (int(image.shape[1] * self.resize), int(image.shape[0] * self.resize)),
                               interpolation=cv2.INTER_AREA)

        if page is not None:
            cv2.imwrite(self.dir_images + os.sep + "page-{}-{}-{:03d}.jpg".format(detected.get_date(), detected.get_exam_id(), page), image)
        elif detected.get_exam_id():
            cv2.imwrite(self.dir_images + os.sep + "page-{}-{}-{:03d}.jpg".format(detected.get_date(), detected.get_exam_id(), 0), image)
        else:
            cv2.imwrite(self.dir_images + os.sep + "{}-{:03d}.jpg".format(self.filename, self.index), image)

        # # Compute the transformation
        generated_page_codeset = PageCodeSet(self.generated.select(exam=exam, page=page))

        # We will use the two codes that are the farthest apart to compute
        # the transformation, if we have at least two codes detected
        max_dist, codes = 0, None
        for code1 in detected:
            for code2 in detected:
                if code1!=code2:
                    dist = math.sqrt((code1.get_pos()[0] - code2.get_pos()[0]) ** 2 + (code1.get_pos()[1] - code2.get_pos()[1]) ** 2)
                    if dist > max_dist:
                        max_dist = dist
                        codes = (code1, code2)

        if codes is not None:
            # we have at least two codes detected, we can use them to compute the transformation
            code1, code2 = codes[0], codes[1]
            p11 = self.generated.get(code1).get_pos()
            p12 = self.generated.get(code2).get_pos()
            p21 = code1.get_pos()
            p22 = code2.get_pos()
            transform = get_similarity_transform([p11, p12], [p21, p22]) # noqa
        elif len(detected) > 0:
            # we have detected just one code, we can use it to compute the transformation
            code1 = detected.first()
            p11 = self.generated.get(code1).get_pos()
            p21 = code1.get_pos()
            transform = lambda pt: (pt[0] + (p21[0] - p11[0]), pt[1] + (p21[1] - p11[1]))
        else:
            # No codes detected, we can not compute the transformation, we will just use the identity
            transform = lambda pt: pt

        # TODO: NOTHING TO DO, JUST A NOTE
        # TODO: ATTENTION! This is the KEY: ALL THE CODES will be present in the detected set,
        # TODO: but they will be marked as "marked" if they were not detected in the page.
        # TODO: This way we can keep track of all the codes and their positions, even if
        # TODO: they were not detected in the page.

        for code in generated_page_codeset:
            new_pose = transform(code.get_pos())
            code.set_pos(new_pose)  # Note: OpenCV uses (y, x) order
            code.set_size(120, 120)
            code.scale(72.0 / self.dpi)
            code.set_marked(detected.get(code) is None)
            self.result.append(code)

        #print(f"Processed {os.path.basename(self.filename)} page {self.index} ({len(generated_page_codeset)} codes detected)")
        self.semaphore.release()
