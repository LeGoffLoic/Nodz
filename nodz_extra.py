from glm.Qtpy import Qt
from glm.Qtpy.Qt import QtGui, QtCore, QtWidgets
import nodz_main

class QtPopupLineEditWidget(QtWidgets.QLineEdit):

    @staticmethod
    def defaultNodeCreator(nodzInst, nodeName, pos):
        nodzInst.createNode(name=nodeName, position=pos)

    def __init__(self, nodzInst, nodeList=[], nodeCreator=None):
        """
        Initialize the graphics view.

        """
        super(QtPopupLineEditWidget, self).__init__(nodzInst)
        self.nodzInst = nodzInst
        self.nodeList = nodeList
        if nodeCreator is None:
            self.nodeCreator = self.defaultNodeCreator
        else:
            self.nodeCreator = nodeCreator
        self.returnPressed.connect(self.onReturnPressedSlot)

    def popup(self):
        position = self.parentWidget().mapFromGlobal(QtGui.QCursor.pos())
        self.move(position)
        self.clear()
        self.show()
        self.setFocus()
        self.setNodesList(self.nodeList)

    def popdown(self):
        self.hide()
        self.clear()
        self.parentWidget().setFocus()

    def setNodesList(self, nodeList):
        self.nodeList = nodeList
        self.completer = QtWidgets.QCompleter(self.nodeList, self)
        self.completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.setCompleter(self.completer)
        self.completer.activated.connect(self.onCompleterActivatedSlot)

        fontMetrics = QtGui.QFontMetrics(self.font())
        maxSize = self.size()
        for nodeName in self.nodeList:
            boundingSize = fontMetrics.boundingRect(nodeName).size()
            maxSize.setWidth(max(maxSize.width(), boundingSize.width()+30))  #30 is for margin
        self.resize(maxSize.width(), self.size().height())

    def focusOutEvent(self, QFocusEvent):
        self.popdown()

    def onCompleterActivatedSlot(self, text):
        pos=QtCore.QPointF(self.nodzInst.mapToScene(self.pos()))
        self.popdown()
        self.nodeCreator(self.nodzInst, text, pos)

    def onReturnPressedSlot(self):
        name = self.text()
        pos = QtCore.QPointF(self.nodzInst.mapToScene(self.pos()))
        self.completer.activated.disconnect(self.onCompleterActivatedSlot)
        self.popdown()
        self.nodeCreator(self.nodzInst, name, pos)
