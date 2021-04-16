#!/bin/bash
'
Creación de la base de datos sqlite para seguimiento de descargas
'
rm -f download.sqlite || true
sqlite3 download.sqlite "CREATE TABLE downloads ( name_file varchar(60) PRIMARY KEY NOT NULL, estado varchar(30));"
echo "Se crea la base de datos"
