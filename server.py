import io

from flask import Flask, request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlite3 import dbapi2 as sqlite

import model
from mapping import *


app = Flask('mapvis')
#app.config.from_object('mapvis')

app.config.update(dict(DATABASE='sqlite+pysqlite:///mapvis.db'))
app.config.from_envvar('MAPVIS_SETTINGS', silent=True)


engine = create_engine(app.config['DATABASE'], module=sqlite)
Session = sessionmaker(bind=engine)


@app.route("/")
def hello():
    return "<html><body><form method='POST' action='upload' enctype='multipart/form-data'><input type='file' name='data'/><input type='submit' value='submit'/></form></body></html>"

@app.route("/upload", methods=['POST'])
def upload_file():
    upload = request.files['data']
    stream = io.BytesIO(upload.read())

    _, ext = os.path.splitext(upload.filename)
    file_type = ext.lstrip(".")

    return str(read_spreadsheet(file_type, stream))



if __name__ == '__main__':
    app.run(debug=True)

