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
connect_str = config._AZURE_STORAGE_CONNECTION_STRING
container = config._STORAGE_CONTAINER_INPUT


def getJsonFromBlobStorage(local_path, json_name):
    download_file_path = os.path.join(local_path, json_name)
    try:

        blob_client = BlobClient.from_connection_string(
            conn_str=connect_str, 
            container_name=container, 
            blob_name=json_name)

        blob = blob_client.download_blob().readall()
        
        with open(download_file_path, "wb") as download_file:
            download_file.write(blob)

        print("\nDescargado el json \n\t" + download_file_path)

        return download_file_path
    except:
        print("\nError al descargar el json: \n\t" + download_file_path)
        raise FileExistsError("Error al descargar el archivo")

def getConfigFromTableStorage(cliente, proyecto):
    table_service = TableService(connection_string=config._AZURE_STORAGE_CONNECTION_STRING)
    task = table_service.get_entity(config._STORAGE_TABLE_NAME, cliente, proyecto)
    return (task.cfg_file, task.data_file, task.w_file, task.ypath)

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

    archivoMensaje = getJsonFromBlobStorage(jpath, json_name)

        
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

    #cfg_file  =  "yolov4.cfg"            # Nombre archivo cfg de yolo
    #data_file =  "coco.data"             # Nombre archivo .data de yolo
    #w_file    =  "yolov4.weights"        # Nombre modelo  .weights de yolo
    #ypath     =  './SoftwareOne/2.yolo_files/'     # la ruta donde encuentra estos archivos