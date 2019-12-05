import hashlib
import os
import unittest
from collections import namedtuple

from code.analyzer import LogAnalyzer, LogParser
from log_analyzer import get_config
from log_analyzer import config


class TestStringMethods(unittest.TestCase):

    def test_get_config(self):
        config_file = 'config.py'
        conf = get_config(default_config=config,
                                            config_file=config_file)
        self.assertEqual(conf['REPORT_SIZE'], 1000)

    def test_parse_line(self):
        parse_line = '1.194.135.240 -  - [29/Jun/2017:03:51:06 +0300] "GET /api/v2/group/6867433/statistic/sites/?date_type=day&date_from=2017-06-29&date_to=2017-06-29 HTTP/1.1" 200 22 "-" "python-requests/2.13.0" "-" "1498697466-3979856266-4708-9753261" "8a7741a54297568b" 0.075'

        pl = LogParser(filedata='').parse_line(parse_line)
        self.assertEqual(pl[1], '0.075')

    def test_main_log_analyzer(self):
        local_config = config.copy()
        local_config["REPORT_DIR"] = "./tests/reports"

        la = LogAnalyzer(config=local_config, filedata='')
        FileData = namedtuple('FileData', 'path date ext')
        la.filedata = FileData(
            path='./log/nginx-access-ui.log-20170630.gz',
            date='2017-06-30',
            ext='gz')
        la.run()
        report_file = "{}/{}".format(local_config["REPORT_DIR"],
                                     'report-2017.06.30.html')
        report_hash = self.get_file_hash(filename=report_file)
        self.assertEqual(str(report_hash), '17e27d8c2ad8f7efe7704df182523ad1')

        try:
            os.remove(report_file)
        except FileNotFoundError:
            pass

    def get_file_hash(self, filename):

        hasher = hashlib.md5()
        with open(filename, 'rb') as afile:
            buf = afile.read()
            hasher.update(buf)
        return hasher.hexdigest()


if __name__ == '__main__':
    unittest.main()
