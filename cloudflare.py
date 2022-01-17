from pathlib import Path
import CloudFlare

from config import cfg

token = cfg.token

def cloudflare_cli():
    return CloudFlare.CloudFlare(token=token)
