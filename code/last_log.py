import logging
import re
import datetime
from collections import namedtuple
from os import walk


class LastLog:
    def get_last_log(self, config: dict) -> namedtuple:
        files = []
        log_dates = []
        log_files = {}
        for (dirpath, dirnames, filenames) in walk(config['LOG_DIR']):
            files.extend(filenames)

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

            FileData = namedtuple('FileData', 'path date ext')
            filedata = FileData(filepath, filedate, fileext)

            return filedata
