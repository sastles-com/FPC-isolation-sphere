# -*- coding: utf-8 -*-
import pcbnew
import re
import math

(
    HORIZON_THEN_VERTICAL,
    VERTICAL_THEN_HORIZON 
) = range(0, 2)


def __extractRefNumber(fp):
    matchResult = re.findall(r'\d+', fp.GetReference())
    return int(matchResult[0]) if matchResult else -1


def findModulesByRe(pattern, sort=False):
    re_pattern = re.compile(pattern)
    moduleList = []
    for fp in pcbnew.GetBoard().GetFootprints():
        if re_pattern.match(fp.GetReference()):
            moduleList.append(fp)
    if sort:
        moduleList = sorted(moduleList, key=__extractRefNumber)
    return moduleList


def findModulesByStrings(refList):
    board = pcbnew.GetBoard()
    moduleList = []
    for ref in refList:
        fp = board.FindFootprintByReference(ref)
        if fp:
            moduleList.append(fp)
        else:
            print(f"[Warning] Reference '{ref}' not found.")
    return moduleList


def changeRefSize(moduleList, size, thickness):
    for fp in moduleList:
        ref = fp.Reference()
        ref.SetHeight(int(size * 1e6))
        ref.SetWidth(int(size * 1e6))
        ref.SetThickness(int(thickness * 1e6))


def rotate(moduleList, orientation):
    for fp in moduleList:
        fp.SetOrientationDegrees(orientation)


def move(moduleList, diff):
    for fp in moduleList:
        old_pos = fp.GetPosition()
        new_pos = pcbnew.VECTOR2I(
            old_pos.x + pcbnew.FromMM(diff[0]),
            old_pos.y + pcbnew.FromMM(diff[1])
        )
        fp.SetPosition(new_pos)


def arrangeInLine(moduleList, start, space):
    for index, fp in enumerate(moduleList):
        posx = start[0] + index * space[0]
        posy = start[1] + index * space[1]
        fp.SetPosition(pcbnew.wxPointMM(posx, posy))


def arrangeInMatrix(moduleList, start, space, size, priority=HORIZON_THEN_VERTICAL):
    for index, fp in enumerate(moduleList):
        if priority == HORIZON_THEN_VERTICAL:
            j = index % size
            i = index // size
        elif priority == VERTICAL_THEN_HORIZON:
            j = index // size
            i = index % size
        posx = start[0] + j * space[0]
        posy = start[1] + i * space[1]
        fp.SetPosition(pcbnew.wxPointMM(posx, posy))


def arrangeInCircle(moduleList, center, radius, rotate=True, orientationOffset=0, angleOffset=0):
    angleStep = 360 / len(moduleList)
    for index, fp in enumerate(moduleList):
        angle = index * angleStep + angleOffset
        angle_rad = math.radians(angle)
        posx = center[0] + radius * math.cos(angle_rad)
        posy = center[1] + radius * math.sin(angle_rad)
        fp.SetPosition(pcbnew.wxPointMM(posx, posy))

        if rotate:
            orientation = -(angle + orientationOffset)
            fp.SetOrientationDegrees(orientation)
