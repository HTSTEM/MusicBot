import json

from bottle import Bottle, run, template, static_file, request, redirect


REDIRECT = 'http%3A%2F%2F127.0.0.1%3A8080%2Fqueue%2Foauth2'
OAUTH2 = 'https://discordapp.com/api/oauth2/authorize?response_type=code&client_id=377169849744359424&scope=identify&state={state}&redirect_uri=' + REDIRECT

keys = {

}


app = Bottle()

queue = [
    ('Song name'*10, 'jim'),
    ('Song nme', 'fred'),
    ('Sng name', 'jim2'*10),
    ('Son name', 'jim3'),
    ('Song nname', 'jim4'),
]*10

@app.get('/queue/oauth2')
def oauth2_complete():
    key = request.query['code']

    keys[request.remote_addr] = key

    print(keys)

    redirect('../queue')

@app.get('/queue')
def queue_requested():
    if request.remote_addr not in keys:
        redirect(OAUTH2.format(state='15773059ghq9183habn'))
        return

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
    run(app, host='0.0.0.0', port=8080, debug=True, reloader=True)
