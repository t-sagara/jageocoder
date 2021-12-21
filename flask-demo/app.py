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
    inner_url_prefix = inner_url_prefix[:-1]


@app.route(inner_url_prefix + "/")
def index():
    query = request.args.get('q') or ''
    skip_aza = request.args.get('skip_aza') or 'auto'
    return render_template(
        'index.html',
        url_prefix=url_prefix,
        skip_aza=skip_aza,
        q=query, result=None)


@app.route(inner_url_prefix + "/search", methods=['POST', 'GET'])
def search():
    query = request.args.get('q')
    skip_aza = request.args.get('skip_aza') or 'auto'
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


@app.route(inner_url_prefix + "/node/<id>", methods=['POST', 'GET'])
def show_node(id):
    node = jageocoder.get_module_tree().get_node_by_id(id)
    query = request.args.get('q')
    skip_aza = request.args.get('skip_aza') or 'auto'

    return render_template(
        'node.html',
        url_prefix=url_prefix,
        skip_aza=skip_aza,
        q=query,
        node=node)
