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
#import seaborn as sns
import warnings
warnings.filterwarnings('ignore')
warnings.simplefilter(action='ignore', category=FutureWarning)
import sys
from azure.cosmosdb.table.tableservice import TableService
import timeit
import sqlite3



################  YOLO:
from ctypes import *                                               
import cv2
import darknet
import PIL
from PIL import Image, ImageDraw, ImageFont, ImageOps
import urllib.request


### CONFIGURACION
import config
### DEPENDENCIAS DE AZURE
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, __version__
import azure.core.exceptions
from azure.storage.queue import (
        QueueClient,
        BinaryBase64EncodePolicy,
        BinaryBase64DecodePolicy
)


### YOLO SET INICIAL
netMain = None
metaMain = None
altNames = None


# Almacene esta información en una variable del sistema operativo - export AZURE_STORAGE_CONNECTION_STRING="<yourconnectionstring>"
# O Almacene en azure key vault
#_AZURE_STORAGE_CONNECTION_STRING = config._AZURE_STORAGE_CONNECTION_STRING
#_STORAGE_CONTAINER_INPUT = config._STORAGE_CONTAINER_INPUT
#_STORAGE_CONTAINER_MODEL = config._STORAGE_CONTAINER_MODEL

### Base de datos local creada en 2.yolo_files en start_task para controlar la descarga de archivos grandes desde azure storage.
# sqlite3 download.sqlite "CREATE TABLE downloads ( name_file varchar(60) PRIMARY KEY NOT NULL, estado varchar(30));"

def readFile(filePath):
    with open(filePath) as json_file:
        res= json.loads(json_file.read())
    return json.dumps(res)

def createContainer(container):
    try:
        container_client = BlobClient.from_connection_string(
            conn_str=config._AZURE_STORAGE_CONNECTION_STRING, 
            container_name=container)
        
        container_client.create_container()
    except:
        pass

def uploadToContainer(local_path, blob,container):
    blob_client = BlobClient.from_connection_string(
            conn_str=config._AZURE_STORAGE_CONNECTION_STRING, 
            container_name=container, 
            blob_name=blob)

    with open(local_path, "rb") as data:
        blob_client.upload_blob(data)

def crearQueue(q_name):  
    print("Creando la cola: " + q_name)
    queue_client = QueueClient.from_connection_string(config._AZURE_STORAGE_CONNECTION_STRING, q_name)
    try:
        queue_client.create_queue()
    except azure.core.exceptions.ResourceExistsError as aze:
        pass

def addMessagesQueue(mensajes,q_name):
    queue_client = QueueClient.from_connection_string(config._AZURE_STORAGE_CONNECTION_STRING, q_name)
    [queue_client.send_message(message) for message in mensajes]
    print("Mensajes agregados")
    

def getFromBlobStorage(local_path, blob,container):
    download_file_path = os.path.join(local_path, blob)
    try:

        blob_client = BlobClient.from_connection_string(
            conn_str=config._AZURE_STORAGE_CONNECTION_STRING, 
            container_name=container, 
            blob_name=blob)

        blob = blob_client.download_blob().readall()
        
        with open(download_file_path, "wb") as download_file:
            download_file.write(blob)

        return download_file_path
    except:
        print("\nError al descargar el blob: \n\t" + download_file_path)
        raise FileExistsError("Error al descargar el blob")

def getConfigFromTableStorage(cliente, proyecto):
    table_service = TableService(connection_string=config._AZURE_STORAGE_CONNECTION_STRING)
    task = table_service.get_entity(config._STORAGE_TABLE_NAME, cliente, proyecto)
    return (task.cfg_file, task.data_file, task.w_file, task.ypath)

def setEstadoDescarga(filepath, estado):
    conn = sqlite3.connect(config._DATABASE_SQLITE_DOWNLOAD)

    if not(getExisteFile(filepath)):
        query = "INSERT INTO {0} (name_file, estado) VALUES ('{1}','{2}')".format(config._TABLE_SQLITE,filepath,estado)
    else:
        query = "UPDATE {0} set estado = '{1}' where name_file = '{2}'".format(config._TABLE_SQLITE,estado,filepath)
    print(query)
    conn.execute(query)
    conn.commit()
    numrows = conn.total_changes
    conn.close()
    
    return numrows

def getExisteFile(filepath):
    conn = sqlite3.connect(config._DATABASE_SQLITE_DOWNLOAD)
    query = "SELECT count(*) from downloads where name_file = '{0}'".format(filepath)
    cursor = conn.execute(query)
    num = cursor.fetchone()[0]
    conn.close()
    
    return num > 0
    

def getEstadoDescarga(filepath):
    conn = sqlite3.connect(config._DATABASE_SQLITE_DOWNLOAD)
    query = "SELECT estado from downloads where name_file = '{0}'".format(filepath)
    cursor = conn.execute(query)
    estado = cursor.fetchone()[0]
    conn.close()
    return estado

def vericarCarpetasSalida():
    paths = ['./SoftwareOne/1. step1/', './SoftwareOne/1. step2/',
    './SoftwareOne/1. steperror/','./SoftwareOne/2.yolo_files/',
    './SoftwareOne/3. tasks/'] 
    
    for path in paths:
        if not(os.path.isdir(path)): os.mkdir(path)

    crearQueue(config._QUEUE_TOPIC_STITCHING)
    crearQueue(config._QUEUE_TOPIC_OBJECT_ERROR)

def existeArchivoDescargadoEnCarpeta(filepath):
    return os.path.isfile(filepath)


def espera_por_descarga_weight(filepath,timeout):

    timeout_expiration = datetime.datetime.now() + timeout

    print("Monitoreando la descarga, tiempo de expiración {}..."
          .format(timeout), end='')

    while datetime.datetime.now() < timeout_expiration:
        print('.', end='')
        sys.stdout.flush()
        
        if getEstadoDescarga(filepath) == config._DOWNLOADED:
            print()
            return True
        else:
            time.sleep(1)
    
    return False

### Descargando el modelo y los archivos de configuración desde azure storage hacia la ruta ypath
def descargaModeloDesdeStorage(cfg_file, data_file, w_file, ypath):
    configPath = "{}{}".format(ypath,cfg_file)
    metaPath = "{}{}".format(ypath,data_file)
    weightPath = "{}{}".format(ypath,w_file)

    print("configPath: {0}".format(configPath))
    print("metaPath: {0}".format(metaPath))
    print("weightPath: {0}".format(weightPath))
    print("ypath: {0}".format(ypath))

    if existeArchivoDescargadoEnCarpeta(configPath):
        print("Archivo {0} existente".format(configPath))
    else:
        path = getFromBlobStorage(ypath,cfg_file,config._STORAGE_CONTAINER_MODEL)
        print("Descargado el archivo de configuración {0}".format(configPath))

    if existeArchivoDescargadoEnCarpeta(metaPath):
        print("Archivo {0} existente".format(metaPath))
    else:
        path = getFromBlobStorage(ypath,data_file,config._STORAGE_CONTAINER_MODEL)
        print("Descargado el archivo de configuración {0}".format(metaPath))

    if existeArchivoDescargadoEnCarpeta(weightPath):
        print("Archivo {0} existente".format(weightPath))
    else:
        #path = getFromBlobStorage(ypath,w_file,config._STORAGE_CONTAINER_MODEL)
        if not(getExisteFile(weightPath)) or getEstadoDescarga(weightPath) == config._DOWNLOADED:
            setEstadoDescarga(weightPath, config._DOWNLOADING)
            print("Inicia descarga de {}".format(weightPath))
            path = getFromBlobStorage(ypath,w_file,config._STORAGE_CONTAINER_MODEL)
            setEstadoDescarga(weightPath, config._DOWNLOADED)
            print("Descargado el archivo de configuración {0}".format(weightPath))
        else:
            if espera_por_descarga_weight(weightPath,datetime.timedelta(minutes=5)) and existeArchivoDescargadoEnCarpeta(weightPath):
                print("Archivo {0} descargado por otra tarea con exito".format(weightPath))
            else:
                raise Exception("Otra tarea no descargo correctamente el archivo {}".format(weightPath))
    
    return (configPath, metaPath, weightPath)

def getMensajeJson(jpath1,json_name):
    filePathJson = getFromBlobStorage(jpath1, json_name,config._STORAGE_CONTAINER_INPUT)

    print("Descargado el json {0}".format(filePathJson))
    
    with open(filePathJson) as json_file:
        res= json.loads(json_file.read())
        
    cliente  = str(res["master_customer"])
    proyecto = str(res["proyecto"])
    job_id   = str(res["job_id"])
    imglist = res["img_cap"]

    print("cliente: {0}\nproyecto: {1}\njob_id: {2}".format(cliente,proyecto,job_id))

    [print("imagen: {0}".format(img)) for img in imglist]

    return (cliente,proyecto,job_id,imglist,filePathJson)

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

    # Almacena la ubicación de los resultados
    images_result  = []
    cvs_result = []

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

            #images_result  = []
            #cvs_result = []
            
            ###### GRABANDO ARCHIVOS LOCALES
            file = job_id + "_"+ str(cont) + ".jpg"
            k1_name = w_path + "/" + file
            cv2.imwrite(k1_name, image2)
            images_result.append((file,k1_name))

            file = job_id + "_"+ str(cont) + "c.jpg"
            k2_name = w_path + "/" + file
            plt.savefig(k2_name)
            plt.close(fig)
            images_result.append((file,k2_name))
            
            file = "data_" + job_id + "_"+ str(cont) +".csv"
            k3_name = w_path + "/" + file
            df.to_csv(k3_name, sep=',', encoding='utf-8')
            cvs_result.append((file,k3_name))


            print('[INFO]: csv guardado ', k3_name, cont, '/', str(len(imglist)))
            

            print( cont, "/", len(imglist)) 
            cont = cont + 1

        except:
            err = True
            pass
    
    #jsonfile   = "data_" + str(job_id) + ".json"
    #jsonfilePath = ""
    
    ## PUBLICANDO STEP YOLO HECHO.
    if err == False:
        #shutil.move(filepathJson, "./SoftwareOne/1. step2/" ) 
        #newPath = "./SoftwareOne/1. step2/{}"
        print('[INFO]: Object detection Terminado ', job_id)
    else:
        #shutil.move(filepathJson, "./SoftwareOne/1. steperror/" ) 
        #newPath = "./SoftwareOne/1. steperror/{}"
        print('[INFO]:ERROR' , job_id)
    
    #_, path_and_file = os.path.splitdrive(filepathJson)
    #_, file = os.path.split(path_and_file)

    #newfilepathJson =  newPath.format(file)
    
    return (err,images_result,cvs_result)


jpath1 = './SoftwareOne/1. step1/'

# Nombre del archivo json a procesar.
if __name__ == '__main__':

    # Iniciando el desarrollo personalizado
    tic=timeit.default_timer()

    if len(sys.argv) == 2:
        json_name = str(sys.argv[1])
    else:
        raise ValueError("La parametros son incorrectos")
    
    ### Verifica que existan las carpetas para los resultados
    vericarCarpetasSalida()

    ### PASO No 2.  ABRIENDO JSON:
    (cliente,proyecto,job_id,imglist,filepathJson) = getMensajeJson(jpath1,json_name)

    ### PASO No 3.  CONSULTA BASE DE DATOS SEGUN CLIENTE Y PROYECTO Y TRAE:
    (cfg_file, data_file, w_file, ypath) = getConfigFromTableStorage(cliente, proyecto)

    ### PASO No 3.1 Descargando el modelo y los archivos de configuración desde azure storage hacia la ruta ypath
    (configPath, metaPath, weightPath) = descargaModeloDesdeStorage(cfg_file, data_file, w_file, ypath)


    ## PASO No 4.  RUTA PARA GRABAR RESULTADOS:
    w_path = './SoftwareOne/3. tasks/' + cliente + "/" + job_id +"/"
    if not os.path.exists(w_path):
        os.makedirs(w_path)

    ## PASO No 5.  ARMANDO EL CONFIG:
    configYolo = [configPath, weightPath, metaPath,w_path,job_id, jpath1]

    ## PASO No 6.  LLAMANDO FUNCION:
    print("[CONFIG]", config, imglist)   
    (err,images_result,cvs_result) = YOLO(imglist,configYolo)

    ## PASO NO 6.1. UBICACIÓN DE RESULTADOS
    print("########################RESULTADOS FINALES############################")
    [print("Imagenes: {}".format(local_path)) for (blob,local_path) in images_result]
    [print("Cvs: {}".format(local_path)) for (blob,local_path) in cvs_result]
    print("######################################################################")


    ## PASO No 7.  VOLCANDO RESULTADOS A LOS CONTENEDORES Y A LA COLA:
    createContainer(cliente)
    [uploadToContainer(local_path, blob,cliente) for (blob,local_path) in images_result]
    [uploadToContainer(local_path, blob,cliente) for (blob,local_path) in cvs_result]
    
    ## PASO No 8.  VOLCANDO MENSAJE A LA COLAS:
    message = readFile(filepathJson)
    addMessagesQueue(message,config._QUEUE_TOPIC_STITCHING) if err == True else addMessagesQueue(message,config._QUEUE_TOPIC_STITCHING)
    
    # Tiempo total de procesamiento de la tarea
    toc=timeit.default_timer()
    print("Tiempo de procesamiento en segundos (tic): {0}".format(str(toc-tic)))