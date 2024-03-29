import configparser
import datetime
import json
import os

import pymysql
import psycopg2
import requests


class Logger:
    __level = {
        'none': -1,
        'debug': 50,
        'info': 40,
        'warning': 30,
        'error': 20,
        'critical': 10
    }
    __name_time = ''
    __name = ''
    __str = ''
    __file = ''
    __file_time = ''
    __console_log = 50
    __file_log = -1
    __database_log_mysql = -1
    __database_log_postgres = -1
    __slack_log = -1
    __service = 'example'
    __file_mode = 'default'

    def __init__(self, directory=''):
        if directory != '':
            self.__config = configparser.ConfigParser()
            self.__config.read(directory)
            self.__console_log = self.__level[str(self.__config['output']['console'])]
            self.__file_log = self.__level[str(self.__config['output']['file'])]
            self.__type_db = self.__config['typedatabase']['type']
            self.__database_log_mysql = self.__level[str(self.__config['output']['mysql'])]
            self.__database_log_postgres = self.__level[str(self.__config['output']['postgres'])]
            self.__slack_log = self.__level[str(self.__config['output']['slack'])]
            self.__service = self.__config['service']['name']

            if self.__file_log != -1:
                self.__file_mode = self.__config['file']['mode']
                name_list = self.__config['file']['filename'].split('.')
                name_list.remove('txt')
                if self.__file_mode == 'timestamp':
                    create_time = datetime.datetime.now()
                    self.__name_time = '.'.join(name_list) + '-' \
                                       + str(datetime.date.today()) + '-' \
                                       + str(create_time.hour) + '-' \
                                       + str(create_time.minute) + '-' \
                                       + str(create_time.second) + '.txt'
                    self.__file_time = os.path.join(self.__config['file']['directory'], self.__name_time)
                    self.__name = '.'.join(name_list) + '.txt'
                    self.__file = os.path.join(self.__config['file']['directory'], self.__name)
                if self.__file_mode == 'default':
                    self.__name = '.'.join(name_list) + '.txt'
                    self.__file = os.path.join(self.__config['file']['directory'], self.__name)
                if self.__file_mode == 'current':
                    self.__name = '.'.join(name_list) + '.txt'
                    self.__file = os.path.join(self.__config['file']['directory'], self.__name)
            if self.__database_log_mysql != -1:
                self.__create_table(self.__type_db)
            if self.__database_log_postgres != -1:
                self.__create_table(self.__type_db)


    def __create_table(self,type_db):
        self.__conn_mysql = pymysql.connect(
                host=self.__config['mysql']['host'],
                port=int(self.__config['mysql']['port']),
                user=self.__config['mysql']['user'],
                password=self.__config['mysql']['password'],
                database=self.__config['mysql']['database'],
                cursorclass=pymysql.cursors.DictCursor
            )
        self.__conn_postgres = psycopg2.connect(dbname=self.__config['postgres']['database'],
                                                   user=self.__config['postgres']['user'],
                                                   password=self.__config['postgres']['password'],
                                                   host=self.__config['postgres']['host'],
                                                   port=self.__config['postgres']['port'])
        if type_db == "mysql":
            self.__cursor_mysql = self.__conn_mysql.cursor()
            try:
                self.__cursor_mysql.execute("CREATE TABLE {0} (id int auto_increment primary key,"
                                      "timestamp datetime default CURRENT_TIMESTAMP not null,"
                                      "message varchar(255) not null,"
                                      "service varchar(255) not null,"
                                      "level varchar(255) not null);".format(self.__config['mysql']['table']))
                self.__conn_mysql.commit()
            except:
                self.__conn_mysql.rollback()
        elif type_db == "postgres":
                    self.__cursor_postgres = self.__conn_postgres.cursor()
                    try:
                        self.__cursor_postgres.execute("CREATE TABLE {0} (id serial primary key,"
                                              "timestamp timestamp default CURRENT_TIMESTAMP not null,"
                                              "message varchar(255) not null,"
                                              "service varchar(255) not null,"
                                              "level varchar(255) not null);".format(self.__config['postgres']['table']))
                        self.__conn_postgres.commit()
                    except:
                        self.__conn_postgres.rollback()
        elif type_db == "mysql_postgres":
            self.__cursor_mysql = self.__conn_mysql.cursor()
            self.__cursor_postgres = self.__conn_postgres.cursor()
            try:
                self.__cursor_mysql.execute("CREATE TABLE {0} (id int auto_increment primary key,"
                                      "timestamp datetime default CURRENT_TIMESTAMP not null,"
                                      "message varchar(255) not null,"
                                      "service varchar(255) not null,"
                                      "level varchar(255) not null);".format(self.__config['mysql']['table']))
                self.__conn_mysql.commit()
            except:
                self.__conn_mysql.rollback()

            try:
                self.__cursor_postgres.execute("CREATE TABLE {0} (id serial primary key,"
                                      "timestamp timestamp default CURRENT_TIMESTAMP not null,"
                                      "message varchar(255) not null,"
                                      "service varchar(255) not null,"
                                      "level varchar(255) not null);".format(self.__config['postgres']['table']))
                self.__conn_postgres.commit()
            except:
                self.__conn_postgres.rollback()


    def __db_write(self, level, message, time, db=None):
        logg = [(time, message, self.__service, level)]
        if db == 'mysql':
            if self.__database_log_mysql != -1:
                self.__cursor_mysql.executemany(
                    'INSERT INTO {0} (timestamp, message, service, level) VALUES (%s,%s,%s,%s)'.format(self.__config['mysql']['table']), logg)
                self.__conn_mysql.commit()
        if db == 'postgres':
            if self.__database_log_postgres != -1:
                self.__cursor_postgres.executemany('INSERT INTO {0} (timestamp, message, service, level) VALUES (%s,%s,%s,%s)'.format(self.__config['postgres']['table']), logg)
                self.__conn_postgres.commit()


    def __file_write(self, level, message, time):
        self.__str = str(time) + ' | ' + str(message) + ' | ' + self.__service + ' | ' + level + '\n'
        if self.__file_mode == 'default':
            self.__f = open(self.__file, 'a')
            self.__f.write(self.__str)
            self.__f.close()
        if self.__file_mode == 'current':
            self.__f = open(self.__file, 'w')
            self.__f.write(self.__str)
            self.__f.close()
        if self.__file_mode == 'timestamp':
            self.__f_time = open(self.__file_time, 'w')
            self.__f_time.write(self.__str)
            self.__f_time.close()
            self.__f = open(self.__file, 'w')
            self.__f.write(self.__str)
            self.__f.close()


    def __console_write(self, level, message, time):
        print(f'{time} | {message} | {self.__service} | {level}')

    def __slack_web_hook_write(self, level, message, time):
        slack_msg = {'timestamp': str(time),
                     'service': self.__service,
                     'level': level,
                     'message': str(message)}
        requests.post(self.__config['slack']['url'], data=json.dumps(slack_msg))

    def debug(self, message):
        time = datetime.datetime.now()
        if self.__console_log > 40:
            self.__console_write('DEBUG', message, time)
        if self.__database_log_mysql > 40:
            self.__db_write('DEBUG', message, time, db='mysql')
        if self.__database_log_postgres > 40:
            self.__db_write('DEBUG', message, time, db='postgres')
        if self.__file_log > 40:
            self.__file_write('DEBUG', message, time)
        if self.__slack_log > 40:
            self.__slack_web_hook_write('DEBUG', message, time)

    def info(self, message):
        time = datetime.datetime.now()
        if self.__console_log > 30:
            self.__console_write('INFO', message, time)
        if self.__database_log_mysql > 30:
            self.__db_write('INFO', message, time, db='mysql')
        if self.__database_log_postgres > 30:
            self.__db_write('INFO', message, time, db='postgres')
        if self.__file_log > 30:
            self.__file_write('INFO', message, time)
        if self.__slack_log > 30:
            self.__slack_web_hook_write('INFO', message, time)

    def warning(self, message):
        time = datetime.datetime.now()
        if self.__console_log > 20:
            self.__console_write('WARNING', message, time)
        if self.__database_log_mysql > 20:
            self.__db_write('WARNING', message, time, db='mysql')
        if self.__database_log_postgres > 20:
            self.__db_write('WARNING', message, time, db='postgres')
        if self.__file_log > 20:
            self.__file_write('WARNING', message, time)
        if self.__slack_log > 20:
            self.__slack_web_hook_write('WARNING', message, time)

    def error(self, message):
        time = datetime.datetime.now()
        if self.__console_log > 10:
            self.__console_write('ERROR', message, time)
        if self.__database_log_mysql > 10:
            self.__db_write('ERROR', message, time, db='mysql')
        if self.__database_log_postgres > 10:
            self.__db_write('ERROR', message, time, db='postgres')
        if self.__file_log > 10:
            self.__file_write('ERROR', message, time)
        if self.__slack_log > 10:
            self.__slack_web_hook_write('ERROR', message, time)

    def critical(self, message):
        time = datetime.datetime.now()
        if self.__console_log > 0:
            self.__console_write('CRITICAL', message, time)
        if self.__database_log_mysql > 0:
            self.__db_write('CRITICAL', message, time, db='mysql')
        if self.__database_log_postgres > 0:
            self.__db_write('CRITICAL', message, time, db='postgres')
        if self.__file_log > 0:
            self.__file_write('CRITICAL', message, time)
        if self.__slack_log > 0:
            self.__slack_web_hook_write('CRITICAL', message, time)