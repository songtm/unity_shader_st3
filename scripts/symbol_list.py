#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import re
import json
try:
    from common import pluginRootPath
except:
    from .common import pluginRootPath

class Symbol(object):
    def __init__(self, name = "", type = "", path = "", pos = (0,0), paramtip = "", paramHolder = ""):
        self.name = name
        self.type = type;
        self.path = path
        self.pos = pos
        self.paramtip = paramtip
        self.paramHolder = paramHolder

    @staticmethod
    def json2Symbol(d):
        return Symbol(d['name'], d['type'], d['path'], d['pos'], d['paramtip'], d['paramHolder'])

# builtin_shader root path
root = ""
def generateSymbolList(beginPath):
    global root
    root = beginPath
    symbolList = []
    generateFunctionList(symbolList)
    generateDefineList(symbolList)
    generateVariableList(symbolList)

    f = open(r'../builtin_shader.symbol', 'w')
    # json.dump(symbolList, f, default=lambda obj: obj.__dict__)
    json.dump(symbolList, f, default=lambda obj: obj.__dict__, indent = 4)
    f.close()

def getParamInfo(paramStr, hasType = True):
    #参数处理
    param = paramStr.strip().strip("(").strip(")").replace("in ", "").replace("out ", "")  #简单处理 in out
    if hasType:
        itr = re.finditer(r"(\w+)\s+(\w+)", param, re.M)
    else:
        itr = re.finditer(r"(\w+)", param, re.M)
    paramHolder = "("
    paramtip = "("
    count = 1
    nameIndex = 1
    if hasType :
        nameIndex = 2
    for ii in itr:
        # print(ii.group(1), ii.group(2))
        if count != 1:
            paramHolder += ","    
            paramtip += ","
        paramHolder += "${"+str(count)+":"+ii.group(nameIndex)+"}"
        # paramtip += ii.group(1)+":"+ii.group(2) #提示带参数
        paramtip += ii.group(nameIndex)
        count += 1
        pass
    paramHolder += ")"
    paramtip += ")"
    return [paramtip, paramHolder]

def generateFunctionList(symbolList):
    for path, folders, files in os.walk(root):
        for filename in files:
            # if filename != "AutoLight.cginc":
            #     continue
            f = open(os.path.join(root, filename))
            buf = f.read()
            f.close()
            cmd = r"^(inline\s+)?(\w+)\s+(\w+)\s*\(([\s\S]*?)\)"
            #cmd = r"^(inline[ \t]+)?[ \t]*[\w]+[ \t]+(\w+)[ \t]*\((([ \t]*(\w+[ \t]+)?\w+[ \t]+\w)|([ \t]*\n)|([ \t]*\)))"
            functionIter = re.finditer(cmd,
                buf, re.M)
            for i in functionIter:
                # todo, path截短
                name = i.group(3)
                #参数处理
                resParam = getParamInfo(i.group(4))
                paramtip = resParam[0]
                paramHolder = resParam[1]


                path = os.path.join(root, filename)
                path = path.replace(pluginRootPath+"\\", "")
                lineNo = len(re.findall(r".*\n", buf[0:i.start()])) + 1
                columnNo = re.search(i.group(3), i.group(0)).start()
                pos = (lineNo, columnNo)
                symbolList.append(Symbol(name, "builtin-function", path, pos, paramtip, paramHolder))



def generateDefineList(symbolList):
    for path, folders, files in os.walk(root):
        for filename in files:

            if filename == "HLSLSupport.cginc":
                continue

            f = open(os.path.join(root, filename))
            buf = f.read()
            f.close()

            # functionIter = re.finditer(r"^[\s]*#define[\s]+(\w+)\b(?!\s*\n)", buf, re.M)
            functionIter = re.finditer(r"[\s]*#define[\s]+(\w+)\b(?!\s*\n)((\(.*?\))?)", buf, re.M)
            
            for i in functionIter:
                name = i.group(1)
                type = "builtin-marco"
                paramtip = ""
                paramHolder = ""
                if len(i.group(2)) > 1: #有参数
                    type = "builtin-function"
                    rss = getParamInfo(i.group(2), False)
                    paramtip = rss[0]
                    paramHolder = rss[1]

                path = os.path.join(root, filename)
                path = path.replace(pluginRootPath+"\\", "")
                lineNo = len(re.findall(r".*\n", buf[0:i.start()])) + 1
                columnNo = re.search(i.group(1), i.group(0)).start()
                pos = (lineNo, columnNo)
                symbolList.append(Symbol(name, type, path, pos, paramtip, paramHolder))

def generateVariableList(symbolList):
    for path, folders, files in os.walk(root):
        for filename in files:

            if not filename in ["UnityShaderVariables.cginc", "UnityLightingCommon.cginc", "Lighting.cginc", "AutoLight.cginc"]:
                continue

            f = open(os.path.join(root, filename))
            buf = f.read()
            f.close()

            variablePattern = r"(uniform[\s]*)?(((float|half|fixed)([2-4](x[2-4])?)?)|sampler(CUBE|[23]D))[\s]*([\w]*)(\[\d*\])?\s*;"
            # sometimes, define statement can break above rule 
            variablePattern2 = r"(uniform[\s]*)(\w+)[\s]*([\w]*)(\[\d*\])?\s*;"

            lineMatchIter = re.finditer(".*\n", buf)
            for index, line in enumerate(lineMatchIter):
                lineBuf = line.group()
                if re.search("\(", lineBuf):
                    match = re.search("\(", lineBuf)
                    _skipToBracketEnd(lineMatchIter, lineBuf[match.end():], "\)")
                elif re.search("{", lineBuf):
                    match = re.search("{", lineBuf)
                    _skipToBracketEnd(lineMatchIter, lineBuf[match.end():], "}")
                elif re.search(variablePattern, lineBuf):
                    match = re.search(variablePattern, lineBuf)
                    name = match.group(8)
                    _fillVariableRecord(symbolList, name, root, filename, index+1, line)
                elif re.search(variablePattern2, lineBuf):
                    match = re.search(variablePattern2, lineBuf)
                    name = match.group(3)
                    _fillVariableRecord(symbolList, name, root, filename, index+1, line)
                else:
                    pass

def _skipToBracketEnd(lineMatchIter, lineBuf, bracket):
    while (True):
        if re.search(bracket, lineBuf):
            return
        elif re.search("\(", lineBuf):
            match = re.search("\(", lineBuf)
            _skipToBracketEnd(lineMatchIter, lineBuf[match.end():], "\)")
        elif re.search("{", lineBuf):
            match = re.search("{", lineBuf)
            _skipToBracketEnd(lineMatchIter, lineBuf[match.end():], "}")

        lineBuf = next(lineMatchIter).group(0)

def _fillVariableRecord(symbolList, name, root, filename, lineNo, lineMatch):
    path = os.path.join(root, filename)
    path = path.replace(pluginRootPath+"\\", "")
    columnNo = re.search(name, lineMatch.group(0)).start()
    pos = (lineNo, columnNo)
    symbolList.append(Symbol(name, "builtin-variable", path, pos))

def printSymbolList():
    f = open(r'../builtin_shader.symbol', 'r')
    symbolList = json.load(f, object_hook=Symbol.json2Symbol)
    f.close()

    f = open(r'C:\Users\Administrator\Desktop\Tmp\symbolList.txt', 'w')
    for i in symbolList:
        f.write("%s,\t%s,\t%s,\t%s\n" % (i.name, i.type, i.path, i.pos))
    f.close()

def generateCompletesFile(forBetterCompletion = False):
    symbolFile = os.path.join(pluginRootPath, 'builtin_shader.symbol')
    f = open( symbolFile, 'r')
    symbolList = json.load(f, object_hook=Symbol.json2Symbol)
    f.close()

    filename = 'builtin.sublime-completions'
    template = '        { "trigger": "%s", "contents": "%s"},\n'
    if forBetterCompletion:
        filename = "../User/sbc-api-builtin.sublime-settings"
        template = '        ["%s", "%s"],\n'

    completesFile = os.path.join(pluginRootPath, filename)
    f = open(completesFile, 'w')
    f.write(r'''{
    "scope": "source.shader",
    "completions":
    [
''')
    
    isExists = set()
    for i in symbolList:
        if i.name in isExists:
            continue
        else:
            isExists.add(i.name)

        if i.type == "builtin-function":
            line = template % (i.name+i.paramtip+"\\tf",  i.name+i.paramHolder)
        elif i.type == "builtin-marco":
            line = template % (i.name+"\\tbuiltin-marco",  i.name)
        elif i.type == "builtin-variable":
            line = template % (i.name+"\\tbuiltin-variable",  i.name)
        else:
            line = template % (i.name, i.name)

        f.write(line)
    
    f.write(r'''    ]
}
''')

    f.close()

if __name__ == "__main__":
    print("xxx")
    root = "C:\\Users\\songtianming\\AppData\\Roaming\\Sublime Text 3\\Packages\\unity_shader_st3\\builtin_shaders-5.5.0f3\\CGIncludes"
    generateSymbolList(root)
    generateCompletesFile(False)
    generateCompletesFile(True)
