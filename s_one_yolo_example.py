### DEPENDENCIAS GENERALES
import numpy as np
import pandas as pd
import random
import datetime
import string
import shutil
import math
import io, os
import time
import glob
import matplotlib.pyplot as plt
import math
import csv
import json
import urllib.request
from ast import literal_eval
from collections import Counter
import warnings
warnings.filterwarnings('ignore')
warnings.simplefilter(action='ignore', category=FutureWarning)


################  YOLO:
from ctypes import *                                               
import cv2
import darknet
import PIL
from PIL import Image, ImageDraw, ImageFont, ImageOps
import urllib.request



### YOLO SET INICIAL
netMain = None
metaMain = None
altNames = None


def convertBack(x, y, w, h):
    xmin = int(round(x - (w / 2)))
    xmax = int(round(x + (w / 2)))
    ymin = int(round(y - (h / 2)))
    ymax = int(round(y + (h / 2)))
    return xmin, ymin, xmax, ymax

def cvDrawBoxes(detections, img, t_size):
    for detection in detections:
        x, y, w, h = detection[2][0],\
            detection[2][1],\
            detection[2][2],\
            detection[2][3]
        xmin, ymin, xmax, ymax = convertBack(
            float(x), float(y), float(w), float(h))
        pt1 = (xmin, ymin)
        pt2 = (xmax, ymax)
        cv2.rectangle(img, pt1, pt2, (0, 255, 0), 2)
        cv2.putText(img,
                    detection[0].decode()  +
                    " [" + str(round(detection[1] * 100, 1)) + "]",
                    (pt1[0], pt1[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, t_size,  
                    [0, 255, 0], 2)
    return img


def YOLO(imglist, config):
    
    global metaMain, netMain, altNames

    configPath = config[0]
    weightPath = config[1]      
    metaPath   = config[2]  
    w_path     = config[3]  
    job_id     = config[4] 
    jpath      = config[5] 

    #imagePath  = path_write
    print('#################  TASK', job_id, '####################')


    if not os.path.exists(configPath):                        
        raise ValueError("Invalid config path `" +
                         os.path.abspath(configPath)+"`")
    if not os.path.exists(weightPath):
        raise ValueError("Invalid weight path `" +
                         os.path.abspath(weightPath)+"`")
    if not os.path.exists(metaPath):
        raise ValueError("Invalid data file path `" +
                         os.path.abspath(metaPath)+"`")
    if netMain is None:                                             
        netMain = darknet.load_net_custom(configPath.encode( 
            "ascii"), weightPath.encode("ascii"), 0, 1)             
    if metaMain is None:
        metaMain = darknet.load_meta(metaPath.encode("ascii"))
    if altNames is None:
        try:
            with open(metaPath) as metaFH:
                metaContents = metaFH.read()
                import re
                match = re.search("names *= *(.*)$", metaContents,
                                  re.IGNORECASE | re.MULTILINE)
                if match:
                    result = match.group(1)
                else:
                    result = None
                try:
                    if os.path.exists(result):
                        with open(result) as namesFH:
                            namesList = namesFH.read().strip().split("\n")
                            altNames = [x.strip() for x in namesList]
                except TypeError:
                    pass
        except Exception:
            pass
    
    
    print('[INFO]: Empezando OBJECT DETECTION')
    
    cont = 1
    err = False
    for imagelistfile in imglist:

        try:
            print(imagelistfile)
            #try:
            image = cv2.imread(imagelistfile, cv2.IMREAD_COLOR)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            h=image.shape[0]
            w=image.shape[1] 

            ### TAMANO DE TEXTOS
            t_size = (h/3000)  
            
            #image = cv2.imread(imagelistfile )
            name_file = os.path.basename(imagelistfile)
            name_file2 = os.path.basename(imagelistfile)
            
            print('[INFO]: Analizando', name_file )
            name_file = name_file.split('.')
            name_file = name_file[0]
            

            darknet_image = darknet.make_image(w, h, 3)

            frame_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            frame_resized = cv2.resize(frame_rgb, (w, h), interpolation=cv2.INTER_LINEAR)

            darknet.copy_image_from_bytes(darknet_image,frame_resized.tobytes())  
            print('[INFO]: Detecciones Realizadas', name_file )
            
            detections = darknet.detect_image(netMain, metaMain, darknet_image, thresh=0.25) 
            image = cvDrawBoxes(detections, frame_resized, t_size)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            scale_percent = 50
            width = int(w * scale_percent / 100)
            height = int(h * scale_percent / 100)
            dsize = (width, height)
            # resize image
            image2 = image.copy()
            image2 = cv2.cvtColor(image2, cv2.COLOR_BGR2RGB)
            image2 = cv2.resize(image2, dsize)
            image2 = cv2.cvtColor(image2, cv2.COLOR_BGR2RGB)
            
            fig=plt.figure(figsize=(10, 10))
            qty_annot = len(detections)
            columns = 6
            rows = math.ceil(qty_annot/columns)
            i=0

            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            img = Image.fromarray(image)
            
            x1_list       = []
            y1_list       = []
            x2_list       = []
            y2_list       = []
            
            for d in detections:   
                x1 = int(d[2][0]-d[2][2]/2) if int(d[2][0]-d[2][2]/2) < img.size[0] else img.size[0] 
                x2 = int(d[2][0]+d[2][2]/2) if int(d[2][0]+d[2][2]/2) < img.size[0] else img.size[0] 
                y1 = int(d[2][1]-d[2][3]/2) if int(d[2][1]-d[2][3]/2) < img.size[1] else img.size[1] 
                y2 = int(d[2][1]+d[2][3]/2) if int(d[2][1]+d[2][3]/2) < img.size[1] else img.size[1] 
                #print(x1,x2,y1,y2)
                #print(d,'\n')
                if x1<0:
                    x1=0
                if x2<0:
                    x2=0
                if y1<0:
                    y1=0
                if y2<0:
                    y2=0
                if x1>=img.size[0] or x2>img.size[0]:
                    x1, y1 = y1, x1
                    x2, y2 = y2, x2 
                if y1>=img.size[1] or y2>img.size[1]:
                    x1, y1 = y1, x1
                    x2, y2 = y2, x2 

                box  = [int(x1), int(y1),
                                int(x2),int(y2)]

                x1_list.append(x1)
                y1_list.append(y1)
                x2_list.append(x2)
                y2_list.append(y2)
                
                img_brand = img.crop(box)

                fig.add_subplot(rows, columns, i+1) 
                i=i+1
                plt.imshow(img_brand)
                
            #plt.show() 
            
            print('[INFO]: Catalogo Realizado ', name_file , 'imagen ', cont, '/', str(len(imglist)))
            
            

            ###### CReando y guardando el csv de detecciones
            label_list    = []
            accuracy_list = []
        

            for i in range(0, len(detections)):
                label    = detections[i][0]
                accuracy = detections[i][1]
            
                label_list.append(label)
                accuracy_list.append(accuracy)
            
            df = pd.DataFrame(columns=['img_name', 'Object_Type','Confidence','x1','y1','x2','y2','Width','Height'])
            df['Object_Type']               = label_list
            df['Confidence']                = accuracy_list
            df['x1']                        = x1_list
            df['y1']                        = y1_list
            df['x2']                        = x2_list
            df['y2']                        = y2_list
            df['Width']                     = w
            df['Height']                    = h
            df['img_name']                  = name_file2
            df['job_id']                    = str(job_id)

            
            ###### GRABANDO ARCHIVOS LOCALES
            k1_name = w_path + "/" + job_id + "_"+ str(cont) + ".jpg"
            cv2.imwrite(k1_name, image2)

            k2_name = w_path + "/" + job_id + "_"+ str(cont) + "c.jpg"
            plt.savefig(k2_name)
            plt.close(fig)
            
            k3_name = w_path + "/data_" + job_id + "_"+ str(cont) +".csv"
            df.to_csv(k3_name, sep=',', encoding='utf-8')


            print('[INFO]: csv guardado ', k3_name, cont, '/', str(len(imglist)))
            

            print( cont, "/", len(imglist)) 
            cont = cont + 1

        except:
            err = True
            pass

    ## PUBLICANDO STEP YOLO HECHO.
    if err == False:
        jsonfile   = "data_" + str(job_id) + ".json"
        shutil.move(jpath + '/' + jsonfile , "./SoftwareOne/1. step2/" ) 
        print('[INFO]: Object detection Terminado ', job_id)

    else:
        jsonfile   = "data_" + str(job_id) + ".json"
        shutil.move(jpath + '/' + jsonfile , "./SoftwareOne/1. steperror/" ) 
        print('[INFO]:ERROR' , job_id)



### PASO No 1. LEER EL JSONS EN COLA
jpath = './SoftwareOne/1. step1/'
data_jsons = os.listdir(jpath)

if len(data_jsons)>0:

    for jsonfile in data_jsons:
    
        ### PASO No 2.  ABRIENDO JSON:
        with open(jpath + jsonfile ) as json_file:
            res= json.loads(json_file.read())

        cliente  = str(res["master_customer"])
        proyecto = str(res["proyecto"])
        job_id   = str(res["job_id"])
        imglist = res["img_cap"]

        json_file.close()

        ### PASO No 3.  CONSULTA BASE DE DATOS SEGUN CLIENTE Y PROYECTO Y TRAE:
        cfg_file  =  "yolov4.cfg"            # Nombre archivo cfg de yolo
        data_file =  "coco.data"             # Nombre archivo .data de yolo
        w_file    =  "yolov4.weights"        # Nombre modelo  .weights de yolo
        ypath     =  './SoftwareOne/2.yolo_files/'     # la ruta donde encuentra estos archivos

        ## PASO No 4.  RUTA PARA GRABAR RESULTADOS:
        w_path = './SoftwareOne/3. tasks/' + cliente + "/" + job_id +"/"
        if not os.path.exists(w_path):
            os.makedirs(w_path)


        ## PASO No 5.  ARMANDO EL CONFIG:
        configPath = ypath  + cfg_file 
        weightPath = ypath  + w_file     
        metaPath   = ypath  + data_file
        config     = [configPath, weightPath, metaPath,w_path,job_id, jpath]

        ## PASO No 6.  LLAMANDO FUNCION:
        print("[CONFIG]", config, imglist)
        YOLO(imglist,config)

else:
    print("NADA EN COLA POR PREOCESAR")