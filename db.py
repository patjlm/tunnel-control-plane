import json
import yaml
from pathlib import Path

import cloudflare
from config import cfg

def tunnel_dir(user, name):
    return Path(f'db/{user}/{name}')

def files_for(user, name, create=False):
    dir = tunnel_dir(user, name)
    if create:
        dir.mkdir(exist_ok=True, parents=True)
    return dir / 'credentials.json', dir / 'config.yaml'

def load_config(user, name):
    _, config_file = files_for(user, name)
    if config_file.exists():
        with open(config_file) as f:
            return yaml.safe_load(f)
    return {}

def save_creds(user, name, creds):
    credentials, _ = files_for(user, name, create=True)
    with open(credentials, 'w') as f:
        json.dump(creds, f)

def save_config(user, name, config):
    _, config_yaml = files_for(user, name)
    with open(config_yaml, 'w') as f:
        yaml.safe_dump(config, f)

def tunnel_info(user, name):
    config = load_config(user, name)
    if not config:
        return {}
    return {'name': name, 'config': config}

def list(user: str):
    userdir = Path(f'db/{user}')
    if not userdir.exists():
        return []
    return [tunnel_info(user, f.name) for f in userdir.glob('*')]

def new_hostname(config, name):
    hostnames = [i['hostname'] for i in config['ingress'] if i.get('hostname')]
    while True:
        hostname = f'{cloudflare.random_name()}-{name}.{cfg.zone}'
        if hostname not in hostnames:
            return hostname
