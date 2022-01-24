import json
import shutil
import flask
from flask import Flask, abort, request, make_response, jsonify
from flask_httpauth import HTTPBasicAuth

from CloudFlare.exceptions import CloudFlareAPIError

# from cloudflare import Tunnel, Dns
import cloudflare
from config import cfg
import db
import openshift

app = Flask(__name__)

auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    with open('secret/users.json') as f:
        users = json.load(f)
        if password == users.get(username, None):
            return username

@app.route("/")
def root():
    return "Welcome"

@app.route("/tunnels", methods=['POST'])
@auth.login_required
def create():
    user = auth.current_user()
    t = cloudflare.Tunnel(app.logger)
    name = t.new_name()
    t.create(name)
    db.save_creds(user, name, t.creds)
    db.save_config(user, name, t.default_config())
    return {
        'result': 'ok',
        'tunnel': db.tunnel_info(user, name),
    }

@app.route("/tunnels")
@auth.login_required
def list():
    tunnels = db.list(auth.current_user())
    return {
        'result': 'ok',
        'tunnels': tunnels,
    }

@app.route("/tunnels/<name>/credentials")
@auth.login_required
def credentials(name):
    credentials_file, _ = db.files_for(auth.current_user(), name)
    return flask.send_file(credentials_file)

@app.route("/tunnels/<name>/config")
@auth.login_required
def config(name):
    _, config_file = db.files_for(auth.current_user(), name)
    return flask.send_file(config_file)

@app.route("/tunnels/<name>", methods=['DELETE'])
@auth.login_required
def delete(name):
    user = auth.current_user()
    config = db.load_config(user, name)
    if not config:
        return {
            'result': 'error',
            'message': f'tunnel {name} configuration not found for user {user}'
        }
    for service in set([i['service'] for i in config['ingress']
                        if 'hostname' in i]):
        _delete_routes(user, name, service)
    for t in cloudflare.Tunnel(app.logger).list_by_name(name):
        try:
            t.delete()
        except CloudFlareAPIError as e:
            app.logger.warning(e)
            return {
                'result': 'error',
                'message': str(e)
            }
    shutil.rmtree(db.tunnel_dir(user, name))
    return {
        'result': 'ok',
        'name': name,
    }

@app.route("/tunnels/<name>/routes", methods=['POST'])
@auth.login_required
def create_route(name):
    user = auth.current_user()
    service = get_service_param(request)
    if not db.tunnel_info(user, name):
        return None
    dns = cloudflare.Dns(app.logger)
    config = db.load_config(user, name)
    hostname = db.new_hostname(config, name)
    dns.create_tunnel_cname(config['tunnel'], hostname)
    config['ingress'] = [{'hostname': hostname, 'service': service}] + config['ingress']
    db.save_config(user, name, config)
    if service.startswith('tcp://'):
        openshift.setup_access(hostname.split('.')[0], hostname)
    return {
        'result': 'ok',
        'tunnel': db.tunnel_info(user, name),
    }

@app.route("/tunnels/<name>/routes", methods=['DELETE'])
@auth.login_required
def delete_routes(name):
    user = auth.current_user()
    service = get_service_param(request)
    ok = _delete_routes(user, name, service)
    return {
        'result': 'ok' if ok else 'error',
        'tunnel': db.tunnel_info(user, name),
    }

def _delete_routes(user, name, service):
    dns = cloudflare.Dns(app.logger)
    config = db.load_config(user, name)
    new_config = db.load_config(user, name)
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
    db.save_config(user, name, new_config)
    return True

def get_service_param(request):
    service = request.args.get('service')
    if not service:
        abort(make_response(jsonify(message="Missing parameter: 'service'"), 400))
    return service


if __name__ == '__main__':
    app.run()
