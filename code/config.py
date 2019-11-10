import os
from importlib import import_module


class LogAnalyzerConf:
    def get_config(self, default_config: dict, config_file: str) -> dict:
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
