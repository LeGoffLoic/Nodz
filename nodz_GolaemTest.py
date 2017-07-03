import string
import random

from Qt import QtCore, QtWidgets
import nodz_main

try:
    app = QtWidgets.QApplication([])
except:
    # I guess we're running somewhere that already has a QApp created
    app = None

nodz = nodz_main.Nodz(None)
nodz.loadConfig(filePath='golaem_chOpsNodz_config.json')
nodz.initialize()
nodz.show()

def updateChOpsNodzDebugOutput(nodz, outputValues):
    for chOpName in outputValues.keys():
        if chOpName not in nodz.scene().nodes.keys():
            print 'A node was not found in the visual debug interface : {}'.format(chOpName)
            continue
        node = nodz.scene().nodes[chOpName]

        #create node output attribute if not already present
        foundAttrIndex = -1
        for attrIndex in range(node.attrCount):
            attrName = node.attrs[attrIndex]
            #print 'AttributeName: ',attrName
            if string.find(attrName, "output") >= 0 :
                foundAttrIndex = attrIndex     
        if foundAttrIndex<0:
            nodz.createAttribute(node=node, name="output: ", index=-1, preset='attr_preset_debug', plug=False, socket=False, dataType=str)
            foundAttrIndex = node.attrCount-1

        #update node output
        attributeString = "output: {}".format(outputValues[chOpName])
        nodz.editAttribute(node, foundAttrIndex, attributeString)

######################################################################
# Test signals
######################################################################

# Nodes
@QtCore.Slot(str)
def on_nodeCreated(nodeName):
    print 'node created : ', nodeName

@QtCore.Slot(str)
def on_nodeDeleted(nodeName):
    print 'node deleted : ', nodeName

@QtCore.Slot(str, str)
def on_nodeEdited(nodeName, newName):
    print 'node edited : {0}, new name : {1}'.format(nodeName, newName)

@QtCore.Slot(str)
def on_nodeSelected(nodesName):
    print 'node selected : ', nodesName

# Attrs
@QtCore.Slot(str, int)
def on_attrCreated(nodeName, attrId):
    print 'attr created : {0} at index : {1}'.format(nodeName, attrId)

@QtCore.Slot(str, int)
def on_attrDeleted(nodeName, attrId):
    print 'attr Deleted : {0} at old index : {1}'.format(nodeName, attrId)

@QtCore.Slot(str, int, int)
def on_attrEdited(nodeName, oldId, newId):
    print 'attr Edited : {0} at old index : {1}, new index : {2}'.format(nodeName, oldId, newId)

# Graph
@QtCore.Slot()
def on_graphSaved():
    print 'graph saved !'

@QtCore.Slot()
def on_graphLoaded():
    print 'graph loaded !'

@QtCore.Slot()
def on_graphCleared():
    print 'graph cleared !'

@QtCore.Slot()
def on_graphEvaluated():
    print 'graph evaluated !'

# Other
@QtCore.Slot(object)
def on_keyPressed(key):
    print 'key pressed : ', key

    if key==49:  #numpad 1
        outputValues = dict()
        outputValues["fullOrientationInputShape"] = random.random()
        outputValues["chOpConverterShape1"] = "<<{} {} {}>>".format(random.random(), random.random(), random.random())
        outputValues["chOpOutputShape1"] = "<<{} {} {}>>".format(random.random(), random.random(), random.random())
        updateChOpsNodzDebugOutput(nodz, outputValues)


nodz.signal_NodeCreated.connect(on_nodeCreated)
nodz.signal_NodeDeleted.connect(on_nodeDeleted)
nodz.signal_NodeEdited.connect(on_nodeEdited)
nodz.signal_NodeSelected.connect(on_nodeSelected)

nodz.signal_AttrCreated.connect(on_attrCreated)
nodz.signal_AttrDeleted.connect(on_attrDeleted)
nodz.signal_AttrEdited.connect(on_attrEdited)

nodz.signal_GraphSaved.connect(on_graphSaved)
nodz.signal_GraphLoaded.connect(on_graphLoaded)
nodz.signal_GraphCleared.connect(on_graphCleared)
nodz.signal_GraphEvaluated.connect(on_graphEvaluated)

nodz.signal_KeyPressed.connect(on_keyPressed)


######################################################################
# Test API
######################################################################

# Graph
#print nodz.evaluateGraph()
#nodz.saveGraph(filePath='Enter your path')

nodz.clearGraph()
#nodz.loadGraph(filePath='testChOpWorldDirToAngle')
nodz.loadGraph(filePath='DEMO_chargingArmy')
nodz.autoLayoutGraph()



# outputValues = dict()
# outputValues["fullOrientationInputShape"] = "5"
# outputValues["chOpConverterShape1"] = "<<5 18 32>>"
# outputValues["chOpOutputShape1"] = "<<3 200 1>>"
# updateChOpsNodzDebugOutput(nodz, outputValues)

# outputValues["fullOrientationInputShape"] = "6"
# updateChOpsNodzDebugOutput(nodz, outputValues)

# outputValues["chOpConverterShape1"] = "<<6 18 32>>"
# updateChOpsNodzDebugOutput(nodz, outputValues)

# outputValues["chOpOutputShape1"] = "<<3 2 1>>"
# updateChOpsNodzDebugOutput(nodz, outputValues)

if app:
    mainWidget = app.activeWindow()

    # command line stand alone test... run our own event loop
    app.exec_()
