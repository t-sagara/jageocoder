import os
from flask import Flask, request, render_template

import jageocoder
jageocoder.init()

app = Flask(__name__)
url_prefix = os.environ.get('URL_PREFIX', '')
inner_url_prefix = os.environ.get('INNER_URL_PREFIX', '')
if url_prefix != "" and url_prefix[-1] == "/":
    url_prefix = url_prefix[:-1]
if inner_url_prefix != "" and inner_url_prefix[-1] == "/":
    inner_url_prefix = inner_prefix[:-1]


@app.route(inner_url_prefix + "/")
def index():
    return render_template(
        'index.html',
        url_prefix=url_prefix,
        skip_aza='auto',
        q='', result=None)


@app.route(inner_url_prefix + "/search", methods=['POST', 'GET'])
def search():
    query = request.args.get('q')
    skip_aza = request.args.get('skip_aza')
    if query:
        results = jageocoder.searchNode(
            query, best_only=True,
            aza_skip=skip_aza)
    else:
        results = None

    return render_template(
        'index.html',
        url_prefix=url_prefix,
        skip_aza=skip_aza,
        q=query, results=results)
