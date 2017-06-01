from Qt import QtCore
import nodz_main

nodz = nodz_main.Nodz(None)
# nodz.loadConfig(filePath='')
nodz.initialize()
nodz.show()


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

# Node A
nodeA = nodz.createNode(name='nodeA', preset='node_preset_1', position=None)

nodz.createAttribute(node=nodeA, name='Aattr1', index=-1, preset='attr_preset_1',
                     plug=True, socket=False, dataType=str)

nodz.createAttribute(node=nodeA, name='Aattr2', index=-1, preset='attr_preset_1',
                     plug=True, socket=False, dataType=int)

nodz.createAttribute(node=nodeA, name='Aattr3', index=-1, preset='attr_preset_2',
                     plug=True, socket=False, dataType=int)

nodz.createAttribute(node=nodeA, name='Aattr4', index=-1, preset='attr_preset_2',
                     plug=True, socket=False, dataType=str)



# Node B
nodeB = nodz.createNode(name='nodeB', preset='node_preset_1')

nodz.createAttribute(node=nodeB, name='Battr1', index=-1, preset='attr_preset_1',
                     plug=True, socket=False, dataType=str)

nodz.createAttribute(node=nodeB, name='Battr2', index=-1, preset='attr_preset_1',
                     plug=True, socket=False, dataType=int)



# Node C
nodeC = nodz.createNode(name='nodeC', preset='node_preset_1')

nodz.createAttribute(node=nodeC, name='Cattr1', index=-1, preset='attr_preset_1',
                     plug=False, socket=True, dataType=str)

nodz.createAttribute(node=nodeC, name='Cattr2', index=-1, preset='attr_preset_1',
                     plug=True, socket=False, dataType=int)

nodz.createAttribute(node=nodeC, name='Cattr3', index=-1, preset='attr_preset_1',
                     plug=True, socket=False, dataType=str)

nodz.createAttribute(node=nodeC, name='Cattr4', index=-1, preset='attr_preset_2',
                     plug=False, socket=True, dataType=str)

nodz.createAttribute(node=nodeC, name='Cattr5', index=-1, preset='attr_preset_2',
                     plug=False, socket=True, dataType=int)

nodz.createAttribute(node=nodeC, name='Cattr6', index=-1, preset='attr_preset_3',
                     plug=True, socket=False, dataType=str)

nodz.createAttribute(node=nodeC, name='Cattr7', index=-1, preset='attr_preset_3',
                     plug=True, socket=False, dataType=str)

nodz.createAttribute(node=nodeC, name='Cattr8', index=-1, preset='attr_preset_3',
                     plug=True, socket=False, dataType=int)


# Please note that this is a local test so once the graph is cleared
# and reloaded, all the local variables are not valid anymore, which
# means the following code to alter nodes won't work but saving/loading/
# clearing/evaluating will.


# Attributes Edition
nodz.editAttribute(node=nodeC, index=0, newName=None, newIndex=-1)
nodz.editAttribute(node=nodeC, index=-1, newName='NewAttrName', newIndex=None)

# Attributes Deletion
nodz.deleteAttribute(node=nodeC, index=-1)


# Nodes Edition
nodz.editNode(node=nodeC, newName='newNodeName')

# Nodes Deletion
nodz.deleteNode(node=nodeC)


# Graph
print nodz.evaluateGraph()

nodz.saveGraph(filePath='Enter your path')

nodz.clearGraph()

nodz.loadGraph(filePath='Enter your path')

nodz.debug()




