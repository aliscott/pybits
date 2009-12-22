"""
A really basic sudoku solver.
Reads in an image and solves the sudoku using constraints programming.
Requires gocr for the OCR (http://jocr.sourceforge.net/),
and modules PIL (http://www.pythonware.com/products/pil/)
and python-constraint (http://labix.org/python-constraint).

Currently doesn't really work for JPEG images,
but has been tested with GIF and PNG.

Usage: python sudoku.py <image_file>

TODO: improve JPEG support, improve OCR,
extract grids from photos, output solutions
back to image.
"""

__author__ = 'Ali Scott'
__email__ = 'ali.scott@gmail.com'

import os
import tempfile
import subprocess

from constraint import Problem, AllDifferentConstraint
from PIL import Image

GOCR_CMD = """gocr -a 50 -C '1-9' -i"""

def parse_image(img):
    """ Retrieves the sudoku data from the image.
    """
    img = img.convert('1') # convert to black and white
    pixels = img.load()
    sudoku_data = []
    (w, h) = img.size
    for row in range(0, 9):
        for col in range(0, 9):
            (box_w, box_h) = (float(w) / 9, float(h) / 9)
            # get bounds of box
            (l, t, r, b) = (int(col * box_w), int(row * box_h),
                            int((col + 1) * box_w), int((row + 1) * box_h))
            # get black pixel close to centre of box
            black_pixel = _get_nearby_pixel(pixels, int(l + box_w / 2),
                                            int(t + box_h / 2),
                                            (l, t, r, b), lambda p: p < 1)
            # if no black pixel found, then no number in box
            if not black_pixel:
                sudoku_data.append(None)
                continue
            # get bounds of number
            bounds = _get_bounds(pixels, black_pixel[0], black_pixel[1],
                                (l, t, r, b), lambda p: p < 1)
            # if bounds not found within box then no number in box
            if not bounds:
                sudoku_data.append(None)
                continue
            # perform OCR on number
            cropped = img.crop(bounds)
            temp = tempfile.NamedTemporaryFile(suffix='.pbm')
            cropped.convert('1').save(temp.name)
            gocr = subprocess.Popen(GOCR_CMD.split() + [temp.name],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            temp.close()
            result = gocr.communicate()[0]
            # check result is valid
            try:
                result = int(result.strip())
                if result in range(0, 10):
                    sudoku_data.append(result)
                else:
                    sudoku_data.append(None)
            except ValueError:
                sudoku_data.append(None)
    return sudoku_data

def _get_bounds(pixels, x, y, area, condition=lambda p: p < 1):
    """ Extracts the bounds of a blob which contains
    pixel x, y and lies within specified area.
    A condition function can be specified to specify
    the conditions for a blob pixel. If no condition
    is pixel is part of the blob if it is black.
    """
    (l, t, r, b) = (x - 1, y -1, x + 1, y + 1)
    (al, at, ar, ab) = area
    l_found = t_found = r_found = b_found = False
    prev = None
    while False in (l_found, t_found, r_found, b_found):
        if (l, t, r, b) == prev:
            return None
        prev = (l, t, r, b)
        l_found = t_found = r_found = b_found = True
        for j in range(t, b + 1):
            if condition(pixels[l, j]):
                l_found = False
                l = max(l - 1, al)
                break
        for i in range(l, r + 1):
            if condition(pixels[i, t]):
                t_found = False
                t = max(t - 1, at)
                break
        for j in range(t, b + 1):
            if condition(pixels[r, j]):
                r_found = False
                r = min(r + 1, ar - 1)
                break
        for i in range(l, r + 1):
            if condition(pixels[i, b]):
                b_found = False
                b = min(b + 1, ab - 1)
                break
    return (l, t, r, b)


def _get_nearby_pixel(pixels, x, y, area, condition):
    """ Gets a nearby pixel to pixel x, y that is within the
    specified area and matches the specified condition.
    Note: this does not necessarily return the closest
    pixel distance-wise.
    """
    l = r = x
    t = b = y
    (al, at, ar, ab) = area
    while not (l == al and t == at and \
               r == ar - 1 and b == ab - 1):
        for i in range(l, r + 1):
            if condition(pixels[i, t]):
                return (i, t)
            if condition(pixels[i, b]):
                return (i, b)
        for j in range(b - 1, t):
            if condition(pixels[l, j]):
                return (l, j)
            if condition(pixels[i, j]):
                return (r, j)
        l = max(l - 1, al)
        t = max(t - 1, at)
        r = min(r + 1, ar - 1)
        b = min(b + 1, ab - 1)
    return None

def solve(sudoku_data):
    """ Solves the sudoku using simple constraints programming.
    Returns a list of solutions. Multiple solutions may be found if
    the sudoku wasn't parsed correctly.
    """
    problem = Problem()
    # add known numbers
    for i in range(0, 81):
        problem.addVariable(i, [int(sudoku_data[i])]
                                   if sudoku_data[i]
                                   else range(1, 10))
    for i in range(0, 9):
        # row constraint
        problem.addConstraint(AllDifferentConstraint(),
                              range(i * 9, i * 9 + 9))
        # column constraint
        problem.addConstraint(AllDifferentConstraint(),
                              [(i + 9 * c) for c in range(0, 9)])
        # box constraint
        problem.addConstraint(AllDifferentConstraint(),
                              [(i * 3) + (i / 3 * 18) + (9 * j) + k
                                  for j in range(0, 3)
                                    for k in range(0, 3)])
    return problem.getSolutions()


def output(sudoku_data):
    """ Outputs the sudoku in rows and columns.
    """
    for row in range(0, 9):
        if row in (3, 6):
            print """------+-------+-------"""
        for col in range(0, 9):
            if col in (3, 6):
                print '|',
            print sudoku_data[row * 9 + col] or ' ',
        print '\n',


def main():
    """ Takes a sudoku image file name as an argument and displays
    the solution.
    """
    import sys
    if len(sys.argv) < 2:
        print """Usage: python sudoku.py <image_file>"""
        sys.exit(0)
    input_file = sys.argv[1]
    try:
        img = Image.open(input_file)
    except IOError:
        print """Error: could not open file %s""" % (input_file)
        sys.exit(0)
    parsed = parse_image(img)
    if not any(parsed):
        print """Could not be parsed"""
        sys.exit(0)
    print """Parsed as:"""
    output(parsed)
    print '\n'
    solutions = solve(parsed)
    if not solutions:
        print """No solution found"""
        sys.exit(0)
    if len(solutions) > 1:
        print """Multiple solutions found:"""
    else:
        print """Solution:"""
    for solution in solutions:
        output(solution)
        print '\n'


if __name__ == '__main__':
    main()
