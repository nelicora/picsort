from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
import os
import functools
from wand import image as wandimage
import sys, os, os.path, json, shutil



IMAGE_EXTENSIONS = [".jpg",".png",".tiff",".jpeg",".gif",".bmp"]
ZOOM_FITTED, ZOOM_100, ZOOM_ZOOM = 1,2,3
groupManager = None
storage = None
mainWindow = None


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.resize(900,700)
        
        global mainWindow
        mainWindow = self
        global groupManager    
        groupManager = GroupManager()
        
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        self.setLayout(layout)
        
        # Menu
        menuBar = QtWidgets.QMenuBar(self)
        fileMenu = menuBar.addMenu("File")
        editMenu = menuBar.addMenu("Edit")
        groupMenu = menuBar.addMenu("Group")
        viewMenu = menuBar.addMenu("View")
        layout.addWidget(menuBar)
        
        
        # Big part with group/selection manager and image viewer
        topLayout = QtWidgets.QHBoxLayout()
        layout.addLayout(topLayout,1)
        
        splitter = QtWidgets.QSplitter()
        topLayout.addWidget(splitter)
        
        self.imageView = ImageView()
        groupView = GroupView(self.imageView)
        splitter.addWidget(groupView)
        
        
        splitter.addWidget(self.imageView)
        splitter.setSizes((100,500))
        
        buttonBar = ButtonBar(self.imageView)
        layout.addWidget(buttonBar)
        
        self.imageView.currentChanged.connect(self._handleCurrentChanged)
        self._handleCurrentChanged()
        
        # Shortcuts
        shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(Qt.Key_Left),self)
        shortcut.activated.connect(self.imageView.previous)
        shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(Qt.Key_Right),self)
        shortcut.activated.connect(self.imageView.next)
        
        # Actions:
        # View Menu:
        zoomInAction = QtWidgets.QAction("Engorgio", self)
        zoomInAction.setShortcut(QtGui.QKeySequence(Qt.Key_Plus))
        viewMenu.addAction(zoomInAction)
        zoomInAction.triggered.connect(self.imageView.zoomIn)
        
        zoomOutAction = QtWidgets.QAction("Zoom out", self)
        zoomOutAction.setShortcut(QtGui.QKeySequence(Qt.Key_Minus))
        viewMenu.addAction(zoomOutAction)
        zoomOutAction.triggered.connect(self.imageView.zoomOut)
        
        zoom100Action = QtWidgets.QAction("View at 100%", self)
        zoom100Action.setShortcut(QtGui.QKeySequence("#"))
        viewMenu.addAction(zoom100Action)
        zoom100Action.triggered.connect(functools.partial(self.imageView.setZoomMode, ZOOM_100))
        
        zoomFittedAction = QtWidgets.QAction("Fit to screen", self)
        zoomFittedAction.setShortcut(QtGui.QKeySequence("Ä"))
        viewMenu.addAction(zoomFittedAction)
        zoomFittedAction.triggered.connect(functools.partial(self.imageView.setZoomMode, ZOOM_FITTED))
             
        # File Menu:
        changeDirectoryAction = QtWidgets.QAction("Change Directory", self)
        changeDirectoryAction.setShortcut(QtGui.QKeySequence( "Ctrl+O"))
        fileMenu.addAction(changeDirectoryAction)
        changeDirectoryAction.triggered.connect(self._handleChangeDirectory)
        
        # Group Menu
        addGroupAction = QtWidgets.QAction("Add Group", self)
        addGroupAction.setShortcut(QtGui.QKeySequence("Ctrl+N"))
        groupMenu.addAction(addGroupAction)
        addGroupAction.triggered.connect(groupView._handleAddButton)
        
        exportToFolderAction = QtWidgets.QAction("Export Group to Folder", self)
        exportToFolderAction.setShortcut(QtGui.QKeySequence("Ctrl+S"))
        groupMenu.addAction(exportToFolderAction)
        exportToFolderAction.triggered.connect(self._handleExportToFolder)
        
    def shutdown(self):
        storage["directory"] = self.imageView.directory
        storage["groups"] = [group.save() for group in groupManager.groups]
        
        
    def _handleCurrentChanged(self):
        if self.imageView.getImageSizeAsString() is not None:
            self.setWindowTitle("Picsort by nelicora - {}".format(self.imageView.getImageSizeAsString()))
        else: self.setWindowTitle("Picsort by nelicora")
        
    def _handleChangeDirectory(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Change Directory", "/home", QtWidgets.QFileDialog.ShowDirsOnly) 
        if len(directory) != 0:
            self.imageView.setDirectory(directory)
    
    def _handleExportToFolder(self):
        dialog = ExportDialog(self)
        dialog.exec_()
        #directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Export Group to folder", "/home", QtWidgets.QFileDialog.ShowDirsOnly) # TODO change the Button Text in the opening window
        #if len(directory) != 0:
        #    print(directory) # TODO call to  the real export method here. Should prob be part of the GroupManager class
            
class Group(set):
    def __init__(self, name, shortcut=None):
        super().__init__()
        self.name = name
        self.shortcut = shortcut
        #QtWidgets.QShortcut(QtGui.QKeySequence(shortcut),mainWindow)
        #self.shortcut.activated.connect()
    
    def save(self):
        return {"name": self.name, 
                "shortcut": self.shortcut,
                "images": [image.path for image in self]
                }
    
    @staticmethod
    def load(data):
        group = Group(data["name"], data["shortcut"])
        group.update(Image(path) for path in data["images"])
        return group
    
    def displayString(self):
        return self.name +"  ["+self.shortcut +"]"   #.key().toString()+"]")
        
    def __eq__(self, other):
        return self.name == other.name
    def __ne__(self, other):
        return self.name != other.name
    def __hash__(self):
        return hash(self.name)

class GroupManager(QtCore.QObject):
    groupAdded = QtCore.pyqtSignal(Group)
    groupRemoved = QtCore.pyqtSignal(Group)
    
    def __init__(self):
        super().__init__()
        if "groups" in storage:        
            self.groups = [Group.load(data) for data in storage["groups"]] # Group list
        else: self.groups = []
        
    def addGroup(self, group):
        if group not in self.groups:
            self.groups.append(group)
            self.groupAdded.emit(group)
        
    def removeGroup(self, group):
        self.groups.remove(group)
        self.groupRemoved.emit(group)
        
    def getGroupByName(self, name):
        for group in self.groups: 
            if group.name == name:
                return group
        else: return None
    
    def addImageToGroup(self, image, group):
        group.add(image)
        #self.gd[group].add(image)
    
    def removeImageFromGroup(self, image, group):
        group.discard(image)
        #self.gd[group].discard(image)
                     
            
class GroupView(QtWidgets.QWidget):
    def __init__(self, imageView):
        super().__init__()
        self.imageView = imageView
        self._shortcuts = {}
        
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        
        self.groupListWidget = QtWidgets.QListWidget()
        layout.addWidget(self.groupListWidget)
        self.groupListWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        
        addButton = QtWidgets.QPushButton("Add Group")
        layout.addWidget(addButton)
        addButton.clicked.connect(self._handleAddButton)
        
        self.removeButton = QtWidgets.QPushButton("Remove Group")
        layout.addWidget(self.removeButton)
        self.removeButton.setEnabled(False)
        self.groupListWidget.selectionModel().selectionChanged.connect(self._handleSelectionChanged)
        self.removeButton.clicked.connect(self._handleRemoveButton)
        
        
        layout.addStretch()
        
        for group in groupManager.groups:
            self._handleGroupAdded(group)
        
        self._handleCurrentChanged()
        
        self.groupListWidget.itemChanged.connect(self._handleItemChanged)
        self.imageView.currentChanged.connect(self._handleCurrentChanged)
        groupManager.groupAdded.connect(self._handleGroupAdded)
        groupManager.groupRemoved.connect(self._handleGroupRemoved)
    
    def _handleItemChanged(self, item):
        group = item.data(Qt.UserRole)
        image = self.imageView.getCurrentImage()
        if image is not None:
            if item.checkState() == Qt.Checked:            
                groupManager.addImageToGroup(image, group) 
            else: groupManager.removeImageFromGroup(image, group) 
        else:
            item.setCheckState(Qt.Unchecked) 
         
    def _handleCurrentChanged(self): #load groups for current image
        #print(self.imageView.getCurrentImage())
        for i in range(self.groupListWidget.count()):
            item = self.groupListWidget.item(i)
            if self.imageView.getCurrentImage() in item.data(Qt.UserRole):  
                item.setCheckState(Qt.Checked) 
            else: item.setCheckState(Qt.Unchecked)
    
    def _handleGroupAdded(self, group): # if a group is added, display it in the list
        item = QtWidgets.QListWidgetItem(group.displayString())
        self._shortcuts[group] = QtWidgets.QShortcut(QtGui.QKeySequence(group.shortcut), self)
        self._shortcuts[group].activated.connect(functools.partial(self._handleShortcut, item)) #connect the shortcut to painting the check mark 
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
        item.setCheckState(Qt.Unchecked)
        self.groupListWidget.addItem(item)
        item.setData(Qt.UserRole, group)
    
    def _handleGroupRemoved(self, group):
        for i in range(self.groupListWidget.count()):
            item = self.groupListWidget.item(i)
            if item.data(Qt.UserRole) == group:
                self._shortcuts[group].setKey(0)
                del self._shortcuts[group]
                self.groupListWidget.takeItem(i)
                break
    
    def _handleAddButton(self):
        dialog = GroupDialog(self)
        dialog.exec_()
    
    def _handleRemoveButton(self):
        groupList = [] # selected groups go in here
        for i in range(self.groupListWidget.count()):
            item = self.groupListWidget.item(i)
            if item.isSelected():
                group = item.data(Qt.UserRole)
                groupList.append(group)
        if len(groupList) == 0:
            return
        
        ok = QtWidgets.QMessageBox.warning(self, "Delete?", "Do you want to delete the selected {} group(s)?".format(len(groupList)),
                                       QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if ok == QtWidgets.QMessageBox.Yes:
            for group in groupList:
                groupManager.removeGroup(group)
    
    def _handleShortcut(self, item):
        if item.checkState() == Qt.Unchecked:
            item.setCheckState(Qt.Checked)
        else: item.setCheckState(Qt.Unchecked)
    
    def _handleSelectionChanged(self):
        self.removeButton.setEnabled(self.groupListWidget.selectionModel().hasSelection())
                
        
class GroupDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(300,100)
        self.setWindowTitle("Create a new empty Group")
        
        layout = QtWidgets.QVBoxLayout(self)
        inputForm = QtWidgets.QFormLayout()
        layout.addLayout(inputForm)
        self.newGroupWidget = QtWidgets.QLineEdit()
        self.shortcutWidget = QtWidgets.QLineEdit()
        inputForm.addRow("Name", self.newGroupWidget)
        inputForm.addRow("Shortcut", self.shortcutWidget)
        
        buttonLayout = QtWidgets.QHBoxLayout()
        layout.addLayout(buttonLayout)
        buttonLayout.addStretch()
        cancelButton = QtWidgets.QPushButton("Cancel")
        buttonLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)
        okayButton = QtWidgets.QPushButton("Okay")
        buttonLayout.addWidget(okayButton)
        okayButton.clicked.connect(self.accept)
        okayButton.setDefault(True)
        
    def accept(self):
        name = self.newGroupWidget.text()
        if len(name) < 3:
            QtWidgets.QMessageBox.warning(self, "Group name too short", "Please enter a group name with more than two characters.",
                                       QtWidgets.QMessageBox.Close)
            return
        
        shortcut = self.shortcutWidget.text()    
        group = Group(name, shortcut)
        
        if group in groupManager.groups:
            QtWidgets.QMessageBox.warning(self, "Group already exists", "To create a new group please choose a new group name.",
                                       QtWidgets.QMessageBox.Close)
            return
        
        groupManager.addGroup(group)
        self.close()
        
   
            
        
class ButtonBar(QtWidgets.QWidget):
    def __init__(self, imageView):
        super().__init__()
        
        self.imageView = imageView
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        imageView.currentChanged.connect(self._handleCurrentChanged)
        imageView.zoomModeChanged.connect(self._handleZoomModeChanged)
        
        self.currentLabel = QtWidgets.QLabel()
        layout.addWidget(self.currentLabel)
        layout.addSpacing(10)
        
        self.imageSizeLabel = QtWidgets.QLabel()
        layout.addWidget(self.imageSizeLabel)
        layout.addStretch()
        
        
        
        previousButton = QtWidgets.QPushButton("Previous")
        layout.addWidget(previousButton)
        previousButton.clicked.connect(imageView.previous)
       
        nextButton = QtWidgets.QPushButton("Next")
        layout.addWidget(nextButton)
        nextButton.clicked.connect(imageView.next)
        
        layout.addStretch()
        
        self.fitToScreenButton = QtWidgets.QPushButton("Fit to screen")
        self.fitToScreenButton.setCheckable(True)
        layout.addWidget(self.fitToScreenButton)
        self.fitToScreenButton.clicked.connect(functools.partial(imageView.setZoomMode, ZOOM_FITTED))
              
        
        self.originalSizeButton = QtWidgets.QPushButton("100 %")
        self.originalSizeButton.setCheckable(True)
        layout.addWidget(self.originalSizeButton)
        self.originalSizeButton.clicked.connect(functools.partial(imageView.setZoomMode, ZOOM_100))
        
        self._handleCurrentChanged()
        self._handleZoomModeChanged(imageView.getZoomMode())
        
        
    def _handleCurrentChanged(self):
        if self.imageView.getCurrent() is not None:
            self.currentLabel.setText("{} / {}".format(self.imageView.getCurrent()+1,self.imageView.getCount()))
            self.imageSizeLabel.setText(self.imageView.getImageSizeAsString())
        else: 
            self.currentLabel.setText("")
            self.imageSizeLabel.setText("")
    
    def _handleZoomModeChanged(self, zoomMode):
        self.fitToScreenButton.setChecked(zoomMode == ZOOM_FITTED)
        self.originalSizeButton.setChecked(zoomMode == ZOOM_100)

class Image:
    def __init__(self, path):
        self.path = path
        self.metadata = None
    
    def __repr__(self):
        return "<Image {}>".format(self.path)
    
    def readMetadata(self):
        file = open(self.path, "rb")
        image = wandimage.Image(file=file)    
        self.metadata = dict(image.metadata.items())
        file.close()
        
    def getExifTag(self, key):
        metadata = self.getMetadata()
        return metadata['exif:'+key] if 'exif:'+key in metadata else None
    
    def getMetadata(self):
        if self.metadata is None:
            self.readMetadata()
        return self.metadata
    
    def __eq__(self, other):
        return self.path == other.path
    def __ne__(self, other):
        return self.path != other.path
    def __hash__(self):
        return hash(self.path)
    
    #def getAsQImage(self):
        #TO DO 
         
class ImageView(QtWidgets.QScrollArea):
    currentChanged = QtCore.pyqtSignal()
    zoomModeChanged = QtCore.pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        
        self.zoomFactor = 1.0
        self.zoomMode = ZOOM_FITTED
        
        self.label = QtWidgets.QLabel()
        self.label.setStyleSheet("QLabel { background-color: #444444 }")
        self.label.setAlignment(Qt.AlignVCenter|Qt.AlignHCenter)
        self.setWidget(self.label)
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignVCenter|Qt.AlignHCenter)       
        
        self.directory = 0
        #self.setDirectory("/home/cornelia/Bilder/TestPicsort")
        try:
            if "directory" in storage:
                self.setDirectory(storage["directory"])
            else: self.setDirectory(os.path.expanduser("~"))
        except FileNotFoundError:
            #print("Folder not found")
            self.setDirectory(None)
        
    def getImageSize(self):
        return self.pixmap.size() if self.pixmap is not None else None
    
    def getImageSizeAsString(self):
        if self.pixmap is not None:
            return "{}x{}".format(self.getImageSize().width(), self.getImageSize().height())
        else: return None
    
    def setCurrent(self, number):
        if number is not None:
            self.current = number % len(self.images)
            path = self.images[self.current].path
            #metadata = self.images[self.current].getMetadata()
            
            orientation = self.images[self.current].getExifTag("Orientation")
            
            self.pixmap = QtGui.QPixmap(path)
            
            # Rotations stuff (read from EXIF data)
            rotate = QtGui.QTransform()
            if orientation == "6":
                self.pixmap = self.pixmap.transformed(rotate.rotate(90))
            if orientation == "8":
                self.pixmap = self.pixmap.transformed(rotate.rotate(270))
            if orientation == "3":
                self.pixmap = self.pixmap.transformed(rotate.rotate(180))
            
            if self.zoomMode != ZOOM_FITTED:
                self.setZoomMode(ZOOM_FITTED)
            else: self._updateImage() 
        else:
            self.current = None
            self.pixmap = None
            
        self.currentChanged.emit()
    
    def next(self):
        if self.current is not None: 
            self.setCurrent(self.current + 1)
            
    def previous(self):
        if self.current is not None: 
            self.setCurrent(self.current - 1)
        
    def getCurrent(self):
        return self.current
    
    def getCount(self):
        return len(self.images)
    
    def getZoomMode(self):
        return self.zoomMode
    
    def _updateImage(self):
        if self.current is None:
            self.label.setText("No images to display")
            return
        
        if self.zoomMode == ZOOM_100:
            self.widget().setPixmap(self.pixmap)
        elif self.zoomMode == ZOOM_FITTED:
            size = self.viewport().size()
            self.widget().setPixmap(self.pixmap.scaled(size,Qt.KeepAspectRatio, Qt.SmoothTransformation))
        elif self.zoomMode == ZOOM_ZOOM:
            size = self.viewport().size()
            self.widget().setPixmap(self.pixmap.scaled(size*self.zoomFactor, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
    def setZoomMode(self, zoomMode):
        if self.zoomMode != zoomMode:
            self.zoomMode = zoomMode
            self._updateImage()
            self.zoomModeChanged.emit(zoomMode)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.zoomMode == ZOOM_FITTED:
            self._updateImage()
    
    def mousePressEvent(self, event):
        self._pos = event.pos()
            
            
    def mouseReleaseEvent(self, event):
        self._pos = None
        
    def mouseMoveEvent(self, event):
        if self.zoomMode != ZOOM_FITTED and Qt.LeftButton & event.buttons():
            if self._pos is not None:
                dx = self._pos.x()-event.pos().x()
                dy = self._pos.y()-event.pos().y()
                self.horizontalScrollBar().setValue(self.horizontalScrollBar().value()+dx)
                self.verticalScrollBar().setValue(self.verticalScrollBar().value()+dy)
            self._pos = event.pos()
    
    def wheelEvent(self, event):
        
        if self.zoomMode != ZOOM_100:
            if event.angleDelta().y() > 0:
                self.zoomIn()
            elif event.angleDelta().y() < 0:
                self.zoomOut()            
        else: super().wheelEvent(event)
    
    def zoomIn(self):
        if self.zoomFactor < 5.99:
            self.zoomFactor += 0.2
            if self.zoomMode != ZOOM_ZOOM:
                self.setZoomMode(ZOOM_ZOOM)
            else: self._updateImage()
            
    def zoomOut(self):
        if self.zoomFactor > 0.41:
            self.zoomFactor -= 0.2
            if self.zoomMode != ZOOM_ZOOM:
                self.setZoomMode(ZOOM_ZOOM)
            else: self._updateImage()
    
    def setDirectory(self, directory):
        if self.directory != directory:
            if directory is not None:
                paths = os.listdir(directory)
                self.directory = directory
                imagePaths = [path for path in paths if os.path.splitext(path)[1].lower() in IMAGE_EXTENSIONS]
                imagePaths.sort()
                self.images = [Image(os.path.join(self.directory, path)) for path in imagePaths]
                if len(self.images) > 0:
                    self.setCurrent(0)
                else: 
                    #self.label.setText("No images to display")
                    self.setCurrent(None)
            else:
                self.setCurrent(None)
                self.images = []
                self.directory = None
    
    def getCurrentImage(self):
        return self.images[self.current] if self.current is not None else None

class ExportDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        #self.resize(400,200)
        self.setWindowTitle("Export Group")
        
        layout = QtWidgets.QVBoxLayout(self)
        optionsLayout = QtWidgets.QFormLayout()
        layout.addLayout(optionsLayout)
        
        
        self.groupComboBox = QtWidgets.QComboBox()
        optionsLayout.addRow("Select Group", self.groupComboBox)
        for group in groupManager.groups:
            self.groupComboBox.addItem(group.name, group)
        
        self.actionComboBox = QtWidgets.QComboBox()
        optionsLayout.addRow("Select Action", self.actionComboBox)
        self.actionComboBox.addItems(["Copy", "Copy and Resize"])
        
        sizeWidget = QtWidgets.QWidget()
        sizeLayout = QtWidgets.QHBoxLayout(sizeWidget)
        sizeLayout.addWidget(QtWidgets.QLabel("Size"))
        self.sizeInput = QtWidgets.QLineEdit()
        sizeValidator = QtGui.QIntValidator(1, 100000)
        self.sizeInput.setValidator(sizeValidator)
        sizeLayout.addWidget(self.sizeInput)
        sizeLayout.addWidget(QtWidgets.QLabel("px  (shortest side)"))
        optionsLayout.addRow("", sizeWidget)
        
        folderLayout = QtWidgets.QHBoxLayout()
        self.folderPathInput = QtWidgets.QLineEdit()
        folderLayout.addWidget(self.folderPathInput)
        folderBrowseButton = QtWidgets.QPushButton()
        folderBrowseButton.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        folderLayout.addWidget(folderBrowseButton)
        optionsLayout.addRow("Select Folder", folderLayout)
        folderBrowseButton.clicked.connect(self._handleChangeDirectory)
                
        buttonLayout = QtWidgets.QHBoxLayout()
        layout.addLayout(buttonLayout)
        buttonLayout.addStretch()
        cancelButton = QtWidgets.QPushButton("Cancel")
        buttonLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)
        exportButton = QtWidgets.QPushButton("Export")
        buttonLayout.addWidget(exportButton)
        exportButton.clicked.connect(self.accept)
        exportButton.setDefault(True)
        
    def accept(self):  # Here is it where the export magic is happening (soon)
        directory = self.folderPathInput.text()
        if not os.path.isdir(directory):
            QtWidgets.QMessageBox.warning(self, "Directory doesn't exist", "Please check your target directory - it wasn't found.")
        else:
            group = self.groupComboBox.itemData(self.groupComboBox.currentIndex())
            if self.actionComboBox.currentText() == "Copy":
                for image in group:
                    shutil.copy(image.path, directory)
            elif self.actionComboBox.currentText() == "Copy and Resize":
                size = max(1, int(self.sizeInput.text()))
                for image in group:
                    scaled = QtGui.QImage(image.path).scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    scaled.save(os.path.join(directory, os.path.basename(image.path)))
            # more elifs when I need them in the future
            super().accept()
        
    def _handleChangeDirectory(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose Destination", "/home", QtWidgets.QFileDialog.ShowDirsOnly)
        if len(directory) != 0:
            self.folderPathInput.setText(directory)


#kram von maddin #storage speichert krempel
        
def getConfigDir():
    path = os.path.join(os.path.expanduser('~'), ".config", "picsort")
    if not os.path.exists(path):
        try:
            os.makedirs(path) # also create intermediate directories
        except OSError:
            print("Could not create config file. Please check directory permissions.")
            sys.exit(1)
    return path
     
    
            
def readConfig():
    global storage
    path = os.path.join(getConfigDir(), 'storage')
    if not os.path.exists(path):
        storage = {}
    else:
        with open(path, 'r') as file:
            storage = json.load(file)
        #TODO: Fehler-Behandlung
        
        
def writeConfig():
    # Do not write to file directly because all contents will be lost if *storage* contains an object that
    # is not a Python standard type
    string = json.dumps(storage, ensure_ascii=False, indent=2)
    path = os.path.join(getConfigDir(), 'storage')
    with open(path, 'w') as file:
        file.write(string)
    #TODO: Fehler-Behandlung               
            
        
if __name__ == "__main__":
    readConfig()
    app = QtWidgets.QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()
    window.shutdown()
    writeConfig()  
        
        
