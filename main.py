import os
import json

from ruamel import yaml

from bottle import Bottle, run, template, static_file, request, redirect
from requests_oauthlib import OAuth2Session

with open('./config/config.yml', 'r') as config_file:
    config = yaml.safe_load(config_file)

OAUTH2_CLIENT_ID = config['id']
OAUTH2_CLIENT_SECRET = config['secret']


REDIRECT = 'http://localhost:8080/queue/oauth2'
OAUTH2 = 'https://discordapp.com/api/oauth2/authorize?response_type=code&client_id=377169849744359424&scope=identify&state={state}&redirect_uri=' + REDIRECT

if 'http://' in REDIRECT:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'

keys = {

}

# I'm using this for now, does bottle have sessions? I couldn't find it in the docs
sessions = {
    
}


app = Bottle()


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
        auto_refresh_url='https://discordapp.com/api/oauth2/token'
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
        'https://discordapp.com/api/oauth2/token',
        client_secret=OAUTH2_CLIENT_SECRET,
        authorization_response=request.url
    )
    sessions[request.remote_addr]['oauth2_token'] = token

    key = request.query['code']

    keys[request.remote_addr] = key

    print(keys)

    redirect('../queue')

@app.get('/queue')
def queue_requested():
    if request.remote_addr not in keys:
        discord = make_session(scope='identify guilds')
        authorization_url, state = discord.authorization_url(
            'https://discordapp.com/api/oauth2/authorize')
        sessions[request.remote_addr] = {}
        sessions[request.remote_addr]['oauth2_state'] = state
        redirect(authorization_url)
        return

    discord = make_session(token=sessions[request.remote_addr].get('oauth2_token'))
    user = discord.get('https://discordapp.com/api/users/@me').json()
    guilds = discord.get('https://discordapp.com/api/users/@me/guilds').json()
    print(user)
    print(guilds)

    key = keys[request.remote_addr]
    return template('queue', {'key': key})

@app.post('/queue')
def api_request():
    key = request.forms.get("key")
    resource = request.forms.get("resource")

    if resource == 'FULL_QUEUE':
        data = {
            'code': 1000,
            'msg': 'Queue read succesful',
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

    return template('queue')

@app.get('/<filename:re:.*\.css>')
def stylesheets(filename):
    return static_file(filename, root='static/')


if __name__ == '__main__':
    run(app, host='127.0.0.1', port=8080, debug=True, reloader=True)
