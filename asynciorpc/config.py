import yaml
from . import exceptions


CONFIG = {
    'company': None,
    'service': None,
    'rpc_port': 10080,
    'threadpool_size': 100,
    'processpool_size': 10
}

TIMEOUTS = dict()
INTERFACES = dict()

with open('config.yaml') as yaml_file:
    config = yaml.load(yaml_file.read())
    CONFIG.update(config)
    if not all(CONFIG.values()):
        raise exceptions.InvalidConfig('Invalid Config')