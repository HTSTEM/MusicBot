from bottle import Bottle, run, template, static_file

app = Bottle()

@app.route('/queue')
def index():
    return template('queue')

@app.get('/<filename:re:.*\.css>')
def stylesheets(filename):
    return static_file(filename, root='static/')

if __name__ == '__main__':
    run(app, host='localhost', port=8080, debug=True, reloader=True)
