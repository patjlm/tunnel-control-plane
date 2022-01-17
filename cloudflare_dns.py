from config import cfg
from cloudflare import cloudflare_cli

class Dns():
    def __init__(self) -> None:
        self.cli = cloudflare_cli()
        zones = self.cli.zones.get()
        self.zone = cfg.zone
        zone = [z for z in zones if z['name'] == self.zone][0]
        self.zoneid = zone['id']

    def records(self):
        return self.cli.zones.dns_records.get(self.zoneid)
    
    def create_cname(self, hostname, target):
        recordid = [r['id'] for r in self.records() if r['name'] == hostname]
        if len(recordid) == 0:
            data = {'name': hostname.removesuffix(f'.{cfg.zone}'),
                    'type': 'CNAME',
                    'content': target}
            self.cli.zones.dns_records.post(self.zoneid, data=data)

    def create_tunnel_cname(self, tunnel_id, hostname):
        # _, credentials, _ = files_for(user, name, create=True)
        # tunnel_id = json.load(open(credentials))['TunnelID']
        target = f'{tunnel_id}.cfargotunnel.com'
        return self.create_cname(hostname, target)

    def delete(self, hostname):
        recordid = [r['id'] for r in self.records() if r['name'] == hostname]
        if len(recordid) == 1:
            self.cli.zones.dns_records.delete(self.zoneid, recordid[0])
        else:
            print(f'DNS record not found for route hostname {hostname}. Skipping')
