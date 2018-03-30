from flask import Flask, send_from_directory, render_template


app = Flask(__name__)

app.secret_key = 'lol idk, something'
app.config['SESSION_TYPE'] = 'filesystem'


@app.route('/queue', methods=['GET'])
def queue_requested():
    return render_template('queue.html')


@app.route('/queue/<filename>', methods=['GET'])
def stylesheets(filename):
    return send_from_directory('static', filename)


if __name__ == '__main__':
    host = '0.0.0.0'
    port = 8080
    app.debug = False
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.run(host=host, port=port)
