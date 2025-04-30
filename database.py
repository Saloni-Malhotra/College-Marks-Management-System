from flask_mysqldb import MySQL

mysql = MySQL()

def init_db(app):
    app.config['MYSQL_HOST'] = 'localhost'  #host
    app.config['MYSQL_USER'] = 'root'       #user
    app.config['MYSQL_PASSWORD'] = ''  #password
    app.config['MYSQL_DB'] = 'collegemarks'  #name
    mysql.init_app(app)
