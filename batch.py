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

def setEstadoDescarga(fileName, estado):
    conn = sqlite3.connect(config._DATABASE_SQLITE_DOWNLOAD)

    if not(getExisteFile(fileName)):
        query = "INSERT INTO {0} name_file, estado VALUES ('{1}','{2}')".format(config._TABLE_SQLITE,fileName,estado)
    else:
        query = "UPDATE {0} set estado = '{1}' where name_file = '{2}'".format(config._TABLE_SQLITE,estado,fileName)
    conn.execute(query)
    conn.commit()
    numrows = conn.total_changes
    conn.close()
    
    return numrows

def getExisteFile(fileName):
    conn = sqlite3.connect(config._DATABASE_SQLITE_DOWNLOAD)
    query = "SELECT count(*) from downloads where name_file = '{0}'".format(fileName)
    cursor = conn.execute(query)
    num = cursor.fetchone()[0]
    conn.close()
    
    return num > 0
    

def getEstadoDescarga(fileName):
    conn = sqlite3.connect(config._DATABASE_SQLITE_DOWNLOAD)
    query = "SELECT estado from downloads where name_file = '{0}'".format(fileName)
    cursor = conn.execute(query)
    estado = cursor.fetchone()[0]
    conn.close()
    return estado

### PASO No 1. LEER EL JSONS EN COLA
jpath = './SoftwareOne/1. step1/'
#data_jsons = os.listdir(jpath)

# Nombre del archivo json a procesar.
if __name__ == '__main__':

    # Iniciando el desarrollo personalizado

    print(len(sys.argv))

    if len(sys.argv) == 2:
        json_name = str(sys.argv[1])
    elif len(sys.argv) == 1:
        json_name = "68a11879-7434-420f-bb09-cde500c0b95b.json"
    else:
        raise ValueError("La parametros son incorrectos")

    archivoMensaje = getFromBlobStorage(jpath, json_name,config._STORAGE_CONTAINER_INPUT)
    print("Descargado el json {0}".format(archivoMensaje))

        
    ### PASO No 2.  ABRIENDO JSON:
    with open(archivoMensaje) as json_file:
        res= json.loads(json_file.read())
        
    cliente  = str(res["master_customer"])
    proyecto = str(res["proyecto"])
    job_id   = str(res["job_id"])
    imglist = res["img_cap"]

    print("cliente: {0}\nproyecto: {1}\njob_id: {2}".format(cliente,proyecto,job_id))

    [print("imagen: {0}".format(img)) for img in imglist]


    ### PASO No 3.  CONSULTA BASE DE DATOS SEGUN CLIENTE Y PROYECTO Y TRAE:
    (cfg_file, data_file, w_file, ypath) = getConfigFromTableStorage(cliente, proyecto)

    print("cfg_file: {0}".format(cfg_file))
    print("data_file: {0}".format(data_file))
    print("w_file: {0}".format(w_file))
    print("ypath: {0}".format(ypath))

    ### PASO No 3.1 Descargando el modelo y los archivos de configuración del mismo desde azure storage hacia la ruta ypath
 
    tic=timeit.default_timer()

    path = getFromBlobStorage(ypath,cfg_file,config._STORAGE_CONTAINER_MODEL)
    print("Descargado el archivo de configuración {0}".format(path))

    path = getFromBlobStorage(ypath,data_file,config._STORAGE_CONTAINER_MODEL)
    print("Descargado el archivo de configuración {0}".format(path))

    path = getFromBlobStorage(ypath,w_file,config._STORAGE_CONTAINER_MODEL)
    print("Descargado el archivo de configuración {0}".format(path))

 
    toc=timeit.default_timer()

    print("Tiempo inicial (tic): {0}, Tiempo final {1}".format(tic,toc)) 

    print("Tiempo de la descarga en segundos (tic): {0}".format(str(toc-tic)))

    #cfg_file  =  "yolov4.cfg"            # Nombre archivo cfg de yolo
    #data_file =  "coco.data"             # Nombre archivo .data de yolo
    #w_file    =  "yolov4.weights"        # Nombre modelo  .weights de yolo
    #ypath     =  './SoftwareOne/2.yolo_files/'     # la ruta donde encuentra estos archivos