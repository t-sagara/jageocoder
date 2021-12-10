from flask import Flask, request, render_template

import jageocoder
jageocoder.init()

app = Flask(__name__)


@app.route("/")
def index():
    return render_template('index.html', q='', result=None)


@app.route("/search", methods=['POST', 'GET'])
def search():
    query = request.args.get('q') or None
    if query:
        results = jageocoder.searchNode(query, best_only=True)
    else:
        results = None

    return render_template('index.html', q=query, results=results)
