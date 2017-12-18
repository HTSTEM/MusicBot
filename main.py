import requests
import os
import json

from ruamel import yaml

from bottle import Bottle, run, template, static_file, request, redirect, abort, ServerAdapter
from requests_oauthlib import OAuth2Session

with open('./config/config.yml', 'r') as config_file:
    config = yaml.safe_load(config_file)

OAUTH2_CLIENT_ID = config['id']
OAUTH2_CLIENT_SECRET = config['secret']


REDIRECT = 'http://localhost:8080/queue/oauth2'

BASE_API_URL = 'https://discordapp.com/api'

if 'http://' in REDIRECT:
    secure = False
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'
else:
    secure = True

keys = {

}

# I'm using this for now, does bottle have sessions? I couldn't find it in the docs
sessions = {

}


class SSLWSGIRefServer(ServerAdapter):
    def run(self, handler):
        from wsgiref.simple_server import make_server, WSGIRequestHandler
        import ssl
        if self.quiet:
            class QuietHandler(WSGIRequestHandler):
                def log_request(*args, **kw): pass
            self.options['handler_class'] = QuietHandler
        srv = make_server(self.host, self.port, handler, **self.options)
        srv.socket = ssl.wrap_socket(
            srv.socket,
            certfile='fullchain.pem',
            keyfile='privkey.pem',
            server_side=True)
        srv.serve_forever()


app = Bottle()

def is_mod_on_htc(user_id):
    # This will tap into the aIO loop and query d.py
    return requests.get(f'http://localhost:8088/authorize/{user_id}').json()
    # return True


def make_session(token=None, state=None, scope=None):
    return OAuth2Session(
        client_id=OAUTH2_CLIENT_ID,
        token=token,
        state=state,
        scope=scope,
        redirect_uri=REDIRECT,
        auto_refresh_kwargs={
            'client_id': OAUTH2_CLIENT_ID,
            'client_secret': OAUTH2_CLIENT_SECRET,
        },
        auto_refresh_url=BASE_API_URL+'/oauth2/token'
        )


queue = [
    ('Song name'*10, 'jim'),
    ('Song nme', 'fred'),
    ('Sng name', 'jim2'*10),
    ('Son name', 'jim3'),
    ('Song nname', 'jim4'),
]*10


@app.get('/queue/oauth2')
def oauth2_complete():
    discord = make_session(state=sessions[request.remote_addr].get('oauth2_state'))
    token = discord.fetch_token(
        BASE_API_URL+'/oauth2/token',
        client_secret=OAUTH2_CLIENT_SECRET,
        authorization_response=request.url
    )
    sessions[request.remote_addr]['oauth2_token'] = token

    key = request.query['code']

    keys[request.remote_addr] = key

    redirect('../queue')


@app.get('/queue')
def queue_requested():
    if request.remote_addr not in keys:
        discord = make_session(scope='identify guilds')
        authorization_url, state = discord.authorization_url(
            BASE_API_URL+'/oauth2/authorize')
        sessions[request.remote_addr] = {}
        sessions[request.remote_addr]['oauth2_state'] = state
        redirect(authorization_url)
        return

    discord = make_session(token=sessions[request.remote_addr].get('oauth2_token'))
    user = discord.get(BASE_API_URL+'/users/@me').json()

    user_id = user['id']

    if not is_mod_on_htc(user_id):
        abort(403, 'You\'re not a moderator on HTC.')
        return

    key = keys[request.remote_addr]
    return template('queue', {'key': key})


@app.post('/queue')
def api_request():
    key = request.forms.get("key")
    resource = request.forms.get("resource")

    if key != keys.get(request.remote_addr):
        data = {
            'code': 4001,
            'msg': 'Not authenticated',
        }

        return json.dumps(data)

    if resource == 'FULL_QUEUE':
        data = {
            'code': 1000,
            'msg': 'Queue read successful',
            'd': {
                'queue_length': len(queue),
                'queue': queue
            }
        }

        return json.dumps(data)
    else:
        data = {
            'code': 4000,
            'msg': 'Unknown resource',
            'd': {
            }
        }

        return json.dumps(data)


@app.get('/<filename:re:.*\.css>')
def stylesheets(filename):
    return static_file(filename, root='static/')


if __name__ == '__main__':
    host = '127.0.0.1'
    port = 8080
    if secure:
        server = SSLWSGIRefServer(host="0.0.0.0", port=8080)
        run(app, host=host, port=port, server=server,
            debug=True, reloader=True)
    else:
        run(app, host=host, port=port, debug=True, reloader=True)
