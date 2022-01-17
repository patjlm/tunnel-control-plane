from dataclasses import dataclass
from pathlib import Path
import yaml

@dataclass
class Config():
    zone: str
    token: str
    cert: str
    dns_suffix: str
    kubeconfig: str
    namespace: str

def get_config():
    with open('secret/cloudflare.yaml') as f:
        return Config(**yaml.safe_load(f))

cfg = get_config()
