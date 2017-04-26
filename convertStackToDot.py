#!/usr/bin/python
#coding=utf-8
#python convertStackToDot.py stack.txt|dot -Tpng>output.png
#To generate ascii flow chart, graph_easy should be installed:
#  sudo apt-get install libgraph-easy-perl
#The use below command line:
#python convertStackToDot.py stack.txt|graph-easy -as_ascii>output.txt

import sys
import re
import argparse
import os
import operator

function_name_str = r"[a-zA-Z][a-zA-Z0-9]*::[~a-zA-Z0-9\_\-<: >=]*\(|[a-zA-Z0-9_\-<>]* \("
class_name_str = r"::[a-zA-Z][a-zA-Z0-9]*::"
known_namespaces = ["WebCore","WTF","android","v8"]

libCName="/system/lib/libc.so"

Colors=["#000000","#ff0000","#00aa00","#0000ff","#800080","#daa520","#ff00b4","#d2691e","#00bfff",
        "#D0A020","#006000","#305050","#101870"]

Styles=["solid","dashed","dotted"]

MAX_COLOR_COUNT = len(Colors)
MAX_LINE_WIDTH_COUNT = 4
MAX_STYLE_COUNT = len(Styles)

FirstNodeAttr = ' style="rounded,filled" fillcolor=\"#00bb0050\"'
HighlightAttr = ' style="rounded,filled" fillcolor=yellow'

blockNum = 0    
nodeNo = 0

nodeList={}
usedNodeList={}
nodeUsedCount={}
relationUsedCount={}
nodeOrderList={}
firstNodeList={}
nodeAttr={}

outputText = ''
callingStack = ''
newBlock=True

willCommit=False #For filtering purpose
strictCommit=False
blockBackTrace = ''
blockNodeList=[]
blockNodeOrderList={}

minStackLevel = 2

def getTextOfBlockNodeList(lastNodeName,lastNodeLabel):
    global firstNodeList,nodeOrderList,blockNodeList,usedNodeList
    strBlockNodeText = ''

    lastName = ''
    for key in blockNodeList:
        name = nodeList[key]
        if not usedNodeList.has_key(key):
            strBlockNodeText = strBlockNodeText + name + nodeAttr[name]+'\n'
            usedNodeList[key] = name

        if len(lastName)>0:
            tempKey = '%s,%s'%(name,lastName)
            nodeOrderList[tempKey] = True

        lastName = name

    #Replace the attribute of the last node
    if len(lastNodeName)>0 and not firstNodeList.has_key(lastNodeName):
        oldStr = lastNodeName+'[label="'+lastNodeLabel+'" shape=box ];';
        newStr = lastNodeName+'[label="'+lastNodeLabel+'" shape=box '+FirstNodeAttr+' ];'
        strBlockNodeText = strBlockNodeText.replace(oldStr,newStr,1)
        firstNodeList[lastNodeName] = True

    return strBlockNodeText


def submitAndResetForNewBlock(args,lastNodeName,lastNodeLabel):
    global blockBackTrace,newBlock,callingStack
    global blockNodeList,willCommit,outputText

    newBlock = True

    if willCommit and len(blockBackTrace)>0:
        callingStack = blockBackTrace + '\n' + callingStack
        blockNodeText = getTextOfBlockNodeList(lastNodeName,lastNodeLabel)
        outputText = outputText+blockNodeText

    blockNodeList = []
    blockNodeOrderList = {}
    blockBackTrace = ''
    willCommit = (len(args.filter)==0)

def getClassName(text):
    m = re.search(class_name_str,text)
    if m:
        className=text[0:m.end()-2]
    elif not text[:text.find('::')] in known_namespaces:
        className = text[:text.find('::')]
    else:
        className = text

    return className

def getNodeName(text,nodeNo,args):
    global willCommit,blockNodeList,newBlock
    global strictCommit,minStackLevel
    
    processText = text

    if len(args.ignore)>0 and re.search(args.ignore,text):
        return '' 

    if args.onlyClass:
        processText = getClassName(text)

    if nodeList.has_key(processText):
        nodeName = nodeList[processText]
    else:
        nodeName = 'Node'+str(nodeNo)
        nodeList[processText]=nodeName
        
        extraAttr = ''
        try:
            if len(args.highlight)>0 and re.search(args.highlight,processText):
                extraAttr = HighlightAttr
        except:
            extraAttr = ''

        nodeAttr[nodeName] = '[label="'+processText+'" shape=box '+extraAttr+'];'

    blockNodeList.append(processText)

    if not strictCommit and len(args.filter)>0 and re.search(args.filter,text):
        willCommit = True

    return [nodeName,processText]


def createNewRelation(nodeName,lastNodeName,blockNum,args):
    global blockBackTrace

    if args.showCallingCount and nodeName==lastNodeName:
        return

    tempKey = "%s,%s"%(nodeName,lastNodeName)
    if args.duplicate or not nodeOrderList.has_key(tempKey): #blockNodeOrderList
        lineColor = Colors[(blockNum-1)%MAX_COLOR_COUNT]
        linePenWidth = str((int((blockNum-1)/MAX_COLOR_COUNT)%MAX_LINE_WIDTH_COUNT)+1)
        lineStyle = Styles[((blockNum-1)/(MAX_COLOR_COUNT*MAX_LINE_WIDTH_COUNT))%MAX_STYLE_COUNT]

        if nodeOrderList.has_key(tempKey):
            linePenWidth = '1'
            lineColor = lineColor+'50' #Set alpha value

        if args.showCallingCount:
            tempLabel = ''
        else:
            tempLabel = str(blockNum)

        blockBackTrace = nodeName+'->'+lastNodeName+'[label='+tempLabel+\
                    ',color=\"'+lineColor+'\"'+\
                    ',style=\"'+lineStyle+'\"'+\
                    ',penwidth='+linePenWidth+']\n'+ \
                    blockBackTrace

        blockNodeOrderList[tempKey] = True


def outputFunctions(usedCountDict):    
    f = open("orderedFunctions.txt", 'w')    
    for node in usedCountDict:
        f.write("%s,%d\n"%(node[0],node[1]))
    f.close()

def replaceOutputText(text,usedCountDict):
    for node in usedCountDict:
        stringText = '"%s"'%(node[0])
        newString = '"%s(%d)"'%(node[0],node[1])
        text = text.replace(stringText,newString,1)

    return text

def replaceLineLabel(stackText,usedCountDict):
    global usedNodeList
    for node in usedCountDict:
        [nodeA,nodeB] = node[0].split(',')
        stringText = '%s->%s[label=,'%(nodeA,nodeB)
        newString = '%s->%s[label=%d,'%(nodeA,nodeB,node[1])
        stackText = stackText.replace(stringText,newString)

    return stackText

def combineOutputText(args):
    global outputText,callingStack,nodeUsedCount,relationUsedCount

    if len(callingStack)>0:
        newList = sorted(nodeUsedCount.items(), key=operator.itemgetter(1), reverse=True)
        outputFunctions(newList)

        if args.showCallingCount:
            outputText = replaceOutputText(outputText,newList)
            newList = sorted(relationUsedCount.items(), key=operator.itemgetter(1), reverse=True)
            outputText = outputText+replaceLineLabel(callingStack,newList)
        else:
            outputText = outputText+callingStack

        return outputText+"\n}"
    else:
        return ''

def increaseDictValueWithKey(dict,key):
    if dict.has_key(key):
        dict[key] = dict[key] + 1
    else:
        dict[key] = 1

def initialize(args):
    global outputText,callingStack
    outputText = "digraph backtrace{ \n node [ style=rounded  fontname=\"Helvetica Bold\"];\n" + args.extraDotOptions +"\n"

def convertToDot(file,args):
    global willCommit,outputText,newBlock,blockNum,nodeNo
    global outputText,callingStack,blockBackTrace

    blockBackTrace = ''    
    lastNode = ['',''] #name and title

    willCommit = (len(args.filter)==0) #To specify the initial value according to the filter.
    strictCommit = False

    f = open(file, 'r')

    for line in f:
        line = line.strip()
        if(len(line)==0) or line.startswith("#0  ") or line.startswith("#00 "):
            if not newBlock:
                #Start with new block here.
                submitAndResetForNewBlock(args, lastNode[0], lastNode[1])

            if(len(line.strip())==0):
                continue

        if not line.startswith("#"):
            continue

        text = ""

        m = re.search(function_name_str, line)
        if m:
            nodeNo = nodeNo+1
            text=m.group(0).strip()
            text = text[:-1]
            text = text.strip()
        elif line.find(libCName)>0:
            nodeNo = nodeNo+1
            text=''

        if(len(text)==0):
            continue

        #Get the existing node or create new one. Anyway, just ask for the name.
        [nodeName,processedText]= getNodeName(text,nodeNo,args)
        #To throw it away if no valid name was returned according to your arguments.
        if(len(nodeName)==0):
            continue

        increaseDictValueWithKey(nodeUsedCount,processedText)

        if(len(lastNode[0])>0):
            currRelation = "%s,%s"%(nodeName,lastNode[0])
            increaseDictValueWithKey(relationUsedCount,currRelation)

            if args.showCallingCount:
                if nodeUsedCount.get(processedText,1) < minStackLevel:
                    willCommit = False
                    strictCommit = True

        if newBlock:
            newBlock = False
            blockNum = blockNum + 1
        else:
            createNewRelation(nodeName,lastNode[0],blockNum,args)

        lastNode = [nodeName,processedText]

    if len(blockBackTrace)>0:
        #Wow, one block was built successfully, sumit it.
        submitAndResetForNewBlock(args, lastNode[0], lastNode[1])

    f.close()

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=str, help='The text file which contains GDB call stacks.')
    parser.add_argument('-e','--extraDotOptions', default='', help='Extra graph options. For example: rankdir=LR; That means to show functions in horizontal.')
    parser.add_argument('-l','--highlight', default='', help='Regular Expression Pattern. Nodes are highlighted whose name match the pattern.')
    parser.add_argument('-f','--filter', default='', help='Regular Expression Pattern. The calling stack are shown only if which include the matched nodes.')
    parser.add_argument('-d','--duplicate', action='store_true', default=False, help='Leave duplicated callings.')
    parser.add_argument('-i','--ignore', default='', help='To hide some nodes, try this.')
    parser.add_argument('-c','--onlyClass', action='store_true', default=False, help='To simplify the output with less nodes, only Class node will be listed.')
    parser.add_argument('-n','--minUsedCnt', action='store', default=20, type=int, help='To sepecify the minimum stack reused count.')
    parser.add_argument('-s','--showCallingCount', action='store_true', default=False, help='To show calling count on the label and line.')

    if len(sys.argv)<=1:
        parser.print_help()
        print "  Any comment, please feel free to contact horky.chen@gmail.com."
        quit()

    args = parser.parse_args()
    
    if args.file is None:
        quit()

    initialize(args)

    minStackLevel = args.minUsedCnt

    if os.path.isfile(args.file):
        convertToDot(args.file,args)
    else:
        filenames = os.listdir(args.file)
        for filename in filenames:
            convertToDot(os.path.join(args.file,filename),args)

    resultDotString = combineOutputText(args)

    if len(resultDotString)>0:
        print(resultDotString)