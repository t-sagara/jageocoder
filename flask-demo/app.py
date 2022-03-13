import os
from flask import Flask, request, render_template, jsonify
from flask_cors import cross_origin

import jageocoder
from jageocoder.address import AddressLevel
jageocoder.init()

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

@app.route("/")
def index():
    query = request.args.get('q') or ''
    skip_aza = request.args.get('skip_aza') or 'auto'
    return render_template(
        'index.html',
        skip_aza=skip_aza,
        q=query, result=None)


@app.route("/webapi")
def webapi():
    return render_template('webapi.html')


@app.route("/search", methods=['POST', 'GET'])
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
        skip_aza=skip_aza,
        q=query, results=results)


@app.route("/node/<id>", methods=['POST', 'GET'])
def show_node(id):
    node = jageocoder.get_module_tree().get_node_by_id(id)
    query = request.args.get('q')
    skip_aza = request.args.get('skip_aza') or 'auto'

    return render_template(
        'node.html',
        skip_aza=skip_aza,
        q=query,
        node=node)


@app.route("/geocode", methods=['POST', 'GET'])
@cross_origin()
def geocode():
    if request.method == 'GET':
        query = request.args.get('addr')
        skip_aza = request.args.get('skip_aza') or 'auto'
    else:
        query = request.form.get('addr')
        skip_aza = request.form.get('skip_aza')

    if query:
        results = jageocoder.searchNode(
            query, best_only=True,
            aza_skip=skip_aza)
    else:
        return "'addr' is required.", 400

    return jsonify([x.to_dict() for x in results]), 200


@app.route("/rgeocode", methods=['POST', 'GET'])
@cross_origin()
def reverse_geocode():
    if request.method == 'GET':
        lat = request.args.get('lat')
        lon = request.args.get('lon')
        level = request.args.get('level', AddressLevel.AZA)
    else:
        lat = request.form.get('lat')
        lon = request.form.get('lon')
        level = request.form.get('level', AddressLevel.AZA)

    if lat and lon:
        results = jageocoder.reverse(
            x=float(lon),
            y=float(lat),
            level=int(level))
    else:
        return "'lat' and 'lon' are required.", 400

    return jsonify(results), 200
