# -*- coding: utf-8 -*-
import pcbnew
import re
import math


(
    HORIZON_THEN_VERTICAL,
    VERTICAL_THEN_HORIZON 
) = range(0,2)


#MODULEのオブジェクトmoduleを受け取り、
#moduleのリファレンスから数字部分だけを抽出して数値として返す
def __extractRefNumber(module):
    matchResult = re.findall('\d+', module.GetReference())
    return int(matchResult[0])


#正規表現にマッチしたMODULEをリストにして返す
#sort=Trueにするとリファレンスの番号順にソートする
def findModulesByRe(pattern, sort=False):
    re_pattern = re.compile(pattern)
    moduleList = []
    for module in pcbnew.GetBoard().GetModules():
        if re_pattern.match( module.GetReference() ):
            moduleList.append(module)
    if sort:
        moduleList = sorted(moduleList, key=__extractRefNumber)

    return moduleList


#文字列のリストを渡すと、文字列と一致したリファレンスをもつMODULEのリストを返す
def findModulesByStrings(refList):
    moduleList = []
    for ref in refList:
        found = pcbnew.GetBoard().FindModuleByReference(ref)
        if found:
            moduleList.append(found)

    return moduleList


#リファレンスの文字の大きさと太さをまとめて変更する
def changeRefSize(moduleList, size, thickness):
    for module in moduleList:
        ref = module.Reference()
        ref.SetHeight( int(size*10**6) )
        ref.SetWidth( int(size*10**6) )
        ref.SetThickness( int(thickness*10**6) )


#部品の向きをまとめて変更する(度)
def rotate(moduleList, orientation):
    for module in moduleList:
        module.SetOrientation( int(orientation*10) )


#部品をまとめて移動する(mm)
def move(moduleList, diff):
    for module in matchedModules(pattern):
        module.Move( pcbnew.wxPointMM(diff[0], diff[1]) )


#部品を直線上に並べる
#start:始点座標(x,y)
#space:間隔
def arrangeInLine(moduleList, start, space):
    for index, module in enumerate(moduleList):
        posx = start[0] + index * space[0]
        posy = start[1] + index * space[1]
        module.SetPosition( pcbnew.wxPointMM(posx,posy) )


#部品を格子上に並べる
#start:始点座標(x,y)
#space:間隔(x,y)
#priority:moduleListの要素を縦と横どちらを優先して並べていくか
#    HORIZON_THEN_VERTICAL か VERTICAL_THEN_HORIZON
#size:priorityで指定した先に並べる方向に何個並べるか
def arrangeInMatrix(moduleList, start, space, size, priority = HORIZON_THEN_VERTICAL):
    i,j = 0,0
    for index, module in enumerate(moduleList):
        if priority == HORIZON_THEN_VERTICAL:
            j = int( index%size )
            i = int( index/size )
        elif priority == VERTICAL_THEN_HORIZON:
            j = int( index/size )
            i = int( index%size )
        posx = start[0] + j*space[0]
        posy = start[1] + i*space[1]
        module.SetPosition(pcbnew.wxPointMM(posx,posy))


#部品を円状に並べる
#center:中心座標(x,y)
#radius:半径
#rotate:部品を回転するかどうか
#orientationOffset:部品の初期角度(度)
#angleOffset:並べ始める角度(度)
def arrangeInCircle(moduleList, center, radius, rotate = True, orientationOffset = 0, angleOffset = 0):
    angleStep = 360 / len(moduleList)
    for index, module in enumerate(moduleList):
        angle = index*angleStep + angleOffset
        angle_rad = angle*math.pi/180
        posx = center[0] + radius*math.cos(angle_rad)
        posy = center[1] + radius*math.sin(angle_rad)
        module.SetPosition( pcbnew.wxPointMM(posx,posy) )

        if rotate:
            orientation = -(angle + orientationOffset) *10
            module.SetOrientation( int(orientation) )
