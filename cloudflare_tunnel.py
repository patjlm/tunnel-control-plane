import json
import random
import shutil
import string
import subprocess
from pathlib import Path

import yaml

from config import cfg
from cloudflare import cloudflare_cli
from cloudflare_dns import Dns

import openshift

cert = Path(cfg.cert)

def tunnel_exists(name):
    p = subprocess.run([
        'cloudflared', 'tunnel',
        '--origincert', cert,
        'info', name,
    ])
    return p.returncode == 0

def random_name(len=8):
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(len))

def new_tunnel_name():
    while tunnel_exists(name := random_name()):
        pass
    return name

def files_for(user, name, create=False):
    dir = Path(f'db/{user}/{name}')
    if create:
        dir.mkdir(exist_ok=True, parents=True)
    return dir, dir / 'credentials.json', dir / 'config.yaml'

def load_config(user, name):
    _, _, config_file = files_for(user, name)
    if config_file.exists():
        with open(config_file) as f:
            return yaml.safe_load(f)
    return {}

def save_config(user, name, config):
    _, _, config_yaml = files_for(user, name)
    with open(config_yaml, 'w') as f:
        yaml.safe_dump(config, f)

def tunnel_info(user, name):
    config = load_config(user, name)
    return {'name': name, 'config': config}

def create(user: str) -> str:
    name = new_tunnel_name()
    _, credentials, _ = files_for(user, name, create=True)
    p = subprocess.run([
        'cloudflared', 'tunnel',
        '--origincert', cert,
        'create', '--credentials-file', credentials, name,
    ])
    if p.returncode > 0:
        raise Exception('Could not create tunnel', p.stdout, p.stderr)
    tunnel_id = json.load(open(credentials))['TunnelID']
    config = {
        'tunnel': tunnel_id,
        'ingress': [{'service': 'http_status:404'}]
    }
    save_config(user, name, config)
    return tunnel_info(user, name)

def list(user: str):
    userdir = Path(f'db/{user}')
    if not userdir.exists():
        return []
    return [tunnel_info(user, f.name) for f in userdir.glob('*')]

def delete(user: str, name: str):
    dir = Path(f'db/{user}/{name}')
    if not dir.exists():
        raise Exception(f'tunnel {name} configuration not found for user {user}')
    config = load_config(user, name)
    for service in set([i['service'] for i in config['ingress']
                    if 'hostname' in i]):
        delete_routes(user, name, service)
    p = subprocess.run([
        'cloudflared', 'tunnel',
        '--origincert', cert,
        'delete', name,
    ])
    if p.returncode == 0:
        shutil.rmtree(dir)
    return p.returncode == 0

def create_route(user: str, name: str, service: str):
    if not tunnel_info(user, name):
        return None
    dns = Dns()
    config = load_config(user, name)
    hostnames = [i['hostname'] for i in config['ingress'] if i.get('hostname')]
    while hostname := f'{random_name()}-{name}.{cfg.dns_suffix}':
        if hostname not in hostnames:
            break
    # dns.create_tunnel_cname(tunnel_id, hostname)
    p = subprocess.run([
        'cloudflared', 'tunnel',
        '--origincert', cert,
        'route', 'dns', name, hostname,
    ])
    config['ingress'] = [{'hostname': hostname, 'service': service}] + config['ingress']
    save_config(user, name, config)
    if service.startswith('tcp://'):
        openshift.setup_access(hostname.split('.')[0], hostname)
    return tunnel_info(user, name)

def hostnames_for_service(user, name, service):
    config = load_config(user, name)
    return [i['hostname'] for i in config['ingress']
            if i['service'] == service]

def zone_records():
    cli = cloudflare_cli()
    zones = cli.zones.get()
    zone = [z for z in zones if z['name'] == cfg.zone][0]
    zoneid = zone['id']
    return zoneid, cli.zones.dns_records.get(zoneid)

def delete_routes(user, name, service):
    dns = Dns()
    config = load_config(user, name)
    new_config = load_config(user, name)
    new_ingresses = []
    new_config['ingress'] = new_ingresses
    for ingress in config['ingress']:
        if ingress['service'] == service:
            hostname = ingress['hostname']
            if service.startswith('tcp://'):
                openshift.remove_access(hostname.split('.')[0])
            dns.delete(hostname)
        else:
            new_ingresses.append(ingress)
    save_config(user, name, new_config)
    return tunnel_info(user, name)
