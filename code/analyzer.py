import os

import gzip
import json
import logging
from collections import namedtuple
from statistics import median
from string import Template


class LogAnalyzer:

    def __init__(self, config: dict, filedata: namedtuple):
        self.config = config
        self.filedata = filedata

    def run(self):
        try:
            if not self.report_exists():
                parsed_log = LogParser(filedata=self.filedata).parse_log_file()
                prepared = Calculate.prepare_data(parsed_log=parsed_log)
                sorted_urls = LogSorter(self.config).sort_and_slice(prepared)
                Report(self.config, self.filedata).create(log_data=sorted_urls)
                self.error_threshold(parsed_log=parsed_log)
        except KeyboardInterrupt:
            logging.exception('Нажатие CTRL-C')

    def report_exists(self) -> bool:
        report_name = '{}/report-{}.html'.format(
            self.config['REPORT_DIR'],
            self.filedata.date.replace('-', '.'))
        return os.path.exists(report_name)

    def error_threshold(self, parsed_log: dict):
        try:
            percent = round(parsed_log['lines_with_error'] / (
                    parsed_log['total_count'] / 100), 2)
        except ZeroDivisionError:
            percent = 0

        if percent > 0:
            try:
                err_perc = self.config['ERROR_THRESHOLD']
            except KeyError:
                err_perc = 100

            if percent > err_perc:
                logging.info('Превышен порог ошибок: {}%'.format(str(percent)))
            else:
                logging.info('Ошибок: {}%'.format(str(percent)))


class LogParser:
    collected = {}
    total_count = 0
    lines_with_error = 0
    request_time_total = 0

    def __init__(self, filedata: namedtuple):
        self.filedata = filedata

    def parse_log_file(self) -> dict:
        if self.filedata:
            open_file = gzip.open if self.filedata.ext == 'gz' else open
            with open_file(self.filedata.path, 'rt') as file_handler:
                for line in self.read_line(file_object=file_handler):
                    parsed_line = self.parse_line(line=line)
                    self.data_collector(line=parsed_line)
                    self.total_count += 1
        return {
            'collected': self.collected,
            'total_count': self.total_count,
            'request_time_total': self.request_time_total,
            'lines_with_error': self.lines_with_error,
        }

    def read_line(self, file_object):
        while True:
            data = file_object.readline()
            if not data:
                break
            yield data

    def parse_line(self, line: str) -> tuple:
        if 'GET' in line:
            split_one = line.split('GET ')
        elif 'POST' in line:
            split_one = line.split('POST ')
        elif 'HEAD' in line:
            split_one = line.split('HEAD ')
        elif 'PUT' in line:
            split_one = line.split('PUT ')
        else:
            split_one = ''

        if split_one:
            splitted = split_one[1].split()
            try:
                out = splitted[0].strip(), splitted[-1].strip()
            except IndexError:
                logging.info('Ошибка в строке лога')
                out = None
            return out

    def data_collector(self, line: tuple):
        if line:
            count = 1
            time_sum = 0
            request_time = ''

            all_request_time = list()
            try:
                request_time = float(line[1])
            except ValueError:
                logging.error(
                    'Ошибка получения request_time ({})'.format(line[0]))
                self.lines_with_error += 1

            if request_time:
                try:
                    dict_line = self.collected[line[0]]
                    count = dict_line['count'] + 1
                    time_sum = dict_line['time_sum']
                    time_max = dict_line['time_max']
                    all_request_time = dict_line['all_request_time']
                    if time_max < request_time:
                        time_max = request_time
                    all_request_time.append(request_time)
                except KeyError:
                    time_max = request_time
                    all_request_time.append(request_time)

                inside = {
                    'count': count,
                    'time_sum': request_time + time_sum,
                    'time_max': time_max,
                    'all_request_time': all_request_time
                }
                self.request_time_total += request_time
                self.collected[line[0]] = inside


class Calculate:
    @staticmethod
    def prepare_data(parsed_log: dict) -> dict:
        out = dict()
        for key, value in parsed_log['collected'].items():
            count = value['count']
            count_perc = round(count / (parsed_log['total_count'] / 100), 3)
            time_sum = round(value['time_sum'], 3)
            time_perc = round(
                time_sum / (parsed_log['request_time_total'] / 100), 3)
            time_avg = round(time_sum / count, 3)
            time_max = value['time_max']
            time_med = round(median(value['all_request_time']), 3)
            item = {
                'count': count,
                'count_perc': count_perc,
                'time_sum': time_sum,
                'time_perc': time_perc,
                'time_avg': time_avg,
                'time_max': time_max,
                'time_med': time_med,
            }
            out[key] = item

        return out


class LogSorter:
    def __init__(self, config: dict):
        self.config = config

    def sort_and_slice(self, prepared: dict) -> list:
        def localkey(k):
            return k[1]['time_sum']

        out = list()
        for item, val in sorted(prepared.items(), key=localkey, reverse=True):
            val['url'] = item
            out.append(val)
        return out[:self.config['REPORT_SIZE']]


class Report:
    def __init__(self, config: dict, filedata: namedtuple):
        self.config = config
        self.filedata = filedata

    def create(self, log_data: list):
        report = ''
        if log_data:
            with open('template/report.html', 'r') as template_handler:
                template = template_handler.read()
                s = Template(template)
                table_json = json.dumps(log_data)
                report = s.safe_substitute(table_json=table_json)
        if report:
            report_name = '{}/report-{}.html'.format(
                self.config['REPORT_DIR'],
                self.filedata.date.replace('-', '.'))
            with open(report_name, 'w') as report_handler:
                try:
                    report_handler.write(report)
                except OSError:
                    logging.exception('Нет места на диске')
