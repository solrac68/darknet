del download.sqlite
sqlite3 download.sqlite "CREATE TABLE downloads ( name_file varchar(60) PRIMARY KEY NOT NULL, estado varchar(30));"