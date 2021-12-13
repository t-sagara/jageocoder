import os
from flask import Flask, request, render_template

import jageocoder
jageocoder.init()

app = Flask(__name__)
url_prefix = os.environ.get('URL_PREFIX', '')
if url_prefix != "" and url_prefix[-1] == "/":
    url_prefix = url_prefix[:-1]


@app.route(url_prefix + "/")
def index():
    return render_template(
        'index.html',
        url_prefix=url_prefix,
        skip_aza=None,
        q='', result=None)


@app.route(url_prefix + "/search", methods=['POST', 'GET'])
def search():
    query = request.args.get('q')
    skip_aza = request.args.get('skip_aza')
    if query:
        results = jageocoder.searchNode(
            query, best_only=True,
            enable_aza_skip=skip_aza)
    else:
        results = None

    return render_template(
        'index.html',
        url_prefix=url_prefix,
        skip_aza=skip_aza,
        q=query, results=results)
