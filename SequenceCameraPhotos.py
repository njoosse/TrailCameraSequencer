# -*- coding: utf-8 -*-
"""
Created on Tue Jan 18 12:06:12 2022

@author: njoos
"""

from tkinter import filedialog
from tkinter import *
import os
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime
import shutil

# function to move the files 
def moveFiles():
    startTime = datetime(1970, 1, 1, 0, 0, 0)
    sequenceNumber = 1
    for subFolder in os.listdir(inFolder):
        print(subFolder)
        siteName = subFolder
        cameraNumber = int(siteName[-2:])
        oldImageDate = ''
        for filename in os.listdir(os.path.join(inFolder, subFolder)):
            # skips files that are created as locks, not really an image
            if filename.startswith('.'):
                continue
            fullFilename = os.path.join(inFolder, siteName, filename)
            try:
                im = Image.open(fullFilename)
            except:
                print(f'unable to read {fullFilename}')
            # parse the exif data to get the metadata
            exifData = im.getexif()
            for tag_id in exifData:
                tag = TAGS.get(tag_id, tag_id)
                data = exifData.get(tag_id)
                # read the timestamp of the image
                if tag == 'DateTime':
                    imgDatetime = datetime.strptime(data, '%Y:%m:%d %H:%M:%S')
                    imgDate = str(imgDatetime.date())
                    if imgDate != oldImageDate:
                        oldImageDate = imgDate
                        sequenceNumber = 1
                    imgTime = str(imgDatetime.time())
                    secondsSinceLastPicture = (imgDatetime - startTime).total_seconds()
                    # cameras should be taking images in rapid sucession, then have a cooldown
                    if secondsSinceLastPicture > 60 or secondsSinceLastPicture < 0:
                        startTime = imgDatetime
                        # if incrementing the sequence by timestamp, then the sequence number resets to 1 here
                        ## sequenceNumber = 1
                        
                        # separate out the image date and time values, used if sequencing by time, not just by date
                        fileDate = imgDate
                        fileTime = imgTime.replace(':','.')[:-3]
                    outputName = (os.path.join(outFolder, f'CT-{cameraNumber:02d}', f'CT-{cameraNumber:02d}-{fileDate}-{sequenceNumber}.jpg'))
                    if not os.path.exists(os.path.dirname(outputName)):
                        os.makedirs(os.path.dirname(outputName))
                        if makeLegendFile:
                            open(os.path.join(os.path.dirname(outputName),'_Sitename-Year-Month-Day-Sequence.txt'), 'w')
                    sequenceNumber += 1
            if os.path.exists(outputName):
                continue
            print(f'{fullFilename} -> {outputName}')
            shutil.copy(fullFilename, outputName)

# function that will iterate through the source folder and print out the names of all files that are unreadable,
#   either an invalid image type, or a corrupted image file
def findUnreadableFiles():
    for subFolder in os.listdir(inFolder):
        siteName = subFolder
        for filename in os.listdir(os.path.join(inFolder, subFolder)):
            # skips files that are created as locks, not really an image
            if filename.startswith('.'):
                continue
            fullFilename = os.path.join(inFolder, siteName, filename)
            try:
                im = Image.open(fullFilename)
            except:
                print(f'unable to read {fullFilename}')


if __name__ == '__main__':
    makeLegendFile = True
    root = Tk()
    root.withdraw()
    inFolder = filedialog.askdirectory(title="input folder")
    outFolder = filedialog.askdirectory(title="output folder")
    moveFiles()
    # findUnreadableFiles()
