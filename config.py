from dataclasses import dataclass
from pathlib import Path
import yaml

@dataclass
class Config():
    account_id: str
    zone: str
    token: str
    kubeconfig: str
    namespace: str

def get_config():
    with open('secret/cloudflare.yaml') as f:
        return Config(**yaml.safe_load(f))

cfg = get_config()
