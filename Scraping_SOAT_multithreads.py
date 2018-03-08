from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from contextlib import contextmanager
from selenium.webdriver.support.expected_conditions import staleness_of
import selenium

import cv2
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from time import sleep
import re, time, datetime
from bs4 import BeautifulSoup
import csv, string, sys
import numpy as np

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from os import cpu_count
import os, re
from bs4 import BeautifulSoup

browser = None
url = "https://www.apeseg.org.pe/consultas-soat/"
columnsData = ['Compañia','Inicio','Fin','Placa','Certificado','Uso','Clase','Estado','Tipo','Fec.Creación','Datatime_Extraction']

outputFileResults = 'ResultadosScrapping_SOAT_Replicado.tsv'

with open(outputFileResults,'w', encoding='utf-8') as f:
    file_writer = csv.writer(f, delimiter='\t', lineterminator='\n')
    file_writer.writerow(columnsData)

alphabet = set(string.ascii_lowercase)
alphabet = alphabet.union(set(string.punctuation))

def getCaptchaImage(captchaElement,fileNameCaptcha):
    captchaElement.screenshot(fileNameCaptcha)

    img = cv2.imread(fileNameCaptcha, 0)
    crop_img = img[5:5 + 22, 0:0 + 50]
    cv2.imwrite(fileNameCaptcha, crop_img)


def preprocessImage(fileNameCaptcha):
    # Process the Image to make it gray for a better application of Pytesseract

    image = cv2.imread(fileNameCaptcha)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    gray = cv2.bitwise_not(gray)

    cv2.imwrite(fileNameCaptcha, gray)
    return fileNameCaptcha

def decodeStringInImage(fileNameCaptcha):
    #Detects the number in the image using Pytesseract

    im = Image.open(fileNameCaptcha)

    basewidth = 300
    wpercent = (basewidth / float(im.size[0]))
    hsize = int((float(im.size[1]) * float(wpercent)))
    im = im.resize((basewidth, hsize), Image.ANTIALIAS)
    enhancer = ImageEnhance.Contrast(im)
    im = enhancer.enhance(5)

    im.save(fileNameCaptcha)

    stringInCaptcha = pytesseract.image_to_string(im, config='--psm 10 --eom 3')
    return stringInCaptcha.replace(" ", "")


def writeRows(html_source):
    soup = BeautifulSoup(html_source, 'lxml')
    table = soup.find("table", id="grid1")
    tbody = table.find("tbody")

    ts = time.time()

    for row in tbody.findAll("tr"):
        columns = row.findAll("td")
        columnsText = []
        for iColumns in range(1,len(columns)):
            columnsText.append(columns[iColumns].text.strip())

        columnsText.append(datetime.datetime.fromtimestamp(ts).strftime('%d-%m-%Y %H:%M:%S'))

        print(columnsText)
        #Write in File
        with open(outputFileResults, 'a', encoding='utf-8') as f:
            file_writer = csv.writer(f, delimiter='\t', lineterminator='\n')
            file_writer.writerow(columnsText)


def scrapingOneDocument(browser,placa,rootDirectory):

    browser.get(url)
    delay = 10  # seconds
    delay2 = 2

    try:
        myElem = WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.CLASS_NAME, 'Placa')))
    except TimeoutException:
        print("Se excedió el tiempo de espera")
        resultsScrappingTsvFile.close()

    captchaElement = browser.find_element_by_xpath("//img[@alt='captcha']")

    fileNameCaptcha = rootDirectory + '/captcha_soat_' + placa + '.png'

    getCaptchaImage(captchaElement, fileNameCaptcha)
    fileNameCaptcha = preprocessImage(fileNameCaptcha)
    stringInCaptcha = decodeStringInImage(fileNameCaptcha)

    print("Placa: " + placa + ' - Captcha: ' + stringInCaptcha)


    if len(stringInCaptcha) == 4:

        # 4. Getting form
        num_placa = browser.find_element_by_xpath("//input[@class='Placa'][@name='textfield']")
        strCAPTCHA = browser.find_element_by_xpath("//input[@class='Placa'][@name='captcha']")

        # 5. Filling form
        num_placa.send_keys(placa)
        strCAPTCHA.send_keys(stringInCaptcha)

        # 6. Sending form
        cmdConsultar = browser.find_element_by_id("SOATForm")
        cmdConsultar.click()

        while (not (len(browser.window_handles) == 2)):
            print("Hay 1 ventana aún")

        print(browser.window_handles)
        new_window = browser.window_handles[1]
        browser.switch_to_window(new_window)

        try:
            WebDriverWait(browser, delay2).until(EC.alert_is_present(),
                                            'Timed out waiting for PA creation ' +
                                            'confirmation popup to appear.')
            alert = browser.switch_to.alert
            alert.accept()
            print("alert accepted")
            return False
        except TimeoutException:
            print("no alert")
            writeRows(browser.page_source)
            return True

    else:
        print("Tiene una cantidad de letras diferente a 4")
        return False

def createResultsDirectory():
    directories = set(os.listdir())
    rootDirectory = 'Resultados'

    if rootDirectory not in directories:
        if not os.path.exists(rootDirectory):
            os.makedirs(rootDirectory)
    return rootDirectory


def downloader(placa,rootDirectory):
    print(placa)
    options = Options()
    options.add_argument("--headless")

    profile = webdriver.FirefoxProfile()
    profile.set_preference("dom.disable_beforeunload", True)

    browser = webdriver.Firefox(firefox_options=options,firefox_profile = profile)
    #browser = webdriver.Firefox()
    browser.set_page_load_timeout(30)

    isDownloaded = scrapingOneDocument(browser, placa,rootDirectory)

    browser.quit()

    return isDownloaded

def main():
    placas = ['B5F445','D5J548','AKQ683','C4D167','B2J433','ABS604','C5Y099']*2
    #placas = ['B5F445', 'D5J548']

    numDownloaded = 0
    rootDirectory = createResultsDirectory()

    '''
    for placa in placas:
        isDownloaded = downloader(placa)
        if isDownloaded:
            numDownloaded += 1

    print(numDownloaded)
    '''


    with ThreadPoolExecutor(max_workers=cpu_count()) as executor:
        futures = [executor.submit(downloader, placa, rootDirectory) for placa in placas]
        #for future in as_completed(futures):
        #    print(future.result())
        #    if future.result():
        #        numDownloaded += 1
    #print("Total: " + str(len(placas)) + " - Descargados: " + str(numDownloaded))


def getCaptchas():
    options = Options()
    options.add_argument("--headless")

    profile = webdriver.FirefoxProfile()
    profile.set_preference("dom.disable_beforeunload", True)

    browser = webdriver.Firefox(firefox_options=options,firefox_profile = profile)
    browser.set_page_load_timeout(30)

    for i in range(200):
        print(i)
        browser.get(url)
        delay = 10  # seconds

        try:
            myElem = WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.CLASS_NAME, 'Placa')))
        except TimeoutException:
            print("Se excedió el tiempo de espera")
            resultsScrappingTsvFile.close()

        captchaElement = browser.find_element_by_xpath("//img[@alt='captcha']")

        fileNameCaptcha = 'Captchas/captcha_soat_' + str(i) + '.png'

        captchaElement.screenshot(fileNameCaptcha)

        img = cv2.imread(fileNameCaptcha, 0)
        crop_img = img[5:5 + 22, 0:0 + 50]
        cv2.imwrite(fileNameCaptcha, crop_img)

try:
    t0 = time.time()
    main()
except:
    print("Unexpected error:", sys.exc_info()[0])
    raise
finally:
    t1 = time.time()
    total_time = int(t1 - t0)
    print("Tiempo total de ejecución: " + str(datetime.timedelta(seconds=total_time)))