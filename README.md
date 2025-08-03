# Jageocoder - A Python Japanese geocoder

日本語版は README_ja.md をお読みください。

This is a Python port of the Japanese-address geocoder `DAMS` used in CSIS at the University of Tokyo's ["Address Matching Service"](https://newspat.csis.u-tokyo.ac.jp/geocode/modules/addmatch/index.php?content_id=1) and [GSI Maps](https://maps.gsi.go.jp/).

# Getting Started

This package provides address-geocoding and reverse-geocoding functionality for Python programs. The basic usage is to specify a dictionary with `init()` then call `search()` to get geocoding results.

```python
>>> import jageocoder
>>> jageocoder.init(url='https://jageocoder.info-proto.com/jsonrpc')
>>> jageocoder.search('新宿区西新宿2-8-1')
{'matched': '新宿区西新宿2-8-', 'candidates': [{'id': 5961406, 'name': '8番', 'x': 139.691778, 'y': 35.689627, 'level': 7, 'note': None, 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番']}]}
```

# How to install

## Prerequisites

Requires Python 3.9 or later and 3.12 or earlier.

All other required packages will be installed automatically.

## Install instructions

- Install the package with `pip install jageocoder`

To use Jageocoder, you need to install the "Dictionary Database" on the same machine or connect to the RPC service provided by [jageocoder-server](https://t-sagara.github.io/jageocoder/server/) .

### Install Dictionary Database

When a dictionary database is installed, large amounts of data can be processed at high speed. A database covering addresses in Japan requires 25 GB or more of storage.

- Download an address database file compatible with that version from [here](https://www.info-proto.com/static/jageocoder/latest/v2/)

      jageocoder download-dictionary https://www.info-proto.com/static/jageocoder/latest/v2/jukyo_all_v21.zip 

- Install the dictionary with `install-dictionary` command

      jageocoder install-dictionary jukyo_all_v21.zip

If you need to know the location of the dictionary directory,
perform `get-db-dir` command as follows. (Or call
`jageocoder.get_db_dir()` in your script)

```bash
jageocoder get-db-dir
```

If you prefer to create the database in another location, set the environment variable `JAGEOCODER_DB2_DIR` before executing `install_dictionary()` to specify the directory.

```bash
export JAGEOCODER_DB2_DIR='/usr/local/share/jageocoder/db2'
install-dictionary <db-file>
```

### Connect to the Jageocoder server

Since dictionary databases are large in size, installing them on multiple machines consumes storage and requires time and effort to update them.
Instead of installing a dictionary database on each machine, you can connect to a Jageocoder server to perform the search process.

If you want to use a server, specify the server endpoint in the environment variable `JAGEOCODER_SERVER_URL`. For a public demonstration server, use the following

```bash
export JAGEOCODER_SERVER_URL=https://jageocoder.info-proto.com/jsonrpc
```

However, the server for public demonstrations cannot withstand the load when accesses are concentrated, so it is limited to one request per second.
If you want to process a large number of requests, please refer to [here](https://t-sagara.github.io/jageocoder/server/) to set up your own Jageocoder server. The endpoint is '/jsonrpc' on the server.

## Uninstall instructions

Remove the directory containing the database, or perform 
`uninstall-dictionary` command as follows.

```bash
jageocoder uninstall-dictionary
```

Then, uninstall the package with `pip` command.

```bash
pip uninstall jageocoder
```

# How to use

## Use from the command line

Jageocoder is intended to be embedded in applications as a library and used by calling the API, but a simple command line interface is also provided.

For example, to geocode an address, execute the following command.

```bash
jageocoder search 新宿区西新宿２－８－１
```

You can check the list of available commands with `--help`.

```bash
jageocoder --help
```

## Using API

First, import jageocoder and initialize it with `init()`.

```python
>>> import jageocoder
>>> jageocoder.init()
```

The parameter `db_dir` of `init()` can be used to specify the directory where the address database is installed. Alternatively, you can specify the endpoint URL of the Jageocoder server with `url`. If it is omitted, the value of the environment variable is used.

### Search for latitude and longitude by address

Use `search()` to search for the address you want to check the longitude and latitude of.

The `search()` function returns a dict with `matched` as
the matched string and `candidates` as the list of search results.
(The results are formatted for better viewing)

Each element of `candidates` contains the information of an address node (AddressNode).

```python
>>> jageocoder.search('新宿区西新宿２－８－１')
{
  'matched': '新宿区西新宿２－８－',
  'candidates': [{
    'id': 12299846, 'name': '8番',
    'x': 139.691778, 'y': 35.689627, 'level': 7, 'note': None,
    'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番']
  }]
}
```

The meaning of the items is as follows

- id: ID in the database
- name: Address notation
- x: longitude
- y: latitude
- level: Address level (1:Prefecture, 2:County, 3:City and 23 district,
    4:Ward, 5:Oaza, 6:Aza and Chome, 7:Block, 8:Building)
- note: Notes such as city codes
- fullname: List of address notations from the prefecture level to this node

### Search for addresses by longitude and latitude

You can specify the latitude and longitude of a point and look up the address of that point (so-called reverse geocoding).

When you pass the longitude and latitude of the point you wish to look up to `reverse()`, you can retrieve up to three address nodes surrounding the specified point.

```python
>>> import jageocoder
>>> jageocoder.init()
>>> triangle = jageocoder.reverse(139.6917, 35.6896, level=7)
>>> if len(triangle) > 0:
...     print(triangle[0]['candidate']['fullname'])
...
['東京都', '新宿区', '西新宿', '二丁目', '8番']
```

In the example above, the ``level`` optional parameter is set to 7 to search down to the block (街区・地番) level.

> [!NOTE]
>
> Indexes for reverse geocoding are automatically created the first time you perform reverse geocoding. Note that this process can take a long time.

### Explore the attribute information of an address

Use `searchNode()` to retrieve information about an address.

This function returns a list of type `jageocoder.result.Result` .
You can access the address node from node element of the Result object.

```python
>>> results = jageocoder.searchNode('新宿区西新宿２－８－１')
>>> len(results)
1
>>> results[0].matched
'新宿区西新宿２－８－'
>>> type(results[0].node)
<class 'jageocoder.node.AddressNode'>
>>> node = results[0].node
>>> node.get_fullname()
['東京都', '新宿区', '西新宿', '二丁目', '8番']
```

#### Get GeoJSON representation

You can use the `as_geojson()` method of the Result and AddressNode
objects to obtain the GeoJSON representation.

```python
>>> results[0].as_geojson()
{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [139.691778, 35.689627]}, 'properties': {'id': 12299851, 'name': '8番', 'level': 7, 'note': None, 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番'], 'matched': '新宿区西新宿２－８－'}}
>>> results[0].node.as_geojson()
{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [139.691778, 35.689627]}, 'properties': {'id': 12299851, 'name': '8番', 'level': 7, 'note': None, 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番']}}
```

#### Get the local government codes

There are two types of local government codes: JISX0402 (5-digit) and Local Government Code (6-digit).

You can also obtain the prefecture code JISX0401 (2 digits).

```python
>>> node.get_city_jiscode()  # 5-digit code
'13104'
>>> node.get_city_local_authority_code() # 6-digit code
'131041'
>>> node.get_pref_jiscode()  # prefecture code
'13'
```

#### Get link URLs to maps

Generate URLs to link to GSI and Google maps.

```python
>>> node.get_gsimap_link()
'https://maps.gsi.go.jp/#16/35.689627/139.691778/'
>>> node.get_googlemap_link()
'https://maps.google.com/maps?q=35.689627,139.691778&z=16'
```

#### Traverse the parent node

A "parent node" is a node that represents a level above the address.
Get the node by attribute `parent`.

Now the `node` points to '8番', so the parent node will be '二丁目'.

```python
>>> parent = node.parent
>>> parent.get_fullname()
['東京都', '新宿区', '西新宿', '二丁目']
>>> parent.x, parent.y
(139.691774, 35.68945)
```

#### Traverse the child nodes

A "child node" is a node that represents a level below the address.
Get the node by attribute `children`.

There is one parent node, but there are multiple child nodes.
The actual return is a SQL query object, but it can be looped through
with an iterator or cast to a list.

Now the `parent` points to '二丁目', so the child node will be
the block number (○番) contained therein.

```python
>>> parent.children
<sqlalchemy.orm.dynamic.AppenderQuery object at 0x7fbc08404b38>
>>> [child.name for child in parent.children]
['10番', '11番', '1番', '2番', '3番', '4番', '5番', '6番', '7番', '8番', '9番']
```

# For developers

## Documentation

Tutorials and references are [here](https://jageocoder.readthedocs.io/ja/latest/).

## Create your own dictionary

Consider using [jageocoder-converter](https://github.com/t-sagara/jageocoder-converter).

## Tests

Run `pytest` for unit tests, `pytest jageocoder/ --doctest-modules`
for testing sample codes in comments and
`pytest docs/source/ --doctest-glob=*.rst`
for testing codes in the online manual document.

## Contributing

Address notation varies. So suggestions for logic improvements are welcome.
Please submit an issue with examples of address notations in use and how they should be parsed.

## Authors

* **Takeshi SAGARA** - [Info-proto Co.,Ltd.](https://www.info-proto.com/)

## License

This project is licensed under [the MIT License](https://opensource.org/licenses/mit-license.php).

This is not the scope of the dictionary data license. Please follow the license of the respective dictionary data.

## Acknowledgements

We would like to thank CSIS for allowing us to provide address matching services on their institutional website for over 20 years.

We would also like to thank Professor Asanobu Kitamoto of NII for providing us with a large sample of areas using the older address system and for his many help in confirming the results of our analysis.
