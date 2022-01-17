import json
import flask
from flask import Flask, abort, request, make_response, jsonify
from flask_httpauth import HTTPBasicAuth
import yaml

import cloudflare_tunnel

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
    tunnel = cloudflare_tunnel.create(auth.current_user())
    return {
        'result': 'ok',
        'tunnel': tunnel,
    }

@app.route("/tunnels")
@auth.login_required
def list():
    tunnels = cloudflare_tunnel.list(auth.current_user())
    return {
        'result': 'ok',
        'tunnels': tunnels,
    }

@app.route("/tunnels/<name>/credentials")
@auth.login_required
def credentials(name):
    _, credentials_file, _ = cloudflare_tunnel.files_for(auth.current_user(), name)
    return flask.send_file(credentials_file)

@app.route("/tunnels/<name>/config")
@auth.login_required
def config(name):
    _, _, config_file = cloudflare_tunnel.files_for(auth.current_user(), name)
    return flask.send_file(config_file)

@app.route("/tunnels/<name>", methods=['DELETE'])
@auth.login_required
def delete(name):
    ok = cloudflare_tunnel.delete(auth.current_user(), name)
    return {
        'result': 'ok' if ok else 'error',
        'name': name,
    }

@app.route("/tunnels/<name>/routes", methods=['POST'])
@auth.login_required
def create_route(name):
    service = request.args.get('service')
    if not service:
        abort(make_response(jsonify(message="Missing parameter: 'service'"), 400))
    tunnel = cloudflare_tunnel.create_route(auth.current_user(), name, service)
    return {
        'result': 'ok',
        'tunnel': tunnel,
    }

@app.route("/tunnels/<name>/routes", methods=['DELETE'])
@auth.login_required
def delete_routes(name):
    service = request.args.get('service')
    tunnel = cloudflare_tunnel.delete_routes(auth.current_user(), name, service)
    return {
        'result': 'ok',
        'tunnel': tunnel,
    }
