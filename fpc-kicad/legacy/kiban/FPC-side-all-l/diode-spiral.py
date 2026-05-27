import importlib, pcbnew
from io import open
import csv, math, kicad_tools

(
    HORIZON_THEN_VERTICAL,
    VERTICAL_THEN_HORIZON 
) = range(0,2)


# filename = "/Users/katano/Documents/home/neon/seam-ball/spiral-capacitor-45-150.csv"
filename = '/Users/katano/isolation-sphere/kiban/FPC-head-all/tri_hexagon_centroids.csv'
print(filename)
print('spiral')
# board = pcbnew.GetBoard()

# print(board)

# def findModulesByRe(pattern, sort=False):
#     re_pattern = re.compile(pattern)
#     moduleList = []
#     for module in pcbnew.GetBoard().GetFootprints():
#         if re_pattern.match( module.GetReference() ):
#             moduleList.append(module)
#     if sort:
#         moduleList = sorted(moduleList, key=__extractRefNumber)

#     return moduleList


with open(filename, "r", newline="") as f:
    board = pcbnew.GetBoard()
    csvreader = csv.reader(f)


    for i, row in enumerate(csvreader):
        # print(i, row, row[1], row[2], row[3])
        # if i > 0 and i <= 150:
        if i > 0 and i <= 2000:
            x = float(row[1])
            y = float(row[2])
            # x = int(float(row[1])/10.0)
            # y = int(float(row[2])/10.0)

            ref = "D" + str(i)

            # KiCad 6以降
            if hasattr(board, "FindFootprintByReference"):
                found = board.FindFootprintByReference(ref)
            # KiCad 5以前（参考用）
            elif hasattr(board, "FindModuleByReference"):
                found = board.FindModuleByReference(ref)
            else:
                raise RuntimeError("Unsupported KiCad version: neither FindFootprintByReference nor FindModuleByReference is available.")


            l = kicad_tools.findModulesByStrings([ref])
            # radian = math.atan2(y, x)
            # degree = -radian * (180 / math.pi) - 90.0
            degree = -float(row[5])
            # degree = float(row[4])

            print(i, ref, degree, row)
            l[0].SetOrientationDegrees(degree)
            # l[0].SetOrientation(pcbnew.EDA_ANGLE(degree*1.0, pcbnew.DEGREES_T))


            point = pcbnew.wxPoint(x,y)
            l[0].SetPosition(pcbnew.VECTOR2I(pcbnew.wxPointMM(x, y)))
            # board.Add(l[0])
    # board.Add(l[0])
# ledList = kicad_tools.findModulesByRe("D\d+")

# print(ledList)
# print(ledList.shape)

# for i in range(180):
#     d = kicad_tools.findModulesByStrings(['D' + str()])
#     print(d.GetReference())

# for led in ledList:
#     print(led.GetReference())

