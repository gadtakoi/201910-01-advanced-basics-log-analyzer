#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';
import argparse
import logging

from code.analyzer import LogAnalyzer
from code.config import LogAnalyzerConf
from code.last_log import LastLog

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.py', help='Config file')
    args = parser.parse_args()

    conf = LogAnalyzerConf().get_config(default_config=config,
                                        config_file=args.config)

    logging.basicConfig(filename=conf['ERROR_LOG'],
                        format='[%(asctime)s] %(levelname).1s %(message)s',
                        level=logging.DEBUG)
    lastlog = LastLog().get_last_log(config=conf)
    LogAnalyzer(config=conf, filedata=lastlog).run()


if __name__ == "__main__":
    main()
