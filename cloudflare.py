import base64
import random
import CloudFlare
from markupsafe import string

from config import cfg

token = cfg.token

def cloudflare_cli():
    return CloudFlare.CloudFlare(token=token)

class Tunnel():

    # def __init__(self, TunnelName: str = None, TunnelID: str = None,
    #                    TunnelSecret: str = None, AccountTag: str = None) -> None:
    #     self.id = TunnelID
    #     self.name = TunnelName
    #     self.secret_b64 = TunnelSecret
    #     self.account_tag = AccountTag
    def __init__(self, logger) -> None:
        self.logger = logger
        self.cli = cloudflare_cli()
        self.tunnels = self.cli.accounts.tunnels

    def _from_dict(self, d):
        self.id = d.get('id')
        self.name = d.get('name')
        self.account_tag = d.get('account_tag')
        return self

    # https://api.cloudflare.com/#argo-tunnel-create-argo-tunnel
    def create(self, name: str):
        key = bytes(''.join(random.choice(string.ascii_lowercase + string.ascii_uppercase) for _ in range(32)), 'utf-8')
        b64 = base64.b64encode(key).decode('utf-8')
        self.logger.info(f'creating cloudflare tunnel {name}')
        r = self.tunnels.post(cfg.account_id,
                              data={'name': name, 'tunnel_secret': b64})
        self._from_dict(r)
        self.creds = r.get('credentials_file', {})
        self.secret_b64 = self.creds.get('TunnelSecret')
        return self
    
    # https://api.cloudflare.com/#argo-tunnel-list-argo-tunnels
    def list(self):
        self.logger.info(f'listing cloudflare tunnels')
        r = self.tunnels.get(cfg.account_id)
        return [Tunnel(self.logger)._from_dict(t) for t in r]

    # https://api.cloudflare.com/#argo-tunnel-list-argo-tunnels
    def list_by_name(self, name: str):
        self.logger.info(f'creating cloudflare tunnels by name {name}')
        r = self.tunnels.get(cfg.account_id, params={'name': name})
        return [Tunnel(self.logger)._from_dict(t) for t in r]

    # # https://api.cloudflare.com/#argo-tunnel-get-argo-tunnel
    # def by_id(self, id: str) -> str:
    #     r = self.tunnels.get(cfg.account_id, id)
    #     return self._from_dict(r)

    def exists(self, name: str) -> bool:
        return len(self.list_by_name(name)) > 0

    # https://api.cloudflare.com/#argo-tunnel-delete-argo-tunnel
    def delete(self):
        self.logger.info(f'deleting cloudflare tunnel {self.name}/{self.id}')
        r = self.tunnels.delete(cfg.account_id, self.id)
        return self

    def default_config(self):
        return {
            'tunnel': self.id,
            'ingress': [{'service': 'http_status:404'}]
        }

    def new_name(self):
        while True:
            name = random_name(8)
            if not self.exists(name):
                return name
    

class Dns():
    def __init__(self, logger) -> None:
        self.logger = logger
        self.cli = cloudflare_cli()
        zones = self.cli.zones.get()
        self.zone = cfg.zone
        zone = [z for z in zones if z['name'] == self.zone][0]
        self.zoneid = zone['id']

    def records(self):
        return self.cli.zones.dns_records.get(self.zoneid)
    
    def create_cname(self, hostname, target, proxied=False):
        recordid = [r['id'] for r in self.records() if r['name'] == hostname]
        if len(recordid) == 0:
            data = {'name': hostname.removesuffix(f'.{cfg.zone}'),
                    'type': 'CNAME',
                    'content': target,
                    'proxied': proxied}
            self.logger.info(f'creating cloudflare DNS CNAME record {hostname} towards {target} (proxied={proxied})')
            self.cli.zones.dns_records.post(self.zoneid, data=data)

    def create_tunnel_cname(self, tunnel_id, hostname):
        target = f'{tunnel_id}.cfargotunnel.com'
        return self.create_cname(hostname, target, proxied=True)

    def delete(self, hostname):
        recordid = [r['id'] for r in self.records() if r['name'] == hostname]
        if len(recordid) == 1:
            self.logger.info(f'deleting cloudflare DNS record {hostname} (id={recordid[0]})')
            self.cli.zones.dns_records.delete(self.zoneid, recordid[0])
        else:
            print(f'DNS record not found for route hostname {hostname}. Skipping')


def random_name(len=8):
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(len))
