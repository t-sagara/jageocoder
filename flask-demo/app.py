import json
from typing import List
import re

from flask_cors import cross_origin
from flask import Flask, request, render_template, jsonify

import jageocoder

jageocoder.init()
module_version = jageocoder.__version__
dictionary_version = jageocoder.installed_dictionary_version()

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False


re_splitter = re.compile(r'[ \u2000,、]+')


@app.context_processor
def inject_versions():
    return {
        "module_version": module_version,
        "dictionary_version": dictionary_version,
    }


def _split_args(val: str) -> List[str]:
    args = re_splitter.split(val)
    args = [x for x in args if x != '']
    return args


@app.route("/")
def index():
    query = request.args.get('q', '')
    skip_aza = request.args.get('skip_aza', 'auto')
    area = request.args.get('area', '')
    return render_template(
        'index.html',
        skip_aza=skip_aza,
        area=area,
        q=query,
        result=None)


@app.route("/azamaster/<code>", methods=['POST', 'GET'])
def get_aza(code):
    tree = jageocoder.get_module_tree()
    aza_node = tree.aza_masters.search_by_code(code)

    if aza_node:
        names = json.loads(aza_node.names)
    else:
        names = None

    return render_template(
        'aza.html',
        tree=tree,
        aza=aza_node, names=names)


@app.route("/aza/<aza_id>", methods=['POST', 'GET'])
def search_aza_id(aza_id):
    tree = jageocoder.get_module_tree()
    if len(aza_id) == 12:
        # jisx0402(5digits) + aza_id(7digits)
        candidates = tree.search_nodes_by_codes(
            category="aza_id",
            value=aza_id[-7:])
        nodes = [x for x in candidates if x.get_city_jiscode() == aza_id[0:5]]
    elif len(aza_id) == 13:
        # lasdec(6digits) + aza_id(7digits)
        candidates = tree.search_nodes_by_codes(
            category="aza_id",
            value=aza_id[-7:])
        nodes = [x for x in candidates
                 if x.get_city_local_authority_code() == aza_id[0:6]]
    else:
        nodes = tree.search_nodes_by_codes(
            category="aza_id",
            value=aza_id)

    if len(nodes) == 1:
        return render_template(
            'node.html',
            tree=tree,
            node=nodes[0])

    return render_template(
        'node_list.html',
        tree=tree,
        nodes=nodes)


@app.route("/jisx0401/<code>", methods=['POST', 'GET'])
def search_jisx0401(code):
    tree = jageocoder.get_module_tree()
    nodes = tree.search_nodes_by_codes(
        category="jisx0401",
        value=code[0:2])

    if len(nodes) == 1:
        return render_template(
            'node.html',
            tree=tree,
            node=nodes[0])

    return render_template(
        'node_list.html',
        tree=tree,
        nodes=nodes)


@app.route("/jisx0402/<code>", methods=['POST', 'GET'])
def search_jisx0402(code):
    tree = jageocoder.get_module_tree()
    nodes = tree.search_nodes_by_codes(
        category="jisx0402",
        value=code[0:5])

    if len(nodes) == 1:
        return render_template(
            'node.html',
            tree=tree,
            node=nodes[0])

    return render_template(
        'node_list.html',
        tree=tree,
        nodes=nodes)


@app.route("/postcode/<code>", methods=['POST', 'GET'])
def search_postcode(code):
    tree = jageocoder.get_module_tree()
    nodes = tree.search_nodes_by_codes(
        category="postcode",
        value=code[0:7])

    if len(nodes) == 1:
        return render_template(
            'node.html',
            tree=tree,
            node=nodes[0])

    return render_template(
        'node_list.html',
        tree=tree,
        nodes=nodes)


@app.route("/license")
def license():
    dictionary_readme = jageocoder.installed_dictionary_readme()
    return render_template(
        'license.html',
        readme=dictionary_readme)


@app.route("/webapi")
def webapi():
    return render_template('webapi.html')


@app.route("/search", methods=['POST', 'GET'])
def search():
    query = request.args.get('q')
    area = request.args.get('area', '')
    skip_aza = request.args.get('skip_aza', 'auto')
    if query:
        jageocoder.set_search_config(
            best_only=True,
            aza_skip=skip_aza,
            target_area=_split_args(area))
        results = jageocoder.searchNode(query=query)
    else:
        results = None

    return render_template(
        'index.html',
        skip_aza=skip_aza,
        area=area,
        q=query, results=results)


@app.route("/node/<id>", methods=['POST', 'GET'])
def show_node(id):
    tree = jageocoder.get_module_tree()
    node = tree.get_node_by_id(int(id))
    query = request.args.get('q', '')
    area = request.args.get('area', '')
    skip_aza = request.args.get('skip_aza', 'auto')

    return render_template(
        'node.html',
        skip_aza=skip_aza,
        area=area,
        q=query,
        tree=tree,
        node=node)


@app.route("/geocode", methods=['POST', 'GET'])
@cross_origin()
def geocode():
    if request.method == 'GET':
        query = request.args.get('addr', '')
        area = request.args.get('area', '')
        skip_aza = request.args.get('skip_aza', 'auto')
    else:
        query = request.form.get('addr', '')
        area = request.form.get('area', '')
        skip_aza = request.form.get('skip_aza', 'auto')

    if query:
        jageocoder.set_search_config(
            best_only=True,
            target_area=_split_args(area),
            aza_skip=skip_aza)
        results = jageocoder.searchNode(
            query=query)
    else:
        return "'addr' is required.", 400

    return jsonify([x.as_dict() for x in results]), 200


"""
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
"""
