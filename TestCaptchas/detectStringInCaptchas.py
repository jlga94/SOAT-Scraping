import cv2
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import numpy as np
import os
import csv

def writeFilenamesInDirectory():

    outputFile = 'outputFile.txt'
    with open(outputFile, 'w') as f:
        for i in range(200):
            f.write('captcha_soat_' + str(i) + '.png' + '\n')

#writeFilenamesInDirectory()

def readTestImagesFiles(filename):
    dictFileImages = {}
    with open(filename,'r') as f:
        csvReader = csv.reader(f)
        for row in csvReader:
            #print(row)
            dictFileImages[row[0]] = row[1]
    return dictFileImages

def preprocessImage(fileNameCaptcha):
    #Process the Image to make it gray for a better application of Pytesseract
    fileNameCaptchaSplitted = fileNameCaptcha.split('.')
    fileNameGrayCaptcha = fileNameCaptchaSplitted[0] + '_Dilatation.' + fileNameCaptchaSplitted[1]
    image = cv2.imread(fileNameCaptcha)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    gray = cv2.bitwise_not(gray)

    #kernel = np.ones((2, 1), np.uint8)
    #kernel = cv2.getStructuringElement(cv2.MORPH_CROSS,(3,3))

    #img_erosion = cv2.erode(gray, kernel, iterations=1)
    #img_dilation = cv2.dilate(img_erosion, kernel, iterations=1)




    cv2.imwrite(fileNameGrayCaptcha, gray)
    return fileNameGrayCaptcha

def decodeNumberInImage(fileNameGrayCaptcha):
    #Detects the number in the image using Pytesseract

    im = Image.open(fileNameGrayCaptcha)
    #enhancer = ImageEnhance.Contrast(im)
    #im = enhancer.enhance(5)

    basewidth = 300
    wpercent = (basewidth / float(im.size[0]))
    hsize = int((float(im.size[1]) * float(wpercent)))
    im = im.resize((basewidth, hsize), Image.ANTIALIAS)
    enhancer = ImageEnhance.Contrast(im)
    im = enhancer.enhance(5)

    im.save(fileNameGrayCaptcha)


    numberInCaptcha = pytesseract.image_to_string(im, config='--psm 10 --eom 3')
    return numberInCaptcha.replace(" ", "")


def testImages(testFilesDict,initialPath):

    numCorrectNumber = 0
    iteration = 1
    for file in sorted(testFilesDict.keys()):
        fileNameCaptcha = preprocessImage(initialPath + '/' + file)
        number = decodeNumberInImage(fileNameCaptcha)
        print("Iteration: " + str(iteration) + " - Filename: " + file + " - Expected: " + testFilesDict[file] + ' - Number: '+ number)
        if testFilesDict[file] == number:
            numCorrectNumber += 1
        iteration += 1

    print("De: " + str(len(testFilesDict.keys())) + " fueron correctos: " + str(numCorrectNumber))


testFilesDict = readTestImagesFiles('TestCaptchas.csv')
testImages(testFilesDict,'Captchas')
