import requests
import os
import json

from ruamel import yaml

from flask import Flask, session, request, redirect, abort, send_from_directory, render_template
from requests_oauthlib import OAuth2Session


with open('../config/config.yml', 'r') as config_file:
    with open(yaml.safe_load(config_file)['creds_file'], 'r') as creds_file:
        config = yaml.safe_load(creds_file)

OAUTH2_CLIENT_ID = config['client_id']
OAUTH2_CLIENT_SECRET = config['client_secret']


REDIRECT = 'http://localhost:8080/queue/oauth2'

BASE_API_URL = 'https://discordapp.com/api'

if 'http://' in REDIRECT:
    secure = False
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'
else:
    secure = True

app = Flask(__name__)

app.secret_key = 'lol idk, something'
app.config['SESSION_TYPE'] = 'filesystem'


def is_mod_on_htc(guild_id, user_id):
    # This will tap into the aIO loop and query d.py
    return requests.get(f'http://localhost:8088/authorize/{guild_id}/{user_id}').json()


def make_session(token=None, state=None, scope=None):
    def token_updater(t):
        session['oauth2_token'] = t

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
        auto_refresh_url=BASE_API_URL+'/oauth2/token',
        token_updater=token_updater
    )


@app.route('/queue/oauth2', methods=['GET'])
def oauth2_complete():
    discord = make_session(state=session.get('oauth2_state'))
    session['oauth2_token'] = discord.fetch_token(
        BASE_API_URL+'/oauth2/token',
        client_secret=OAUTH2_CLIENT_SECRET,
        authorization_response=request.url
    )
    session['key'] = request.args.get('code')
    return redirect('../queue?g={}'.format(session.get('guild')))


@app.route('/queue', methods=['GET'])
def queue_requested():
    print(request.args.get('g'))
    session['guild'] = request.args.get('g')
    if 'key' not in session:
        discord = make_session(scope='identify')
        authorization_url, state = discord.authorization_url(
            BASE_API_URL+'/oauth2/authorize')
        session['oauth2_state'] = state
        return redirect(authorization_url)

    discord = make_session(token=session.get('oauth2_token'))
    user = discord.get(BASE_API_URL+'/users/@me').json()
    user_id = user['id']
    guild = request.args.get('g')
    key = session.get('key')
    return render_template('queue.html', key=key, mod=str(is_mod_on_htc(guild, user_id)).lower())


@app.route('/queue', methods=['DELETE'])
def delete():
    key = request.form.get('key')
    if key != session.get('key'):
        data = {
            'code': 4001,
            'msg': 'Not authenticated',
        }

        return json.dumps(data)
    guild_id = request.form.get('guild')
    # we should probably use ids rather than position in case of a desync
    player_id = request.form.get('position')
    discord = make_session(token=session.get('oauth2_token'))
    user = discord.get(BASE_API_URL + '/users/@me').json()
    user_id = user['id']
    if not is_mod_on_htc(guild_id, user_id):
        return abort(403, 'You do not have sufficient permissions.')

    requests.delete(f'http://localhost:8088/{guild_id}', data={'position': player_id})
    queue = requests.get(f'http://localhost:8088/{guild_id}/playlist').json()
    queue = [(player['title'], player['user']) for player in queue]
    data = {
        'code': 1000,
        'msg': 'Queue read successful',
        'd': {
            'queue_length': len(queue),
            'queue': queue
        }
    }
    return json.dumps(data)

@app.route('/queue', methods=['POST'])
def api_request():
    guild = request.form.get('guild')
    key = request.form.get('key')
    resource = request.form.get('resource')
    '''
    discord = make_session(token=session.get('oauth2_token'))
    user = discord.get(BASE_API_URL + '/users/@me').json()
    user_id = user['id']
    if not is_mod_on_htc(guild, user_id):
        return abort(403, 'You do not have sufficient permissions.')
    '''
    if key != session.get('key'):
        data = {
            'code': 4001,
            'msg': 'Not authenticated',
        }

        return json.dumps(data)

    if resource == 'FULL_QUEUE':
        queue = requests.get(f'http://localhost:8088/{guild}/playlist').json()
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
            'd': {resource}
        }

        return json.dumps(data)


@app.route('/queue/<filename>', methods=['GET'])
def stylesheets(filename):
    return send_from_directory('static', filename)


if __name__ == '__main__':
    host = '0.0.0.0'
    port = 8080
    app.debug = True
    app.run(host=host, port=port)
