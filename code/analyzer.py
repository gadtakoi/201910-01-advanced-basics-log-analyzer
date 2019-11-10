import gzip
import json
import logging
import os
from statistics import median
from string import Template


class LogAnalyzer:
    collected = {}
    total_count = 0
    request_time_total = 0
    lines_with_error = 0

    def __init__(self, config: dict, filedata: str):
        self.config = config
        self.filedata = filedata

    def run(self):
        try:
            if not self.report_exists():
                self.parse_log_file()
                prepared = self.prepare_data()
                sorted_urls = self.sort_and_slice(prepared=prepared)
                self.create_report(log_data=sorted_urls)
                self.error_threshold()
        except KeyboardInterrupt:
            logging.exception('Нажатие CTRL-C')

    def report_exists(self) -> bool:
        out = False
        report_name = '{}/report-{}.html'.format(
            self.config['REPORT_DIR'],
            self.filedata.date.replace('-', '.'))
        if os.path.exists(report_name):
            out = True
        return out

    def parse_log_file(self):
        if self.filedata:
            if self.filedata.ext == 'gz':
                open_file = gzip.open(self.filedata.path, 'rt')
            else:
                open_file = open(self.filedata.path)

            with open_file as file_handler:
                for line in self.read_line(file_object=file_handler):
                    parsed_line = self.parse_line(line=line)
                    self.data_collector(line=parsed_line)
                    self.total_count += 1

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

    def prepare_data(self) -> dict:
        out = dict()
        for key, value in self.collected.items():
            count = value['count']
            count_perc = round(count / (self.total_count / 100), 3)
            time_sum = round(value['time_sum'], 3)
            time_perc = round(time_sum / (self.request_time_total / 100), 3)
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

        self.collected = dict()

        return out

    def sort_and_slice(self, prepared: dict) -> list:
        def localkey(k):
            return k[1]['time_sum']

        out = list()
        for item, value in sorted(prepared.items(),
                                  key=localkey,
                                  reverse=True):
            value['url'] = item
            out.append(value)
        return out[:self.config['REPORT_SIZE']]

    def create_report(self, log_data: list):
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

    def error_threshold(self):
        try:
            perc = round(self.lines_with_error / (self.total_count / 100), 2)
        except ZeroDivisionError:
            perc = 0

        if perc > 0:
            try:
                err_perc = self.config['ERROR_THRESHOLD']
            except KeyError:
                err_perc = 100

            if perc > err_perc:
                logging.info('Превышен порог ошибок: {}%'.format(str(perc)))
            else:
                logging.info('Ошибок: {}%'.format(str(perc)))
