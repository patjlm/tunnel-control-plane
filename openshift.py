import subprocess
from pathlib import Path
from config import cfg

from app import app

kubeconfig = cfg.kubeconfig

deployment = Path('deployment.yaml')

def setup_access(route_id, hostname):
    app.logger.info(f'creating openshift tunnel-access resources for route_id {route_id} towards {hostname}')
    manifest = subprocess.getoutput(
        f'oc --kubeconfig {kubeconfig} '
        f'process --local -f {deployment} '
        f'ROUTE_ID={route_id} ROUTE_HOSTNAME={hostname}')
    p = subprocess.run((
        f'oc --kubeconfig {kubeconfig} apply -n {cfg.namespace} -f -').split(),
        input=manifest, encoding='UTF-8',
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    if p.returncode > 0:
        app.logger.error(p.stdout)
    return p.returncode == 0

def remove_access(route_id):
    app.logger.info(f'removing openshift tunnel-access resources for route_id {route_id}')
    p = subprocess.run((
        f'oc --kubeconfig {kubeconfig} '
        f'delete -n {cfg.namespace} deployment,service '
        f'-l deployment=tunnel-access-{route_id}').split(),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    if p.returncode > 0:
        app.logger.error(p.stdout)
    return p.returncode == 0
