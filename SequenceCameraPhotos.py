# -*- coding: utf-8 -*-
"""
Created on Tue Jan 18 12:06:12 2022

@author: njoosse
@version: 1.0 - Jan 18, 2022
@version: 1.1 - Feb 25, 2023
"""

from datetime import datetime
import os
from PIL import Image
from PIL.ExifTags import TAGS
from PyQt5.QtCore import Qt, QThread, QObject, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QDialog, QGridLayout, QLabel, QLineEdit,
        QProgressBar, QPushButton, QRadioButton, QStyleFactory,
        QFileDialog, QMessageBox, QApplication, QLineEdit, QCheckBox)
import shutil

# returns True if the image can be loaded as a PIL Image
def isImage(filename):
    # ensure that this is the basename
    filename = os.path.basename(filename)
    if filename.startswith('.'):
        return False
    fileExt = os.path.splitext(filename)[1]
    # removes the '.' in the extension
    if fileExt.lower()[1:] in ['jpg','jpeg','png','tif']:
        return True
    return False

# class that will run the move task in a 2nd thread to the user interface
class Mover(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(self, fileCount, inFolder, outFolder, useFileDate, useFileTime, folderFormat, parent=None):
        QThread.__init__(self, parent)
        self.fileCount = fileCount
        self.inFolder = inFolder
        self.outFolder = outFolder
        self.useFileDate = useFileDate
        self.useFileTime = useFileTime
        # 'Single' or 'Nested'
        self.folderFormat = folderFormat
        self.sequenceNumber = 1
        self.startTime = datetime(1970, 1, 1, 0, 0, 0)
        self.oldImageDate = ''

    # calculate the output filename for the image
    def createOutputFileName(self, img, cameraName, extension):
        exifData = img.getexif()
        # iterate through the exif data to find the timestamp
        for tag_id in exifData:
            tag = TAGS.get(tag_id, tag_id)
            data = exifData.get(tag_id)
            # read the timestamp of the image
            if tag == 'DateTime':
                imgDatetime = datetime.strptime(data, '%Y:%m:%d %H:%M:%S')
                imgDate = str(imgDatetime.date())
                # if using the time, the sequence number has a different requirement for resetting to 1                
                if self.useFileTime:
                    imgTime = str(imgDatetime.time())
                    secondsSinceLastPicture = (imgDatetime - self.startTime).total_seconds()
                    # cameras should be taking images in rapid sucession, then have a cooldown
                    if secondsSinceLastPicture > 60 or secondsSinceLastPicture < 0:
                        self.startTime = imgDatetime
                        # if incrementing the sequence by timestamp, then the sequence number resets to 1 here
                        self.sequenceNumber = 1
                elif imgDate != self.oldImageDate:
                    self.oldImageDate = imgDate
                    self.sequenceNumber = 1

                # separate out the image date and time values, used if sequencing by time, not just by date
                timestampStr = ''
                if self.useFileDate:
                    timestampStr += imgDate
                if self.useFileTime:
                    fileTime = imgTime.replace(':','.')[:-3]
                    timestampStr += ' ' + fileTime
                outputName = f'{cameraName}-{timestampStr}-{self.sequenceNumber}{extension}'
                if self.folderFormat == 'Single':
                    fullOutName = os.path.join(self.outFolder, outputName)
                else:
                    fullOutName = os.path.join(self.outFolder, cameraName, outputName)
        return fullOutName

    def moveSingleFolder(self, inFolder, outFolder):
        fileNumber = 0
        fullFilename = ''
        filenames = os.listdir(inFolder)
        filenames.sort()
        for filename in filenames:
            if isImage(filename):
                fullFilename = os.path.join(inFolder, filename)
                img = Image.open(fullFilename)
                outputName = self.createOutputFileName(img, os.path.basename(outFolder), os.path.splitext(filename)[1])
                self.sequenceNumber += 1
                if not os.path.exists(os.path.join(os.path.dirname(outputName))):
                    # was mkdir, user could type in a folder whose parent doesn't exist yet
                    os.makedirs(os.path.join(outFolder, filename))
                shutil.copy(fullFilename, outputName)
                fileNumber += 1
                # send the progress back to the front-end thread
                self.progress.emit(fileNumber / self.fileCount * 100)
                while not os.path.exists(outputName):
                    print(f'failed to copy {fullFilename} -> {outputName}')
                    shutil.copy(fullFilename, outputName)
            else:
                continue            

    def moveNestedFolders(self):
        folders = os.listdir(self.inFolder)
        folders.sort()
        for folder in folders:
            outFolder = os.path.join(self.outFolder, folder)
            if not os.path.exists(outFolder):
                os.makedirs(outFolder)
            self.moveSingleFolder(os.path.join(self.inFolder, folder), outFolder)

    # function that opens and renames the images
    def moveFiles(self):
        os.chdir(self.inFolder)
        if self.folderFormat == 'Single':
            self.moveSingleFolder(self.inFolder, self.outFolder)
        else:
            self.moveNestedFolders()
        self.finished.emit()

class WidgetGallery(QDialog):
    # warning dialog if folder contents do not match foler structure selection
    def folderSelectWarning(self):
        if self.folderType == 'Single':
            warningMsg = 'Nested folders detected'
        else:
            warningMsg = 'No folders found in selected folder'
        warning_dialog = QMessageBox()
        warning_dialog.setIcon(QMessageBox.Warning)
        warning_dialog.setText(warningMsg)
        warning_dialog.setWindowTitle('Warning')
        warning_dialog.setStandardButtons(QMessageBox.Retry | QMessageBox.Ok)
        warning_dialog.setDefaultButton(QMessageBox.Ok)
        warning_dialog.exec_()
        if warning_dialog.clickedButton().text() == 'OK':
            return True
        else:
            self.getInFolder()

    def getInFolder(self):
        folderName = QFileDialog.getExistingDirectory(self,'Select Input Directory', os.getcwd(), QFileDialog.ShowDirsOnly)
        if folderName == '':
            return
        folderContents = os.listdir(folderName)
        if (not os.path.isdir(os.path.join(folderName, folderContents[0])) and self.folderType == 'Nested') or (
            os.path.isdir(os.path.join(folderName, folderContents[0])) and self.folderType == 'Single'):
            if self.folderSelectWarning():
                self.inFolderName.setText(folderName)
        else:
            self.inFolderName.setText(folderName)
    
    def getOutFolder(self):
        folderName = QFileDialog.getExistingDirectory(self,'Select Output Directory', os.getcwd(), QFileDialog.ShowDirsOnly)
        if folderName == '':
            return
        self.outFolderName.setText(folderName)
    
    # verify that the input and output folders exist when starting the task
    def validateMove(self):
        errorMsg = ''
        if self.inFolderName.text() == '':
            errorMsg += 'Missing Input Folder Path\n'
        elif not os.path.exists(self.inFolderName.text()):
            errorMsg += 'Cannot Find Input Folder\n'
        if(self.outFolderName.text() == ''):
            errorMsg += 'Missing Output Folder Path\n'
        if errorMsg != '':
            error_dialog = QMessageBox()
            error_dialog.setIcon(QMessageBox.Warning)
            error_dialog.setText(errorMsg)
            error_dialog.setWindowTitle('Warning')
            error_dialog.setStandardButtons(QMessageBox.Ok)
            error_dialog.exec_()
            return False
        return True

    # disable the inputs while the task is running
    def disableInputs(self):
        self.transferButton.setText('Processing...')
        for control in self.controlLst:
            control.setEnabled(False)
        self.transferButton.setEnabled(False)
        self.progressBar.setVisible(True)

    # re-enables the inputs after the task has completed
    def enableInputs(self):
        self.transferButton.setText('Transfer ->')
        for control in self.controlLst:
            control.setEnabled(True)
        self.transferButton.setEnabled(True)
        self.progressBar.setVisible(False)

    # count the number of images that will be moving to scale the progress bar
    def getNumberOfImages(self):
        fileCount = 0
        for dirpath, dirnames, filenames in os.walk(self.inFolderName.text()):
            for filename in filenames:
                if os.path.splitext(filename)[1].lower()[1:] in ['jpg', 'jpeg', 'png', 'tif']:
                    fileCount += 1
        return fileCount

    # incrases the value of the progress bar from the mover task
    def incrementProgress(self, val):
        self.progressBar.setValue(val)

    # definition for dialog that appears when the transfer has completed
    def showCompletedDialog(self):
        completed_dialog = QMessageBox()
        completed_dialog.setIcon(QMessageBox.Information)
        completed_dialog.setText('Copy Completed')
        completed_dialog.setWindowTitle('Information')
        completed_dialog.setStandardButtons(QMessageBox.Ok)
        completed_dialog.exec_()
        self.enableInputs()

    def runTool(self):
        # disable the user interface until the transfer is completed
        self.disableInputs()
        # define the thread that will handle the rename and move
        self.moverThread = QThread()
        self.mover = Mover(self.getNumberOfImages(), self.inFolderName.text(), self.outFolderName.text(), 
                            self.useDateCheck.isChecked(), self.useTimeCheck.isChecked(), self.folderType)
        self.mover.moveToThread(self.moverThread)
        # connect functions to statuses from the mover thread
        self.moverThread.started.connect(self.mover.moveFiles)
        self.mover.finished.connect(self.moverThread.quit)
        self.mover.progress.connect(self.incrementProgress)
        self.mover.finished.connect(self.mover.deleteLater)
        self.mover.finished.connect(self.showCompletedDialog)
        self.moverThread.finished.connect(self.moverThread.deleteLater)
        # start the move
        self.moverThread.start()

    # uncheck the not-most-recently selected radiobutton
    def setRadioButtons(self, selected):
        if selected == 'single':
            self.folderType = 'Single'
            self.multiFolderRadio.setChecked(False)
        else:
            self.folderType = 'Nested'
            self.singleFolderRadio.setChecked(False)

    def checkDate(self):
        # I cannot think of a reason to just use the time in HH:mm
        if self.useTimeCheck.isChecked():
            self.useDateCheck.setChecked(True)

    def uncheckTime(self):
        # disables the time checkbutton if date is deselected
        if not self.useDateCheck.isChecked():
            self.useTimeCheck.setChecked(False)

    # main layout function
    def createLayout(self):
        grid = QGridLayout()
        self.controlLst = []

        self.singleFolderRadio = QRadioButton('Single Folder')
        self.singleFolderRadio.setChecked(True)
        self.singleFolderRadio.pressed.connect(lambda:self.setRadioButtons('single'))
        self.multiFolderRadio = QRadioButton('Nested Folders')
        self.multiFolderRadio.setChecked(False)
        self.multiFolderRadio.pressed.connect(lambda:self.setRadioButtons('nested'))

        self.controlLst.append(self.singleFolderRadio)
        self.controlLst.append(self.multiFolderRadio)

        self.inFolderName = QLineEdit('')
        self.browseIn = QPushButton("Browse")
        self.browseIn.clicked.connect(self.getInFolder)
        self.controlLst.append(self.inFolderName)
        self.controlLst.append(self.browseIn)

        self.outFolderName = QLineEdit('')
        self.browseOut = QPushButton("Browse")
        self.browseOut.clicked.connect(self.getOutFolder)
        self.controlLst.append(self.outFolderName)
        self.controlLst.append(self.browseOut)

        self.cameraPrefix = QLineEdit('Camera')
        self.controlLst.append(self.cameraPrefix)

        self.useDateCheck = QCheckBox("Use Date")
        self.useDateCheck.setChecked(True)
        self.useDateCheck.stateChanged.connect(self.uncheckTime)
        self.controlLst.append(self.useDateCheck)
        self.useTimeCheck = QCheckBox("Use Time")
        self.useTimeCheck.stateChanged.connect(self.checkDate)
        self.controlLst.append(self.useTimeCheck)

        self.progressBar = QProgressBar()
        self.progressBar.setVisible(False)
        self.progressBar.setMaximum(100)

        self.transferButton = QPushButton('Transfer ->')
        self.transferButton.clicked.connect(self.runTool)

        row = 0
        grid.addWidget(QLabel('Folder Structure:'), row, 0, 1, 1, Qt.AlignRight)
        grid.addWidget(self.singleFolderRadio, row, 1, 1, 1, Qt.AlignCenter)
        grid.addWidget(self.multiFolderRadio, row, 2, 1, 1, Qt.AlignCenter)

        row += 1
        grid.addWidget(QLabel('In Folder:'), row, 0, 1, 1, Qt.AlignRight)
        grid.addWidget(self.inFolderName, row, 1, 1, 2)
        grid.addWidget(self.browseIn, row, 3, 1, 1)

        row += 1
        grid.addWidget(QLabel('Out Folder:'), row, 0, 1, 1, Qt.AlignRight)
        grid.addWidget(self.outFolderName, row, 1, 1, 2)
        grid.addWidget(self.browseOut, row, 3, 1, 1)

        # row += 1
        # grid.addWidget(QLabel('Output File Prefix:'), row, 0, 1, 1, Qt.AlignRight)
        # grid.addWidget(self.cameraPrefix, row, 1, 1, 1)
        # grid.addWidget(QLabel('-Number-Timestamp-SequenceNo'), row, 2, 1, 2)

        row += 1
        grid.addWidget(QLabel('Sequence Format:'), row, 0, 1, 1, Qt.AlignRight)
        grid.addWidget(self.useDateCheck, row, 1, 1, 1, Qt.AlignCenter)
        grid.addWidget(self.useTimeCheck, row, 2, 1, 1)

        row += 1
        grid.addWidget(self.progressBar, row, 1, 1, 2)
        grid.addWidget(self.transferButton, row, 3, 1, 1)
        
        self.setLayout(grid)

    # I like a different style than the default one, this is how I change it
    def changeStyle(self, styleName):
        QApplication.setStyle(QStyleFactory.create(styleName))
        QApplication.setPalette(QApplication.style().standardPalette())

    # initialize the class
    def __init__(self, parent=None):
        super(WidgetGallery, self).__init__(parent)
        self.originalPalette = QApplication.palette()
        self.setWindowTitle("Trail Camera Sequencer v1.1")
        self.changeStyle('Fusion')
        width = 500
        self.folderType = 'Single'
        # setting  the fixed width of window
        self.setFixedWidth(width)
        self.createLayout()

if __name__ == '__main__':
    app = QApplication([])
    window = WidgetGallery()
    window.show()
    app.exec_() 
