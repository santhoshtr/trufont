"""
UI-constrained point management methods.
"""
from trufont.tools import bezierMath
from PyQt5.QtCore import QLineF


def _getOffCurveSiblingPoints(contour, point):
    index = contour.index(point)
    pts = []
    for d in (-1, 1):
        sibling = contour.getPoint(index + d)
        if sibling.segmentType is not None:
            sSibling = contour.getPoint(index + 2 * d)
            pts.append((sibling, sSibling))
    return pts


def moveUIPoint(contour, point, delta):
    if point.segmentType is None:
        shouldMove = True
        # point is an offCurve. Get its sibling onCurve and the other
        # offCurve.
        siblings = _getOffCurveSiblingPoints(contour, point)
        for onCurve, otherPoint in siblings:
            # if the onCurve is selected, the offCurve will move along with it
            if onCurve.selected:
                shouldMove = False
            if not onCurve.smooth:
                contour.dirty = True
                continue
            # if the onCurve is smooth, we need to either...
            if otherPoint.segmentType is None and not otherPoint.selected:
                # keep the other offCurve inline
                line = QLineF(point.x, point.y, onCurve.x, onCurve.y)
                otherLine = QLineF(
                    onCurve.x, onCurve.y, otherPoint.x, otherPoint.y)
                line.setLength(line.length() + otherLine.length())
                otherPoint.x = line.x2()
                otherPoint.y = line.y2()
            else:
                # keep point in tangency with onCurve -> otherPoint segment,
                # ie. do an orthogonal projection
                point.x, point.y, _ = bezierMath.lineProjection(
                    onCurve.x, onCurve.y, otherPoint.x, otherPoint.y,
                    point.x, point.y, False)
        if shouldMove:
            point.move(delta)
    else:
        # point is an onCurve. Move its offCurves along with it.
        index = contour.index(point)
        point.move(delta)
        for d in (-1, 1):
            # edge-case: contour open, trailing offCurve and moving first
            # onCurve in contour
            if contour.open and index == 0 and d == -1:
                continue
            pt = contour.getPoint(index + d)
            if pt.segmentType is None:
                # avoid double move for qCurve with single offCurve
                if d > 0:
                    otherPt = contour.getPoint(index + 2 * d)
                    if otherPt.segmentType is not None and otherPt.selected:
                        continue
                pt.move(delta)
    contour.dirty = True


def moveUISelection(contour, delta):
    for point in contour.selection:
        moveUIPoint(contour, point, delta)


def removeUISelection(contour, preserveShape=True):
    segments = contour.segments
    # the last segments contains the first point, make sure to process it last
    # so as to not offset indexes
    toFirstPoint = segments[-1]
    toIter = list(enumerate(segments))
    toIter.insert(0, toIter.pop())
    # moonwalk through segments
    for index, segment in reversed(toIter):
        if segment == toFirstPoint:
            index = len(segments) - 1
        onCurve = segment[-1]
        # if the onCurve is selected, wipe it
        if onCurve.selected:
            # remove the contour if we have exhausted segments
            if len(segments) < 2:
                glyph = contour.glyph
                glyph.removeContour(contour)
                return
            # using preserveShape at the edge of an open contour will traceback
            if preserveShape and contour.open:
                if index in (0, len(segments) - 1):
                    preserveShape = False
            contour.removeSegment(index, preserveShape)
            # remove segment so we can keep track of how many remain
            del segments[index]
        elif len(segment) == 2:
            # move with trailing offCurve
            offCurve = segment[0]
            if offCurve.selected:
                assert(offCurve.segmentType is None)
                contour.removePoint(offCurve)
        elif len(segment) == 3:
            # if offCurve selected, wipe them
            for i in (0, 1):
                if segment[i].selected:
                    contour.removePoint(segment[0])
                    contour.removePoint(segment[1])
                    segment[2].segmentType = "line"
                    break
