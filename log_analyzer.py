#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';
import os
import re
import logging
import argparse
import datetime

from collections import namedtuple
from importlib import import_module

from code.analyzer import LogAnalyzer

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
}


def get_config(default_config: dict, config_file: str) -> dict:
    result_config = default_config
    module_name = os.path.splitext(config_file)[0]
    try:
        config = import_module(module_name)
        result_config = dict(default_config, **config.config)
    except ModuleNotFoundError:
        raise ModuleNotFoundError('Конфигурационный файл {} не найден: '
                                  ''.format(config_file))
    except NameError:
        raise AttributeError('Ошибка в конфигурационном '
                             'файле: {}'.format(config_file))
    except AttributeError:
        pass
    except SyntaxError:
        raise SyntaxError('Синтаксическая ошибка в конфигурационном '
                          'файле: {}'.format(config_file))

    if 'ERROR_LOG' not in result_config:
        result_config['ERROR_LOG'] = None

    return result_config


def get_last_log(config: dict) -> namedtuple:
    files = []
    log_dates = []
    log_files = {}
    FileData = namedtuple('FileData', 'path date ext')

    for filename in os.listdir(config['LOG_DIR']):
        files.append(filename)

    for file in files:
        log_date_str = re.match(
            r'^nginx-access-ui\.log-(?P<date>\d{8})(\.gz)?$', file)
        if log_date_str:
            try:
                log_date = datetime.datetime.strptime(
                    log_date_str.group('date'), "%Y%m%d").date()
                log_dates.append(log_date)
                log_files[str(log_date)] = file
            except ValueError:
                logging.info('Некорректная дата лог файла {}'.format(
                    log_date_str.group()))
                pass

    if log_dates:
        sorted_log_dates = sorted(log_dates)
        log_date = sorted_log_dates[-1]

        filedate = str(log_date)
        fileext = log_files[filedate].split('.')[-1]
        filepath = "{}/{}".format(config['LOG_DIR'], log_files[filedate])
        filedata = FileData(filepath, filedate, fileext)

        return filedata


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.py', help='Config file')
    args = parser.parse_args()

    conf = get_config(default_config=config, config_file=args.config)

    logging.basicConfig(filename=conf['ERROR_LOG'],
                        format='[%(asctime)s] %(levelname).1s %(message)s',
                        level=logging.DEBUG)
    lastlog = get_last_log(config=conf)
    if lastlog:
        LogAnalyzer(config=conf, filedata=lastlog).run()
    else:
        logging.info('Лог не найден')


if __name__ == "__main__":
    main()
