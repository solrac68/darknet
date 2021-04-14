import config
from azure.cosmosdb.table.tableservice import TableService
from azure.cosmosdb.table.models import Entity
from azure.cosmosdb.table.tablebatch import TableBatch



if __name__ == '__main__':
    
    table_service = TableService(connection_string=config._AZURE_STORAGE_CONNECTION_STRING)

    try:
        table_service.create_table(config._STORAGE_TABLE_NAME)
    except:
        pass
    
    tasks = []

    tasks.append({'PartitionKey': 'cliente1', 'RowKey': 'proyecto1',
           'cfg_file': 'yolov4.cfg', 'data_file': 'coco.data', 'w_file':'yolov4.weights', 'ypath':'./SoftwareOne/2.yolo_files/' })

    tasks.append({'PartitionKey': 'cliente2', 'RowKey': 'proyecto1',
           'cfg_file': 'yolov4.cfg', 'data_file': 'coco.data', 'w_file':'yolov4.weights', 'ypath':'./SoftwareOne/2.yolo_files/' })

    tasks.append({'PartitionKey': 'cliente3', 'RowKey': 'proyecto1',
           'cfg_file': 'yolov4.cfg', 'data_file': 'coco.data', 'w_file':'yolov4.weights', 'ypath':'./SoftwareOne/2.yolo_files/' })

    tasks.append({'PartitionKey': 'cliente4', 'RowKey': 'proyecto1',
           'cfg_file': 'yolov4.cfg', 'data_file': 'coco.data', 'w_file':'yolov4.weights', 'ypath':'./SoftwareOne/2.yolo_files/' })

    tasks.append({'PartitionKey': 'cliente5', 'RowKey': 'proyecto1',
            'cfg_file': 'yolov4.cfg', 'data_file': 'coco.data', 'w_file':'yolov4.weights', 'ypath':'./SoftwareOne/2.yolo_files/' })

    tasks.append({'PartitionKey': 'cliente6', 'RowKey': 'proyecto1',
            'cfg_file': 'yolov4.cfg', 'data_file': 'coco.data', 'w_file':'yolov4.weights', 'ypath':'./SoftwareOne/2.yolo_files/' })

    tasks.append({'PartitionKey': 'cliente7', 'RowKey': 'proyecto1',
           'cfg_file': 'yolov4.cfg', 'data_file': 'coco.data', 'w_file':'yolov4.weights', 'ypath':'./SoftwareOne/2.yolo_files/' })
    
    tasks.append({'PartitionKey': 'cliente8', 'RowKey': 'proyecto1',
            'cfg_file': 'yolov4.cfg', 'data_file': 'coco.data', 'w_file':'yolov4.weights', 'ypath':'./SoftwareOne/2.yolo_files/' })

    for task in tasks:
        table_service.insert_or_replace_entity(config._STORAGE_TABLE_NAME, task)

    print("Registros de configuración creados")

