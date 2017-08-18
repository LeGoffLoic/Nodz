import os
import re
import json

from glm.Qtpy.Qt import QtGui, QtCore, QtWidgets
import nodz_utils as utils
import nodz_extra


defaultConfigPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'default_config.json')


class Nodz(QtWidgets.QGraphicsView):

    """
    The main view for the node graph representation.

    The node view implements a state pattern to control all the
    different user interactions.

    """

    signal_NodeCreated = QtCore.Signal(object)
    signal_NodeDeleted = QtCore.Signal(object)
    signal_NodeEdited = QtCore.Signal(object, object)
    signal_NodeSelected = QtCore.Signal(object)

    signal_AttrCreated = QtCore.Signal(object, object)
    signal_AttrDeleted = QtCore.Signal(object, object)
    signal_AttrEdited = QtCore.Signal(object, object, object)

    signal_PlugConnected = QtCore.Signal(object, object, object, object)
    signal_PlugDisconnected = QtCore.Signal(object, object, object, object)
    signal_SocketConnected = QtCore.Signal(object, object, object, object)
    signal_SocketDisconnected = QtCore.Signal(object, object, object, object)

    signal_GraphSaved = QtCore.Signal()
    signal_GraphLoaded = QtCore.Signal()
    signal_GraphCleared = QtCore.Signal()
    signal_GraphEvaluated = QtCore.Signal()

    signal_KeyPressed = QtCore.Signal(object)
    signal_Dropped = QtCore.Signal()

    def __init__(self, parent, configPath=defaultConfigPath):
        """
        Initialize the graphics view.

        """
        super(Nodz, self).__init__(parent)

        # Load nodz configuration.
        self.loadConfig(configPath)

        # General data.
        self.gridVisToggle = True
        self.gridSnapToggle = False
        self._nodeSnap = False
        self.selectedNodes = None

        # Connections data.
        self.drawingConnection = False
        self.currentHoveredNode = None
        self.sourceSlot = None

        # Display options.
        self.currentState = 'DEFAULT'
        self.pressedKeys = list()

        # Node creation helper
        self.nodeCreationPopup = None

    def wheelEvent(self, event):
        """
        Zoom in the view with the mouse wheel.

        """
        self.currentState = 'ZOOM_VIEW'
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)

        inFactor = 1.15
        outFactor = 1 / inFactor

        if event.delta() > 0:
            zoomFactor = inFactor
        else:
            zoomFactor = outFactor

        self.scale(zoomFactor, zoomFactor)
        self.currentState = 'DEFAULT'

    def mousePressEvent(self, event):
        """
        Initialize tablet zoom, drag canvas and the selection.

        """
        # Tablet zoom
        if (event.button() == QtCore.Qt.RightButton and
            event.modifiers() == QtCore.Qt.AltModifier):
            self.currentState = 'ZOOM_VIEW'
            self.zoomInitialPos = event.pos()
            self.initMouse = QtGui.QCursor.pos()
            self.initMousePos = event.pos()
            self.setInteractive(False)


        # Drag view
        elif (event.button() == QtCore.Qt.MiddleButton and
              event.modifiers() == QtCore.Qt.AltModifier):
            self.currentState = 'DRAG_VIEW'
            self.prevPos = event.pos()
            self.setCursor(QtCore.Qt.ClosedHandCursor)
            self.setInteractive(False)


        # Rubber band selection
        elif (event.button() == QtCore.Qt.LeftButton and
              event.modifiers() == QtCore.Qt.NoModifier and
              self.scene().itemAt(self.mapToScene(event.pos()), QtGui.QTransform()) is None):
            self.currentState = 'SELECTION'
            self._initRubberband(event.pos())
            self.setInteractive(False)


        # Drag Item
        elif (event.button() == QtCore.Qt.LeftButton and
              event.modifiers() == QtCore.Qt.NoModifier and
              self.scene().itemAt(self.mapToScene(event.pos()), QtGui.QTransform()) is not None):
            self.currentState = 'DRAG_ITEM'
            self.setInteractive(True)


        # Add selection
        elif (event.button() == QtCore.Qt.LeftButton and
              QtCore.Qt.Key_Shift in self.pressedKeys and
              QtCore.Qt.Key_Control in self.pressedKeys):
            self.currentState = 'ADD_SELECTION'
            self._initRubberband(event.pos())
            self.setInteractive(False)


        # Subtract selection
        elif (event.button() == QtCore.Qt.LeftButton and
              event.modifiers() == QtCore.Qt.ControlModifier):
            self.currentState = 'SUBTRACT_SELECTION'
            self._initRubberband(event.pos())
            self.setInteractive(False)


        # Toggle selection
        elif (event.button() == QtCore.Qt.LeftButton and
              event.modifiers() == QtCore.Qt.ShiftModifier):
            self.currentState = 'TOGGLE_SELECTION'
            self._initRubberband(event.pos())
            self.setInteractive(False)


        else:
            self.currentState = 'DEFAULT'

        super(Nodz, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        Update tablet zoom, canvas dragging and selection.

        """
        # Zoom.
        if self.currentState == 'ZOOM_VIEW':
            offset = self.zoomInitialPos.x() - event.pos().x()

            if offset > self.previousMouseOffset:
                self.previousMouseOffset = offset
                self.zoomDirection = -1
                self.zoomIncr -= 1

            elif offset == self.previousMouseOffset:
                self.previousMouseOffset = offset
                if self.zoomDirection == -1:
                    self.zoomDirection = -1
                else:
                    self.zoomDirection = 1

            else:
                self.previousMouseOffset = offset
                self.zoomDirection = 1
                self.zoomIncr += 1

            if self.zoomDirection == 1:
                zoomFactor = 1.03
            else:
                zoomFactor = 1 / 1.03

            # Perform zoom and re-center on initial click position.
            pBefore = self.mapToScene(self.initMousePos)
            self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)
            self.scale(zoomFactor, zoomFactor)
            pAfter = self.mapToScene(self.initMousePos)
            diff = pAfter - pBefore

            self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
            self.translate(diff.x(), diff.y())

        # Drag canvas.
        elif self.currentState == 'DRAG_VIEW':
            offset = self.prevPos - event.pos()
            self.prevPos = event.pos()
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() + offset.y())
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + offset.x())

        # RuberBand selection.
        elif (self.currentState == 'SELECTION' or
              self.currentState == 'ADD_SELECTION' or
              self.currentState == 'SUBTRACT_SELECTION' or
              self.currentState == 'TOGGLE_SELECTION'):
            self.rubberband.setGeometry(QtCore.QRect(self.origin, event.pos()).normalized())

        super(Nodz, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Apply tablet zoom, dragging and selection.

        """
        # Zoom the View.
        if self.currentState == '.ZOOM_VIEW':
            self.offset = 0
            self.zoomDirection = 0
            self.zoomIncr = 0
            self.setInteractive(True)


        # Drag View.
        elif self.currentState == 'DRAG_VIEW':
            self.setCursor(QtCore.Qt.ArrowCursor)
            self.setInteractive(True)


        # Selection.
        elif self.currentState == 'SELECTION':
            self.rubberband.setGeometry(QtCore.QRect(self.origin,
                                                     event.pos()).normalized())
            painterPath = self._releaseRubberband()
            self.setInteractive(True)
            self.scene().setSelectionArea(painterPath)


        # Add Selection.
        elif self.currentState == 'ADD_SELECTION':
            self.rubberband.setGeometry(QtCore.QRect(self.origin,
                                                     event.pos()).normalized())
            painterPath = self._releaseRubberband()
            self.setInteractive(True)
            for item in self.scene().items(painterPath):
                item.setSelected(True)


        # Subtract Selection.
        elif self.currentState == 'SUBTRACT_SELECTION':
            self.rubberband.setGeometry(QtCore.QRect(self.origin,
                                                     event.pos()).normalized())
            painterPath = self._releaseRubberband()
            self.setInteractive(True)
            for item in self.scene().items(painterPath):
                item.setSelected(False)


        # Toggle Selection
        elif self.currentState == 'TOGGLE_SELECTION':
            self.rubberband.setGeometry(QtCore.QRect(self.origin,
                                                     event.pos()).normalized())
            painterPath = self._releaseRubberband()
            self.setInteractive(True)
            for item in self.scene().items(painterPath):
                if item.isSelected():
                    item.setSelected(False)
                else:
                    item.setSelected(True)

        self.currentState = 'DEFAULT'

        super(Nodz, self).mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        """
        Save pressed key and apply shortcuts.

        Shortcuts are:
        DEL - Delete the selected nodes
        F - Focus view on the selection

        """
        if event.key() not in self.pressedKeys:
            self.pressedKeys.append(event.key())

        if event.key() == QtCore.Qt.Key_Delete:
            self._deleteSelectedNodes()

        if event.key() == QtCore.Qt.Key_F:
            self._focus()

        if event.key() == QtCore.Qt.Key_S:
            self._nodeSnap = True

        if event.key() == QtCore.Qt.Key_Tab:
            self.nodeCreationPopup.popup()

        if event.key() == QtCore.Qt.Key_Escape:
            self.nodeCreationPopup.popdown()

        # Emit signal.
        self.signal_KeyPressed.emit(event.key())

    def keyReleaseEvent(self, event):
        """
        Clear the key from the pressed key list.

        """
        if event.key() == QtCore.Qt.Key_S:
            self._nodeSnap = False

        if event.key() in self.pressedKeys:
            self.pressedKeys.remove(event.key())

    def _initRubberband(self, position):
        """
        Initialize the rubber band at the given position.

        """
        self.rubberBandStart = position
        self.origin = position
        self.rubberband.setGeometry(QtCore.QRect(self.origin, QtCore.QSize()))
        self.rubberband.show()

    def _releaseRubberband(self):
        """
        Hide the rubber band and return the path.

        """
        painterPath = QtGui.QPainterPath()
        rect = self.mapToScene(self.rubberband.geometry())
        painterPath.addPolygon(rect)
        self.rubberband.hide()
        return painterPath

    def _focus(self):
        """
        Center on selected nodes or all of them if no active selection.

        """
        if self.scene().selectedItems():
            itemsArea = self._getSelectionBoundingbox()
            self.fitInView(itemsArea, QtCore.Qt.KeepAspectRatio)
        else:
            itemsArea = self.scene().itemsBoundingRect()
            self.fitInView(itemsArea, QtCore.Qt.KeepAspectRatio)

    def _getSelectionBoundingbox(self):
        """
        Return the bounding box of the selection.

        """
        bbx_min = None
        bbx_max = None
        bby_min = None
        bby_max = None
        bbw = 0
        bbh = 0
        for item in self.scene().selectedItems():
            pos = item.scenePos()
            x = pos.x()
            y = pos.y()
            w = x + item.boundingRect().width()
            h = y + item.boundingRect().height()

            # bbx min
            if bbx_min is None:
                bbx_min = x
            elif x < bbx_min:
                bbx_min = x
            # end if

            # bbx max
            if bbx_max is None:
                bbx_max = w
            elif w > bbx_max:
                bbx_max = w
            # end if

            # bby min
            if bby_min is None:
                bby_min = y
            elif y < bby_min:
                bby_min = y
            # end if

            # bby max
            if bby_max is None:
                bby_max = h
            elif h > bby_max:
                bby_max = h
            # end if
        # end if
        bbw = bbx_max - bbx_min
        bbh = bby_max - bby_min
        return QtCore.QRectF(QtCore.QRect(bbx_min, bby_min, bbw, bbh))

    def _deleteSelectedNodes(self):
        """
        Delete selected nodes.

        """
        selected_nodes = list()
        for node in self.scene().selectedItems():
            if type(node) is NodeItem:
                selected_nodes.append(node.name)
            node._remove()

        # Emit signal.
        self.signal_NodeDeleted.emit(selected_nodes)

    def _returnSelection(self):
        """
        Wrapper to return selected items.

        """
        self.selectedNodes = list()
        if self.scene().selectedItems():
            for node in self.scene().selectedItems():
                if type(node) is NodeItem:
                    self.selectedNodes.append(node.name)

        # Emit signal.
        self.signal_NodeSelected.emit(self.selectedNodes)


    ##################################################################
    # API
    ##################################################################

    def loadConfig(self, filePath):
        """
        Set a specific configuration for this instance of Nodz.

        :type  filePath: str.
        :param filePath: The path to the config file that you want to
                         use.

        """
        self.config = utils._loadConfig(filePath)

    def initialize(self):
        """
        Setup the view's behavior.

        """
        # Setup view.
        config = self.config
        self.setRenderHint(QtGui.QPainter.Antialiasing, config['antialiasing'])
        self.setRenderHint(QtGui.QPainter.TextAntialiasing, config['antialiasing'])
        self.setRenderHint(QtGui.QPainter.HighQualityAntialiasing, config['antialiasing_boost'])
        self.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, config['smooth_pixmap'])
        self.setRenderHint(QtGui.QPainter.NonCosmeticDefaultPen, True)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.rubberband = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Rectangle, self)

        # Setup scene.
        scene = NodeScene(self)
        sceneWidth = config['scene_width']
        sceneHeight = config['scene_height']
        scene.setSceneRect(0, 0, sceneWidth, sceneHeight)
        self.setScene(scene)

        # Tablet zoom.
        self.previousMouseOffset = 0
        self.zoomDirection = 0
        self.zoomIncr = 0

        # Connect signals.
        self.scene().selectionChanged.connect(self._returnSelection)

    def initNodeCreationHelper(self, completerNodeList=[], nodeCreatorCallback=None):
        """
        Setup the node's creation helper that is available from the tab key

        """
        self.nodeCreationPopup = nodz_extra.QtPopupLineEditWidget(self.scene().views()[0])
        self.nodeCreationPopup.setNodesList(completerNodeList)
        if nodeCreatorCallback is not None:
            self.nodeCreationPopup.nodeCreator = nodeCreatorCallback

    # NODES
    def createNode(self, name='default', preset='node_default', position=None, alternate=True):
        """
        Create a new node with a given name, position and color.

        :type  name: str.
        :param name: The name of the node. The name has to be unique
                     as it is used as a key to store the node object.

        :type  preset: str.
        :param preset: The name of graphical preset in the config file.

        :type  position: QtCore.QPoint.
        :param position: The position of the node once created. If None,
                         it will be created at the center of the scene.

        :type  alternate: bool.
        :param alternate: The attribute color alternate state, if True,
                          every 2 attribute the color will be slightly
                          darker.

        :return : The created node

        """
        # Check for name clashes
        if name in self.scene().nodes.keys():
            print 'A node with the same name already exists : {0}'.format(name)
            print 'Node creation aborted !'
            return
        else:
            nodeItem = NodeItem(name=name, alternate=alternate, preset=preset,
                                config=self.config)

            # Store node in scene.
            self.scene().nodes[name] = nodeItem

            if not position:
                # Get the center of the view.
                position = self.mapToScene(self.viewport().rect().center())

            # Set node position.
            self.scene().addItem(nodeItem)
            nodeItem.setPos(position - nodeItem.nodeCenter)

            # Emit signal.
            self.signal_NodeCreated.emit(name)

            return nodeItem

    def deleteNode(self, node):
        """
        Delete the specified node from the view.

        :type  node: class.
        :param node: The node instance that you want to delete.

        """
        if not node in self.scene().nodes.values():
            print 'Node object does not exist !'
            print 'Node deletion aborted !'
            return

        if node in self.scene().nodes.values():
            nodeName = node.name
            node._remove()

            # Emit signal.
            self.signal_NodeDeleted.emit([nodeName])

    def editNode(self, node, newName=None):
        """
        Rename an existing node.

        :type  node: class.
        :param node: The node instance that you want to delete.

        :type  newName: str.
        :param newName: The new name for the given node.

        """
        if not node in self.scene().nodes.values():
            print 'Node object does not exist !'
            print 'Node edition aborted !'
            return

        oldName = node.name

        if newName != None:
            # Check for name clashes
            if newName in self.scene().nodes.keys():
                print 'A node with the same name already exists : {0}'.format(newName)
                print 'Node edition aborted !'
                return
            else:
                node.name = newName

        # Replace node data.
        self.scene().nodes[newName] = self.scene().nodes[oldName]
        self.scene().nodes.pop(oldName)

        # Store new node name in the connections
        if node.sockets:
            for socket in node.sockets.values():
                for connection in socket.connections:
                    connection.socketNode = newName

        if node.plugs:
            for plug in node.plugs.values():
                for connection in plug.connections:
                    connection.plugNode = newName

        node.update()

        # Emit signal.
        self.signal_NodeEdited.emit(oldName, newName)


    # ATTRS
    def createAttribute(self, node, name='default', index=-1, preset='attr_default', plug=True, socket=True, dataType=None):
        """
        Create a new attribute with a given name.

        :type  node: class.
        :param node: The node instance that you want to delete.

        :type  name: str.
        :param name: The name of the attribute. The name has to be
                     unique as it is used as a key to store the node
                     object.

        :type  index: int.
        :param index: The index of the attribute in the node.

        :type  preset: str.
        :param preset: The name of graphical preset in the config file.

        :type  plug: bool.
        :param plug: Whether or not this attribute can emit connections.

        :type  socket: bool.
        :param socket: Whether or not this attribute can receive
                       connections.

        :type  dataType: type.
        :param dataType: Type of the data represented by this attribute
                         in order to highlight attributes of the same
                         type while performing a connection.

        """
        if not node in self.scene().nodes.values():
            print 'Node object does not exist !'
            print 'Attribute creation aborted !'
            return

        if name in node.attrs:
            print 'An attribute with the same name already exists : {0}'.format(name)
            print 'Attribute creation aborted !'
            return

        node._createAttribute(name=name, index=index, preset=preset, plug=plug, socket=socket, dataType=dataType)

        # Emit signal.
        self.signal_AttrCreated.emit(node.name, index)

    def deleteAttribute(self, node, index):
        """
        Delete the specified attribute.

        :type  node: class.
        :param node: The node instance that you want to delete.

        :type  index: int.
        :param index: The index of the attribute in the node.

        """
        if not node in self.scene().nodes.values():
            print 'Node object does not exist !'
            print 'Attribute deletion aborted !'
            return

        node._deleteAttribute(index)

        # Emit signal.
        self.signal_AttrDeleted.emit(node.name, index)

    def editAttribute(self, node, index, newName=None, newIndex=None):
        """
        Edit the specified attribute.

        :type  node: class.
        :param node: The node instance that you want to delete.

        :type  index: int.
        :param index: The index of the attribute in the node.

        :type  newName: str.
        :param newName: The new name for the given attribute.

        :type  newIndex: int.
        :param newIndex: The index for the given attribute.

        """
        if not node in self.scene().nodes.values():
            print 'Node object does not exist !'
            print 'Attribute creation aborted !'
            return

        if newName != None:
            if newName in node.attrs:
                print 'An attribute with the same name already exists : {0}'.format(newName)
                print 'Attribute edition aborted !'
                return
            else:
                oldName = node.attrs[index]

            # Rename in the slot item(s).
            if node.attrsData[oldName]['plug']:
                node.plugs[oldName].attribute = newName
                node.plugs[newName] = node.plugs[oldName]
                node.plugs.pop(oldName)
                for connection in node.plugs[newName].connections:
                    connection.plugAttr = newName

            if node.attrsData[oldName]['socket']:
                node.sockets[oldName].attribute = newName
                node.sockets[newName] = node.sockets[oldName]
                node.sockets.pop(oldName)
                for connection in node.sockets[newName].connections:
                    connection.socketAttr = newName

            # Replace attribute data.
            node.attrsData[oldName]['name'] = newName
            node.attrsData[newName] = node.attrsData[oldName]
            node.attrsData.pop(oldName)
            node.attrs[index] = newName

        if isinstance(newIndex, int):
            attrName = node.attrs[index]

            utils._swapListIndices(node.attrs, index, newIndex)

            # Refresh connections.
            for plug in node.plugs.values():
                plug.update()
                if plug.connections:
                    for connection in plug.connections:
                        if isinstance(connection.source, PlugItem):
                            connection.source = plug
                            connection.source_point = plug.center()
                        else:
                            connection.target = plug
                            connection.target_point = plug.center()
                        if newName:
                            connection.plugAttr = newName
                        connection.updatePath()

            for socket in node.sockets.values():
                socket.update()
                if socket.connections:
                    for connection in socket.connections:
                        if isinstance(connection.source, SocketItem):
                            connection.source = socket
                            connection.source_point = socket.center()
                        else:
                            connection.target = socket
                            connection.target_point = socket.center()
                        if newName:
                            connection.socketAttr = newName
                        connection.updatePath()

            self.scene().update()

        node.update()

        # Emit signal.
        if newIndex:
            self.signal_AttrEdited.emit(node.name, index, newIndex)
        else:
            self.signal_AttrEdited.emit(node.name, index, index)


    # GRAPH
    def autoLayoutGraph(self, nodes = None, margin = 50):
        """
        Auto set nodes positions in the graph according to their connections.

        """

        nodeWidth = 300    #default value, will be replaced by node.baseWidth + margin when iterating on the first node
        sceneNodes = self.scene().nodes.keys()
        if (nodes is None) or len(nodes)==0:
            nodes = sceneNodes
        rootNodes = []
        alreadyVisitedNodes = []

        # root nodes (without connection on the plug)
        for nodeName in sceneNodes:
            node = self.scene().nodes[nodeName]
            if node is not None:
                nodeWidth = node.baseWidth + margin
                connectionCount=0
                isRoot = True
                for plug in node.plugs.values():
                    isRoot &= (len(plug.connections)==0)
                if isRoot:
                    rootNodes.append(node)
        
        maxGraphWidth = 0
        rootGraphs = [[[0 for x in range(0)] for y in range(0)] for z in range(0)]
        for rootNode in rootNodes:
            rootGraph = [[0 for x in range(0)] for y in range(0)]
            rootGraph.append([rootNode])
            
            currentGraphLevel = 0
            doNextGraphLevel = True
            while(doNextGraphLevel):
                doNextGraphLevel = False
                for nodeI in range(len(rootGraph[currentGraphLevel])):
                    node = rootGraph[currentGraphLevel][nodeI]
                    for attr in node.attrs:
                        if attr in node.sockets:
                            socket = node.sockets[attr]
                            for connection in socket.connections:
                                node = connection.plugItem.parentItem()
                                if (node not in alreadyVisitedNodes):
                                    alreadyVisitedNodes.append(node)

                                    if len(rootGraph)<=(currentGraphLevel+1):
                                        emptyArray = []
                                        rootGraph.append(emptyArray)
                                    rootGraph[currentGraphLevel+1].append(connection.plugItem.parentItem())
                                    doNextGraphLevel = True
                currentGraphLevel+=1

            graphWidth = len(rootGraph) * (nodeWidth+margin)
            maxGraphWidth = max(graphWidth, maxGraphWidth)
            rootGraphs.append(rootGraph)

        #update scene rect if needed
        if maxGraphWidth > self.scene().width():
            sceneRect = self.scene().sceneRect()
            sceneRect.setWidth(maxGraphWidth)
            self.scene().setSceneRect(sceneRect)

        alreadyVisitedNodes = []
        baseYpos = margin
        for rootGraph in rootGraphs:
            #set positions...
            currentXpos = max(0, 0.5*(self.scene().width()-maxGraphWidth)) + maxGraphWidth-nodeWidth  #middle of the view
            nextBaseYpos = baseYpos
            for nodesAtLevel in rootGraph:
                currentYpos = baseYpos
                for node in nodesAtLevel:
                    if len(node.plugs)>0:
                        if len(node.plugs.values()[0].connections)>0:
                            parentPosition = node.plugs.values()[0].connections[0].socketItem.parentItem().pos()
                            currentXpos = parentPosition.x() - nodeWidth
                            #currentYpos = parentPosition.y()
                    if (node not in alreadyVisitedNodes) and (node.name in nodes):
                        alreadyVisitedNodes.append(node)
                        node_pos = QtCore.QPointF(currentXpos, currentYpos)
                        node.setPos(node_pos)

                    currentYpos += node.height + margin
                    nextBaseYpos = max(nextBaseYpos, currentYpos)
                currentXpos -= nodeWidth
            baseYpos = nextBaseYpos

        self.scene().updateScene()

    def saveGraph(self, filePath='path'):
        """
        Get all the current graph infos and store them in a .json file
        at the given location.

        :type  filePath: str.
        :param filePath: The path where you want to save your graph at.

        """
        data = dict()

        # Store nodes data.
        data['NODES'] = dict()

        nodes = self.scene().nodes.keys()
        for node in nodes:
            nodeInst = self.scene().nodes[node]
            preset = nodeInst.nodePreset
            nodeAlternate = nodeInst.alternate

            data['NODES'][node] = {'preset': preset,
                                   'position': [nodeInst.pos().x(), nodeInst.pos().y()],
                                   'alternate': nodeAlternate,
                                   'attributes': []}

            attrs = nodeInst.attrs
            for attr in attrs:
                attrData = nodeInst.attrsData[attr]

                # serialize dataType if needed.
                if isinstance(attrData['dataType'], type):
                    attrData['dataType'] = str(attrData['dataType'])

                data['NODES'][node]['attributes'].append(attrData)


        # Store connections data.
        data['CONNECTIONS'] = self.evaluateGraph()


        # Save data.
        try:
            utils._saveData(filePath=filePath, data=data)
        except:
            print 'Invalid path : {0}'.format(filePath)
            print 'Save aborted !'
            return False

        # Emit signal.
        self.signal_GraphSaved.emit()

    def loadGraph(self, filePath='path'):
        """
        Get all the stored info from the .json file at the given location
        and recreate the graph as saved.

        :type  filePath: str.
        :param filePath: The path where you want to load your graph from.

        """
        # Load data.
        if os.path.exists(filePath):
            data = utils._loadData(filePath=filePath)
        else:
            print 'Invalid path : {0}'.format(filePath)
            print 'Load aborted !'
            return False

        # Apply nodes data.
        nodesData = data['NODES']
        nodesName = nodesData.keys()

        for name in nodesName:
            preset = nodesData[name]['preset']
            position = nodesData[name]['position']
            position = QtCore.QPointF(position[0], position[1])
            alternate = nodesData[name]['alternate']

            node = self.createNode(name=name,
                                   preset=preset,
                                   position=position,
                                   alternate=alternate)

            # Apply attributes data.
            attrsData = nodesData[name]['attributes']

            for attrData in attrsData:
                index = attrsData.index(attrData)
                name = attrData['name']
                plug = attrData['plug']
                socket = attrData['socket']
                preset = attrData['preset']
                dataType = attrData['dataType']

                # un-serialize data type if needed
                if (isinstance(dataType, unicode) and dataType.find('<') == 0):
                    dataType = eval(str(dataType.split('\'')[1]))

                self.createAttribute(node=node,
                                     name=name,
                                     index=index,
                                     preset=preset,
                                     plug=plug,
                                     socket=socket,
                                     dataType=dataType)


        # Apply connections data.
        connectionsData = data['CONNECTIONS']

        for connection in connectionsData:
            source = connection[0]
            sourceNode = source.split('.')[0]
            sourceAttr = source.split('.')[1]

            target = connection[1]
            targetNode = target.split('.')[0]
            targetAttr = target.split('.')[1]

            self.createConnection(sourceNode, sourceAttr,
                                  targetNode, targetAttr)

        self.scene().update()

        # Emit signal.
        self.signal_GraphLoaded.emit()

    def createConnection(self, sourceNode, sourceAttr, targetNode, targetAttr):
        plug = self.scene().nodes[sourceNode].plugs[sourceAttr]
        socket = self.scene().nodes[targetNode].sockets[targetAttr]

        connection = ConnectionItem(plug.center(), socket.center(), plug, socket)

        connection.plugNode = plug.parentItem().name
        connection.plugAttr = plug.attribute
        connection.socketNode = socket.parentItem().name
        connection.socketAttr = socket.attribute

        plug.connect(socket, connection)
        socket.connect(plug, connection)

        connection.updatePath()

        self.scene().addItem(connection)

    def evaluateGraph(self):
        """
        Create a list of connection tuples.
        [("sourceNode.attribute", "TargetNode.attribute"), ...]

        """
        scene = self.scene()

        data = list()

        for item in scene.items():
            if isinstance(item, ConnectionItem):
                connection = item

                data.append(connection._outputConnectionData())

        # Emit Signal
        self.signal_GraphEvaluated.emit()

        return data

    def clearGraph(self):
        """
        Clear the graph.

        """
        self.scene().clear()
        self.scene().nodes = dict()

        # Emit signal.
        self.signal_GraphCleared.emit()

    ##################################################################
    # END API
    ##################################################################


class NodeScene(QtWidgets.QGraphicsScene):

    """
    The scene displaying all the nodes.

    """

    def __init__(self, parent):
        """
        Initialize the class.

        """
        super(NodeScene, self).__init__(parent)

        # General.
        self.gridSize = parent.config['grid_size']

        # Nodes storage.
        self.nodes = dict()

    def dragEnterEvent(self, event):
        """
        Make the dragging of nodes into the scene possible.

        """
        event.setDropAction(QtCore.Qt.MoveAction)
        event.accept()

    def dragMoveEvent(self, event):
        """
        Make the dragging of nodes into the scene possible.

        """
        event.setDropAction(QtCore.Qt.MoveAction)
        event.accept()

    def dropEvent(self, event):
        """
        Create a node from the dropped item.

        """
        # Emit signal.
        self.signal_Dropped.emit(event.scenePos())

        event.accept()

    def drawBackground(self, painter, rect):
        """
        Draw a grid in the background.

        """
        if self.views()[0].gridVisToggle:
            leftLine = rect.left() - rect.left() % self.gridSize
            topLine = rect.top() - rect.top() % self.gridSize
            lines = list()

            i = int(leftLine)
            while i < int(rect.right()):
                lines.append(QtCore.QLineF(i, rect.top(), i, rect.bottom()))
                i += self.gridSize

            u = int(topLine)
            while u < int(rect.bottom()):
                lines.append(QtCore.QLineF(rect.left(), u, rect.right(), u))
                u += self.gridSize

            self.pen = QtGui.QPen()
            config = self.parent().config
            self.pen.setColor(utils._convertDataToColor(config['grid_color']))
            self.pen.setWidth(0)
            painter.setPen(self.pen)
            painter.drawLines(lines)

    def updateScene(self):
        """
        Update the connections position.

        """
        for connection in [i for i in self.items() if isinstance(i, ConnectionItem)]:
            connection.target_point = connection.target.center()
            connection.source_point = connection.source.center()
            connection.updatePath()


class NodeItem(QtWidgets.QGraphicsItem):

    """
    A graphic representation of a node containing attributes.

    """

    def __init__(self, name, alternate, preset, config):
        """
        Initialize the class.

        :type  name: str.
        :param name: The name of the node. The name has to be unique
                     as it is used as a key to store the node object.

        :type  alternate: bool.
        :param alternate: The attribute color alternate state, if True,
                          every 2 attribute the color will be slightly
                          darker.

        :type  preset: str.
        :param preset: The name of graphical preset in the config file.

        """
        super(NodeItem, self).__init__()

        self.setZValue(1)

        # Storage
        self.name = name
        self.alternate = alternate
        self.nodePreset = preset
        self.attrPreset = None

        # Attributes storage.
        self.attrs = list()
        self.attrsData = dict()
        self.attrCount = 0
        self.currentDataType = None

        self.plugs = dict()
        self.sockets = dict()

        # Methods.
        self._createStyle(config)

    @property
    def height(self):
        """
        Increment the final height of the node every time an attribute
        is created.

        """
        if self.attrCount > 0:
            return (self.baseHeight +
                    self.attrHeight * self.attrCount +
                    self.border +
                    0.5 * self.radius)
        else:
            return self.baseHeight

    @property
    def pen(self):
        """
        Return the pen based on the selection state of the node.

        """
        if self.isSelected():
            return self._penSel
        else:
            return self._pen

    def _createStyle(self, config):
        """
        Read the node style from the configuration file.

        """
        self.setAcceptHoverEvents(True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)

        # Dimensions.
        self.baseWidth  = config['node_width']
        self.baseHeight = config['node_height']
        self.attrHeight = config['node_attr_height']
        self.border = config['node_border']
        self.radius = config['node_radius']

        self.nodeCenter = QtCore.QPointF()
        self.nodeCenter.setX(self.baseWidth / 2.0)
        self.nodeCenter.setY(self.height / 2.0)

        self._brush = QtGui.QBrush()
        self._brush.setStyle(QtCore.Qt.SolidPattern)
        self._brush.setColor(utils._convertDataToColor(config[self.nodePreset]['bg']))

        self._pen = QtGui.QPen()
        self._pen.setStyle(QtCore.Qt.SolidLine)
        self._pen.setWidth(self.border)
        self._pen.setColor(utils._convertDataToColor(config[self.nodePreset]['border']))

        self._penSel = QtGui.QPen()
        self._penSel.setStyle(QtCore.Qt.SolidLine)
        self._penSel.setWidth(self.border)
        self._penSel.setColor(utils._convertDataToColor(config[self.nodePreset]['border_sel']))

        self._textPen = QtGui.QPen()
        self._textPen.setStyle(QtCore.Qt.SolidLine)
        self._textPen.setColor(utils._convertDataToColor(config[self.nodePreset]['text']))

        self._nodeTextFont = QtGui.QFont(config['node_font'], config['node_font_size'], QtGui.QFont.Bold)
        self._attrTextFont = QtGui.QFont(config['attr_font'], config['attr_font_size'], QtGui.QFont.Normal)

        self._attrBrush = QtGui.QBrush()
        self._attrBrush.setStyle(QtCore.Qt.SolidPattern)

        self._attrBrushAlt = QtGui.QBrush()
        self._attrBrushAlt.setStyle(QtCore.Qt.SolidPattern)

        self._attrPen = QtGui.QPen()
        self._attrPen.setStyle(QtCore.Qt.SolidLine)

    def _createAttribute(self, name, index, preset, plug, socket, dataType):
        """
        Create an attribute by expanding the node, adding a label and
        connection items.

        :type  name: str.
        :param name: The name of the attribute. The name has to be
                     unique as it is used as a key to store the node
                     object.

        :type  index: int.
        :param index: The index of the attribute in the node.

        :type  preset: str.
        :param preset: The name of graphical preset in the config file.

        :type  plug: bool.
        :param plug: Whether or not this attribute can emit connections.

        :type  socket: bool.
        :param socket: Whether or not this attribute can receive
                       connections.

        :type  dataType: type.
        :param dataType: Type of the data represented by this attribute
                         in order to highlight attributes of the same
                         type while performing a connection.

        """
        if name in self.attrs:
            print 'An attribute with the same name already exists on this node : {0}'.format(name)
            print 'Attribute creation aborted !'
            return

        self.attrPreset = preset

        # Create a plug connection item.
        if plug:
            plugInst = PlugItem(parent=self,
                                attribute=name,
                                index=self.attrCount,
                                preset=preset,
                                dataType=dataType)

            self.plugs[name] = plugInst

        # Create a socket connection item.
        if socket:
            socketInst = SocketItem(parent=self,
                                    attribute=name,
                                    index=self.attrCount,
                                    preset=preset,
                                    dataType=dataType)

            self.sockets[name] = socketInst

        self.attrCount += 1

        # Add the attribute based on its index.
        if index == -1 or index > self.attrCount:
            self.attrs.append(name)
        else:
            self.attrs.insert(index, name)

        # Store attr data.
        self.attrsData[name] = {'name': name,
                                'socket': socket,
                                'plug': plug,
                                'preset': preset,
                                'dataType': dataType}

        # Update node height.
        self.update()

    def _deleteAttribute(self, index):
        """
        Remove an attribute by reducing the node, removing the label
        and the connection items.

        :type  index: int.
        :param index: The index of the attribute in the node.

        """
        name = self.attrs[index]

        # Remove socket and its connections.
        if name in self.sockets.keys():
            for connection in self.sockets[name].connections:
                connection._remove()

            self.scene().removeItem(self.sockets[name])
            self.sockets.pop(name)

        # Remove plug and its connections.
        if name in self.plugs.keys():
            for connection in self.plugs[name].connections:
                connection._remove()

            self.scene().removeItem(self.plugs[name])
            self.plugs.pop(name)

        # Reduce node height.
        if self.attrCount > 0:
            self.attrCount -= 1

        # Remove attribute from node.
        if name in self.attrs:
            self.attrs.remove(name)

        self.update()

    def _remove(self):
        """
        Remove this node instance from the scene.

        Make sure that all the connections to this node are also removed
        in the process

        """
        self.scene().nodes.pop(self.name)

        # Remove all sockets connections.
        for socket in self.sockets.values():
            for connection in socket.connections:
                connection._remove()

        # Remove all plugs connections.
        for plug in self.plugs.values():
            for connection in plug.connections:
                connection._remove()

        # Remove node.
        scene = self.scene()
        scene.removeItem(self)
        scene.update()

    def boundingRect(self):
        """
        The bounding rect based on the width and height variables.

        """
        rect = QtCore.QRect(0, 0, self.baseWidth, self.height)
        rect = QtCore.QRectF(rect)
        return rect

    def shape(self):
        """
        The shape of the item.

        """
        path = QtGui.QPainterPath()
        path.addRect(self.boundingRect())
        return path

    def paint(self, painter, option, widget):
        """
        Paint the node and attributes.

        """
        # Node base.
        painter.setBrush(self._brush)
        painter.setPen(self.pen)

        painter.drawRoundedRect(0, 0,
                                self.baseWidth,
                                self.height,
                                self.radius,
                                self.radius)

        # Node label.
        painter.setPen(self._textPen)
        painter.setFont(self._nodeTextFont)

        metrics = QtGui.QFontMetrics(painter.font())
        text_width = metrics.boundingRect(self.name).width() + 14
        text_height = metrics.boundingRect(self.name).height() + 14
        margin = (text_width - self.baseWidth) * 0.5
        textRect = QtCore.QRect(-margin,
                                -text_height,
                                text_width,
                                text_height)

        painter.drawText(textRect,
                         QtCore.Qt.AlignCenter,
                         self.name)


        # Attributes.
        offset = 0
        for attr in self.attrs:
            nodzInst = self.scene().views()[0]
            config = nodzInst.config

            # Attribute rect.
            rect = QtCore.QRect(self.border / 2,
                                self.baseHeight - self.radius + offset,
                                self.baseWidth - self.border,
                                self.attrHeight)



            attrData = self.attrsData[attr]
            name = attr

            preset = attrData['preset']


            # Attribute base.
            self._attrBrush.setColor(utils._convertDataToColor(config[preset]['bg']))
            if self.alternate:
                self._attrBrushAlt.setColor(utils._convertDataToColor(config[preset]['bg'], True, config['alternate_value']))

            self._attrPen.setColor(utils._convertDataToColor([0, 0, 0, 0]))
            painter.setPen(self._attrPen)
            painter.setBrush(self._attrBrush)
            if (offset / self.attrHeight) % 2:
                painter.setBrush(self._attrBrushAlt)

            painter.drawRect(rect)

            # Attribute label.
            painter.setPen(utils._convertDataToColor(config[preset]['text']))
            painter.setFont(self._attrTextFont)

            # Search non-connectable attributes.
            if nodzInst.drawingConnection:
                if self == nodzInst.currentHoveredNode:
                    if (attrData['dataType'] != nodzInst.sourceSlot.dataType or
                        (nodzInst.sourceSlot.slotType == 'plug' and attrData['socket'] == False or
                         nodzInst.sourceSlot.slotType == 'socket' and attrData['plug'] == False)):
                        # Set non-connectable attributes color.
                        painter.setPen(utils._convertDataToColor(config['non_connectable_color']))



            painter.drawText(QtCore.QRect(0.5 + 10,
                                          self.baseHeight-self.radius+(self.attrHeight/4)+offset,
                                          self.baseWidth - 20,
                                          self.attrHeight),
                                            0.5, name)


            offset += self.attrHeight

    def mousePressEvent(self, event):
        """
        Keep the selected node on top of the others.

        """
        nodes = self.scene().nodes
        for node in nodes.values():
            node.setZValue(1)

        for item in self.scene().items():
            if isinstance(item, ConnectionItem):
                item.setZValue(1)

        self.setZValue(2)

        super(NodeItem, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        .

        """
        if self.scene().views()[0].gridVisToggle:
            if self.scene().views()[0].gridSnapToggle or self.scene().views()[0]._nodeSnap:
                gridSize = self.scene().gridSize

                currentPos = self.mapToScene(event.pos().x() - self.baseWidth / 2,
                                             event.pos().y() - self.height / 2)

                snap_x = (round(currentPos.x() / gridSize) * gridSize) - gridSize/4
                snap_y = (round(currentPos.y() / gridSize) * gridSize) - gridSize/4
                snap_pos = QtCore.QPointF(snap_x, snap_y)
                self.setPos(snap_pos)

                self.scene().updateScene()
            else:
                self.scene().updateScene()
                super(NodeItem, self).mouseMoveEvent(event)

    def hoverLeaveEvent(self, event):
        """
        .

        """
        nodzInst = self.scene().views()[0]

        for item in nodzInst.scene().items():
            if isinstance(item, ConnectionItem):
                item.setZValue(0)

        super(NodeItem, self).hoverLeaveEvent(event)


class SlotItem(QtWidgets.QGraphicsItem):

    """
    The base class for graphics item representing attributes hook.

    """

    def __init__(self, parent, attribute, preset, index, dataType):
        """
        Initialize the class.

        :param parent: The parent item of the slot.
        :type  parent: QtWidgets.QGraphicsItem instance.

        :param attribute: The attribute associated to the slot.
        :type  attribute: String.

        :param index: int.
        :type  index: The index of the attribute in the node.

        :type  preset: str.
        :param preset: The name of graphical preset in the config file.

        :param dataType: The data type associated to the attribute.
        :type  dataType: Type.

        """
        super(SlotItem, self).__init__(parent)

        # Status.
        self.setAcceptHoverEvents(True)

        # Storage.
        self.slotType = None
        self.attribute = attribute
        self.preset = preset
        self.index = index
        self.dataType = dataType

        # Style.
        self.brush = QtGui.QBrush()
        self.brush.setStyle(QtCore.Qt.SolidPattern)

        self.pen = QtGui.QPen()
        self.pen.setStyle(QtCore.Qt.SolidLine)

        # Connections storage.
        self.connected_slots = list()
        self.newConnection = None
        self.connections = list()

    def mousePressEvent(self, event):
        """
        Start the connection process.

        """
        if event.button() == QtCore.Qt.LeftButton:
            self.newConnection = ConnectionItem(self.center(),
                                                self.mapToScene(event.pos()),
                                                self,
                                                None)

            self.connections.append(self.newConnection)
            self.scene().addItem(self.newConnection)

            nodzInst = self.scene().views()[0]
            nodzInst.drawingConnection = True
            nodzInst.sourceSlot = self
            nodzInst.currentDataType = self.dataType
        else:
            super(SlotItem, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        Update the new connection's end point position.

        """
        nodzInst = self.scene().views()[0]
        config = nodzInst.config
        if nodzInst.drawingConnection:
            mbb = utils._createPointerBoundingBox(pointerPos=event.scenePos().toPoint(),
                                                  bbSize=config['mouse_bounding_box'])

            # Get nodes in pointer's bounding box.
            targets = self.scene().items(mbb)

            if any(isinstance(target, NodeItem) for target in targets):
                if self.parentItem() not in targets:
                    for target in targets:
                        if isinstance(target, NodeItem):
                            nodzInst.currentHoveredNode = target
            else:
                nodzInst.currentHoveredNode = None

            # Set connection's end point.
            self.newConnection.target_point = self.mapToScene(event.pos())
            self.newConnection.updatePath()
        else:
            super(SlotItem, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Apply the connection if target_slot is valid.

        """
        nodzInst = self.scene().views()[0]
        if event.button() == QtCore.Qt.LeftButton:
            nodzInst.drawingConnection = False
            nodzInst.currentDataType = None

            target = self.scene().itemAt(event.scenePos().toPoint(), QtGui.QTransform())

            if not isinstance(target, SlotItem):
                self.newConnection._remove()
                super(SlotItem, self).mouseReleaseEvent(event)
                return

            if target.accepts(self):
                self.newConnection.target = target
                self.newConnection.source = self
                self.newConnection.target_point = target.center()
                self.newConnection.source_point = self.center()

                # Perform the ConnectionItem.
                self.connect(target, self.newConnection)
                target.connect(self, self.newConnection)

                self.newConnection.updatePath()
            else:
                self.newConnection._remove()
        else:
            super(SlotItem, self).mouseReleaseEvent(event)

        nodzInst.currentHoveredNode = None

    def shape(self):
        """
        The shape of the Slot is a circle.

        """
        path = QtGui.QPainterPath()
        path.addRect(self.boundingRect())
        return path

    def paint(self, painter, option, widget):
        """
        Paint the Slot.

        """
        painter.setBrush(self.brush)
        painter.setPen(self.pen)

        nodzInst = self.scene().views()[0]
        config = nodzInst.config
        if nodzInst.drawingConnection:
            if self.parentItem() == nodzInst.currentHoveredNode:
                painter.setBrush(utils._convertDataToColor(config['non_connectable_color']))
                if (self.slotType == nodzInst.sourceSlot.slotType or (self.slotType != nodzInst.sourceSlot.slotType and self.dataType != nodzInst.sourceSlot.dataType)):
                    painter.setBrush(utils._convertDataToColor(config['non_connectable_color']))
                else:
                    _penValid = QtGui.QPen()
                    _penValid.setStyle(QtCore.Qt.SolidLine)
                    _penValid.setWidth(2)
                    _penValid.setColor(QtGui.QColor(255, 255, 255, 255))
                    painter.setPen(_penValid)
                    painter.setBrush(self.brush)

        painter.drawEllipse(self.boundingRect())

    def center(self):
        """
        Return The center of the Slot.

        """
        rect = self.boundingRect()
        center = QtCore.QPointF(rect.x() + rect.width() * 0.5,
                                rect.y() + rect.height() * 0.5)

        return self.mapToScene(center)


class PlugItem(SlotItem):

    """
    A graphics item representing an attribute out hook.

    """

    def __init__(self, parent, attribute, index, preset, dataType):
        """
        Initialize the class.

        :param parent: The parent item of the slot.
        :type  parent: QtWidgets.QGraphicsItem instance.

        :param attribute: The attribute associated to the slot.
        :type  attribute: String.

        :param index: int.
        :type  index: The index of the attribute in the node.

        :type  preset: str.
        :param preset: The name of graphical preset in the config file.

        :param dataType: The data type associated to the attribute.
        :type  dataType: Type.

        """
        super(PlugItem, self).__init__(parent, attribute, preset, index, dataType)

        # Storage.
        self.attributte = attribute
        self.preset = preset
        self.slotType = 'plug'

        # Methods.
        self._createStyle(parent)

    def _createStyle(self, parent):
        """
        Read the attribute style from the configuration file.

        """
        config = parent.scene().views()[0].config
        self.brush = QtGui.QBrush()
        self.brush.setStyle(QtCore.Qt.SolidPattern)
        self.brush.setColor(utils._convertDataToColor(config[self.preset]['plug']))

    def boundingRect(self):
        """
        The bounding rect based on the width and height variables.

        """
        width = height = self.parentItem().attrHeight / 2.0

        nodzInst = self.scene().views()[0]
        config = nodzInst.config

        x = self.parentItem().baseWidth - (width / 2.0)
        y = (self.parentItem().baseHeight - config['node_radius'] +
             self.parentItem().attrHeight / 4 +
             self.parentItem().attrs.index(self.attribute) * self.parentItem().attrHeight)

        rect = QtCore.QRectF(QtCore.QRect(x, y, width, height))
        return rect

    def accepts(self, socket_item):
        """
        Only accepts socket items that belong to other nodes.

        """
        if isinstance(socket_item, SocketItem):
            if self.parentItem() != socket_item.parentItem():
                if socket_item.dataType == self.dataType:
                    if socket_item in self.connected_slots:
                        return False
                    else:
                        return True
            else:
                return False
        else:
            return False

    def connect(self, socket_item, connection):
        """
        Connect to the given socket_item.

        """
        # Populate connection.
        connection.socketItem = socket_item
        connection.plugNode = self.parentItem().name
        connection.plugAttr = self.attribute

        # Add socket to connected slots.
        if socket_item in self.connected_slots:
            self.connected_slots.remove(socket_item)
        self.connected_slots.append(socket_item)

        # Add connection.
        if connection not in self.connections:
            self.connections.append(connection)

        # Emit signal.
        nodzInst = self.scene().views()[0]
        nodzInst.signal_PlugConnected.emit(connection.plugNode, connection.plugAttr, connection.socketNode, connection.socketAttr)

    def disconnect(self, connection):
        """
        Disconnect the given connection from this plug item.

        """
        # Emit signal.
        nodzInst = self.scene().views()[0]
        nodzInst.signal_PlugDisconnected.emit(connection.plugNode, connection.plugAttr, connection.socketNode, connection.socketAttr)

        # Remove connected socket from plug
        if connection.socketItem in self.connected_slots:
            self.connected_slots.remove(connection.socketItem)
        # Remove connection
        self.connections.remove(connection)


class SocketItem(SlotItem):

    """
    A graphics item representing an attribute in hook.

    """

    def __init__(self, parent, attribute, index, preset, dataType):
        """
        Initialize the socket.

        :param parent: The parent item of the slot.
        :type  parent: QtWidgets.QGraphicsItem instance.

        :param attribute: The attribute associated to the slot.
        :type  attribute: String.

        :param index: int.
        :type  index: The index of the attribute in the node.

        :type  preset: str.
        :param preset: The name of graphical preset in the config file.

        :param dataType: The data type associated to the attribute.
        :type  dataType: Type.

        """
        super(SocketItem, self).__init__(parent, attribute, preset, index, dataType)

        # Storage.
        self.attributte = attribute
        self.preset = preset
        self.slotType = 'socket'

        # Methods.
        self._createStyle(parent)

    def _createStyle(self, parent):
        """
        Read the attribute style from the configuration file.

        """
        config = parent.scene().views()[0].config
        self.brush = QtGui.QBrush()
        self.brush.setStyle(QtCore.Qt.SolidPattern)
        self.brush.setColor(utils._convertDataToColor(config[self.preset]['socket']))

    def boundingRect(self):
        """
        The bounding rect based on the width and height variables.

        """
        width = height = self.parentItem().attrHeight / 2.0

        nodzInst = self.scene().views()[0]
        config = nodzInst.config

        x = - width / 2.0
        y = (self.parentItem().baseHeight - config['node_radius'] +
            (self.parentItem().attrHeight/4) +
             self.parentItem().attrs.index(self.attribute) * self.parentItem().attrHeight )

        rect = QtCore.QRectF(QtCore.QRect(x, y, width, height))
        return rect

    def accepts(self, plug_item):
        """
        Only accepts plug items that belong to other nodes.

        """
        if isinstance(plug_item, PlugItem):
            if (self.parentItem() != plug_item.parentItem() and
                len(self.connected_slots) <= 1):
                if plug_item.dataType == self.dataType:
                    if plug_item in self.connected_slots:
                        return False
                    else:
                        return True
            else:
                return False
        else:
            return False

    def connect(self, plug_item, connection):
        """
        Connect to the given plug item.

        """
        if len(self.connected_slots) > 0:
            # Already connected.
            self.connections[0]._remove()
            self.connected_slots = list()

        # Populate connection.
        connection.plugItem = plug_item
        connection.socketNode = self.parentItem().name
        connection.socketAttr = self.attribute

        # Add plug to connected slots.
        self.connected_slots.append(plug_item)

        # Add connection.
        if connection not in self.connections:
            self.connections.append(connection)

        # Emit signal.
        nodzInst = self.scene().views()[0]
        nodzInst.signal_SocketConnected.emit(connection.plugNode, connection.plugAttr, connection.socketNode, connection.socketAttr)

    def disconnect(self, connection):
        """
        Disconnect the given connection from this socket item.

        """
        # Emit signal.
        nodzInst = self.scene().views()[0]
        nodzInst.signal_SocketDisconnected.emit(connection.plugNode, connection.plugAttr, connection.socketNode, connection.socketAttr)

        # Remove connected plugs
        if connection.plugItem in self.connected_slots:
            self.connected_slots.remove(connection.plugItem)
        # Remove connections
        self.connections.remove(connection)


class ConnectionItem(QtWidgets.QGraphicsPathItem):

    """
    A graphics path representing a connection between two attributes.

    """

    def __init__(self, source_point, target_point, source, target):
        """
        Initialize the class.

        :param sourcePoint: Source position of the connection.
        :type  sourcePoint: QPoint.

        :param targetPoint: Target position of the connection
        :type  targetPoint: QPoint.

        :param source: Source item (plug or socket).
        :type  source: class.

        :param target: Target item (plug or socket).
        :type  target: class.

        """
        super(ConnectionItem, self).__init__()

        self.setZValue(1)
        self.lastSelected = False

        # Storage.
        self.socketNode = None
        self.socketAttr = None
        self.plugNode = None
        self.plugAttr = None

        self.source_point = source_point
        self.target_point = target_point
        self.source = source
        self.target = target

        self.plugItem = None
        self.socketItem = None

        self.movable_point = None

        self.data = tuple()

        # Methods.
        self._createStyle()

    @property
    def pen(self):
        """
        Return the pen based on the selection state of the node.

        """
        if self.isSelected():
            return self._penSel
        else:
            return self._pen

    def paint(self, painter, option, widget):
        """
        Paint the node and attributes.

        """
        #handle selection change...
        isSelected = self.isSelected()
        if self.lastSelected != isSelected:
            self.updatePath()
            self.lastSelected = isSelected

        super(ConnectionItem, self).paint(painter, option, widget)

    def _createStyle(self):
        """
        Read the connection style from the configuration file.

        """
        config = self.source.scene().views()[0].config
        self.setAcceptHoverEvents(True)
        self.setZValue(-1)

        self._pen = QtGui.QPen(utils._convertDataToColor(config['connection_color']))
        self._pen.setWidth(config['connection_width'])
        
        #make link selectable + selection style
        self._penSel = QtGui.QPen(utils._convertDataToColor(config['connection_sel_color']))
        self._penSel.setWidth(config['connection_sel_width'])

        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)

    def _outputConnectionData(self):
        """
        .

        """
        return ("{0}.{1}".format(self.plugNode, self.plugAttr),
                "{0}.{1}".format(self.socketNode, self.socketAttr))

    def mousePressEvent(self, event):
        """
        Make connection in front of other items

        """
        nodzInst = self.scene().views()[0]

        for item in nodzInst.scene().items():
            if isinstance(item, ConnectionItem):
                item.setZValue(0)

        super(ConnectionItem, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        Move the Connection with the mouse.

        """
        nodzInst = self.scene().views()[0]
        config = nodzInst.config

        mbb = utils._createPointerBoundingBox(pointerPos=event.scenePos().toPoint(),
                                              bbSize=config['mouse_bounding_box'])

        # Get nodes in pointer's bounding box.
        targets = self.scene().items(mbb)

        if any(isinstance(target, NodeItem) for target in targets):

            if nodzInst.sourceSlot.parentItem() not in targets:
                for target in targets:
                    if isinstance(target, NodeItem):
                        nodzInst.currentHoveredNode = target
        else:
            nodzInst.currentHoveredNode = None

        if self.movable_point == 'target_point':
            self.target_point = event.pos()
        else:
            self.source_point = event.pos()

        self.updatePath()

    def mouseReleaseEvent(self, event):
        """
        Create a Connection if possible, otherwise do nothing.

        """
        nodzInst = self.scene().views()[0]
        nodzInst.drawingConnection = False

        slot = self.scene().itemAt(event.scenePos().toPoint(), QtGui.QTransform())

        if not isinstance(slot, SlotItem):
            self.updatePath()
            super(ConnectionItem, self).mouseReleaseEvent(event)
            return

        if self.movable_point == 'target_point':
            if slot.accepts(self.source):
                # Plug reconnection.
                self.target = slot
                self.target_point = slot.center()
                plug = self.source
                socket = self.target

                # Reconnect.
                socket.connect(plug, self)

                self.updatePath()
            else:
                self._remove()

        else:
            if slot.accepts(self.target):
                # Socket Reconnection
                self.source = slot
                self.source_point = slot.center()
                socket = self.target
                plug = self.source

                # Reconnect.
                plug.connect(socket, self)

                self.updatePath()
            else:
                self._remove()

    def _remove(self):
        """
        Remove this Connection from the scene.

        """
        if self.source is not None:
            self.source.disconnect(self)
        if self.target is not None:
            self.target.disconnect(self)

        scene = self.scene()
        scene.removeItem(self)
        scene.update()

    def updatePath(self):
        """
        Update the path.

        """
        self.setPen(self.pen)

        path = QtGui.QPainterPath()
        path.moveTo(self.source_point)
        dx = (self.target_point.x() - self.source_point.x()) * 0.5
        dy = self.target_point.y() - self.source_point.y()
        ctrl1 = QtCore.QPointF(self.source_point.x() + dx, self.source_point.y() + dy * 0)
        ctrl2 = QtCore.QPointF(self.source_point.x() + dx, self.source_point.y() + dy * 1)
        path.cubicTo(ctrl1, ctrl2, self.target_point)

        self.setPath(path)
