import subprocess
from pathlib import Path
from config import cfg

kubeconfig = cfg.kubeconfig

deployment = Path('deployment.yaml')

def setup_access(route_id, hostname):
    print(f'creating openshift access point towards {hostname}')
    manifest = subprocess.getoutput(
        f'oc --kubeconfig {kubeconfig} '
        f'process --local -f {deployment} '
        f'ROUTE_ID={route_id} ROUTE_HOSTNAME={hostname}')
    p = subprocess.run((
        f'oc --kubeconfig {kubeconfig} apply -n {cfg.namespace} -f -').split(),
        input=manifest, encoding='UTF-8'
    )
    return p.returncode == 0

def remove_access(route_id):
    p = subprocess.run((
        f'oc --kubeconfig {kubeconfig} '
        f'delete -n {cfg.namespace} deployment,service '
        f'-l deployment=tunnel-access-{route_id}').split()
    )
    return p.returncode == 0
