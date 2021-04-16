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
# from ctypes import *                                               
# import cv2
# import darknet
# import PIL
# from PIL import Image, ImageDraw, ImageFont, ImageOps
# import urllib.request


### CONFIGURACION
import config

### DEPENDENCIAS DE AZURE
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, __version__
#import boto3
#from boto.s3.key import Key


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
    cfg_file_path = "{}{}".format(ypath,cfg_file)
    data_file_path = "{}{}".format(ypath,data_file)
    w_file_path = "{}{}".format(ypath,w_file)


    print("cfg_file_path: {0}".format(cfg_file_path))
    print("data_file_path: {0}".format(data_file_path))
    print("w_file_path: {0}".format(w_file_path))
    print("ypath: {0}".format(ypath))

    

    if existeArchivoDescargadoEnCarpeta(cfg_file_path):
        print("Archivo {0} existente".format(cfg_file_path))
    else:
        path = getFromBlobStorage(ypath,cfg_file,config._STORAGE_CONTAINER_MODEL)
        print("Descargado el archivo de configuración {0}".format(cfg_file_path))

    if existeArchivoDescargadoEnCarpeta(data_file_path):
        print("Archivo {0} existente".format(data_file_path))
    else:
        path = getFromBlobStorage(ypath,data_file,config._STORAGE_CONTAINER_MODEL)
        print("Descargado el archivo de configuración {0}".format(data_file_path))

    if existeArchivoDescargadoEnCarpeta(w_file_path):
        print("Archivo {0} existente".format(w_file_path))
    else:
        #path = getFromBlobStorage(ypath,w_file,config._STORAGE_CONTAINER_MODEL)
        if not(getExisteFile(w_file_path)) or getEstadoDescarga(w_file_path) == config._DOWNLOADED:
            setEstadoDescarga(w_file_path, config._DOWNLOADING)
            print("Inicia descarga de {}".format(w_file_path))
            path = getFromBlobStorage(ypath,w_file,config._STORAGE_CONTAINER_MODEL)
            setEstadoDescarga(w_file_path, config._DOWNLOADED)
            print("Descargado el archivo de configuración {0}".format(w_file_path))
        else:
            if espera_por_descarga_weight(w_file_path,datetime.timedelta(minutes=5)) and existeArchivoDescargadoEnCarpeta(w_file_path):
                print("Archivo {0} descargado por otra tarea con exito".format(w_file_path))
            else:
                raise Exception("Otra tarea no descargo correctamente el archivo {}".format(w_file_path))

def getMensajeJson(jpath1,json_name):
    archivoMensaje = getFromBlobStorage(jpath1, json_name,config._STORAGE_CONTAINER_INPUT)

    print("Descargado el json {0}".format(archivoMensaje))
    
    with open(archivoMensaje) as json_file:
        res= json.loads(json_file.read())
        
    cliente  = str(res["master_customer"])
    proyecto = str(res["proyecto"])
    job_id   = str(res["job_id"])
    imglist = res["img_cap"]

    print("cliente: {0}\nproyecto: {1}\njob_id: {2}".format(cliente,proyecto,job_id))

    [print("imagen: {0}".format(img)) for img in imglist]

    return (cliente,proyecto,job_id,imglist)


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
    (cliente,proyecto,job_id,imglist) = getMensajeJson(jpath1,json_name)

    ### PASO No 3.  CONSULTA BASE DE DATOS SEGUN CLIENTE Y PROYECTO Y TRAE:
    (cfg_file, data_file, w_file, ypath) = getConfigFromTableStorage(cliente, proyecto)

    ### PASO No 3.1 Descargando el modelo y los archivos de configuración desde azure storage hacia la ruta ypath
    descargaModeloDesdeStorage(cfg_file, data_file, w_file, ypath)
    
    # Tiempo total de procesamiento de la tarea
    toc=timeit.default_timer()
    print("Tiempo de la descarga en segundos (tic): {0}".format(str(toc-tic)))



    # path = getFromBlobStorage(ypath,w_file,config._STORAGE_CONTAINER_MODEL)
    # print("Descargado el archivo de configuración {0}".format(path))

 
    # toc=timeit.default_timer()

    # print("Tiempo inicial (tic): {0}, Tiempo final {1}".format(tic,toc)) 

    # print("Tiempo de la descarga en segundos (tic): {0}".format(str(toc-tic)))

    #cfg_file  =  "yolov4.cfg"            # Nombre archivo cfg de yolo
    #data_file =  "coco.data"             # Nombre archivo .data de yolo
    #w_file    =  "yolov4.weights"        # Nombre modelo  .weights de yolo
    #ypath     =  './SoftwareOne/2.yolo_files/'     # la ruta donde encuentra estos archivos