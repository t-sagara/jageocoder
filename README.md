# jageocoder - A Python Japanese geocoder

日本語版は README_ja.md をお読みください。

This is a Python port of the Japanese-address geocoder used in CSIS at the University of Tokyo's ["Address Matching Service"](https://newspat.csis.u-tokyo.ac.jp/geocode/modules/addmatch/index.php?content_id=1) and [GSI Maps](https://maps.gsi.go.jp/).

# Getting Started

This package provides address-geocoding functionality for Python programs. The basic usage is to specify a dictionary with `init()` then call `search()` to get geocoding results.

```python
python
>>> import jageocoder
>>> jageocoder.init()
>>> jageocoder.search('新宿区西新宿2-8-1')
{'matched': '新宿区西新宿2-8-', 'candidates': [{'id': 5961406, 'name': '8番', 'x': 139.691778, 'y': 35.689627, 'level': 7, 'note': None, 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番']}]}
```

# How to install

## Prerequisites

Requires Python 3.7.x or later.

All other required packages will be installed automatically.

## Install instructions

- Install the package with `pip install jageocoder`
- Download an address database file compatible with that version from 
  [here](https://www.info-proto.com/static/jageocoder/latest/v2/)
- Install the dictionary with `install-dictionary` command

```sh
pip install jageocoder
wget https://www.info-proto.com/static/jageocoder/latest/v2/jukyo_all_v20.zip
jageocoder install-dictionary jukyo_all_v20.zip
```

The dictionary database will be installed under
`{sys.prefix}/jageocoder/db2/` by default,
however if the user doesn't have write permission there,
`{site.USER_DATA}/jageocoder/db2/` instead.

If you need to know the location of the dictionary directory,
perform `get-db-dir` command as follows. (Or call
`jageocoder.get_db_dir()` in your script)

```sh
jageocoder get-db-dir
```

If you prefer to create it in another location, set the environment
variable `JAGEOCODER_DB2_DIR` before executing `install_dictionary()`
to specify the directory.

```sh
export JAGEOCODER_DB2_DIR='/usr/local/share/jageocoder/db2'
install-dictionary <db-file>
```

## Uninstall instructions

Remove the directory containing the database, or perform 
`uninstall-dictionary` command as follows.

```sh
jageocoder uninstall-dictionary
```

Then, uninstall the package with `pip` command.

```sh
pip uninstall jageocoder
```

# How to use

## Use from the command line

We assume that jageocoder will be embedded in applications
as a library and used by calling the API, but for testing purposes,
you can check the geocoding results with the following command.

```sh
jageocoder search 新宿区西新宿２－８－１
```

You can check the list of available commands with `--help`.

```sh
jageocoder --help
```

## Using API

First, import jageocoder and initialize it with `init()`.

```
>>> import jageocoder
>>> jageocoder.init()
```

### Search for latitude and longitude by address

Use `search()` to search for the address you want to check the longitude and latitude of.

The `search()` function returns a dict with `matched` as
the matched string and `candidates` as the list of search results.
(The results are formatted for better viewing)

Each element of `candidates` contains the information of an address node (AddressNode).

```
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

Note: This method is not available in v2 series.

### Explore the attribute information of an address

Use `searchNode()` to retrieve information about an address.

This function returns a list of type `jageocoder.result.Result` .
You can access the address node from node element of the Result object.

```
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

```
>>> results[0].as_geojson()
{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [139.691778, 35.689627]}, 'properties': {'id': 12299851, 'name': '8番', 'level': 7, 'note': None, 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番'], 'matched': '新宿区西新宿２－８－'}}
>>> results[0].node.as_geojson()
{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [139.691778, 35.689627]}, 'properties': {'id': 12299851, 'name': '8番', 'level': 7, 'note': None, 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番']}}
```

#### Get the local government codes

There are two types of local government codes: JISX0402 (5-digit) and
Local Government Code (6-digit).

You can also obtain the prefecture code JISX0401 (2 digits).

```
>>> node.get_city_jiscode()  # 5-digit code
'13104'
>>> node.get_city_local_authority_code() # 6-digit code
'131041'
>>> node.get_pref_jiscode()  # prefecture code
'13'
```

#### Get link URLs to maps

Generate URLs to link to GSI and Google maps.

```
>>> node.get_gsimap_link()
'https://maps.gsi.go.jp/#16/35.689627/139.691778/'
>>> node.get_googlemap_link()
'https://maps.google.com/maps?q=35.689627,139.691778&z=16'
```

#### Traverse the parent node

A "parent node" is a node that represents a level above the address.
Get the node by attribute `parent`.

Now the `node` points to '8番', so the parent node will be '二丁目'.

```
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

```
>>> parent.children
<sqlalchemy.orm.dynamic.AppenderQuery object at 0x7fbc08404b38>
>>> [child.name for child in parent.children]
['10番', '11番', '1番', '2番', '3番', '4番', '5番', '6番', '7番', '8番', '9番']
```

## Create your own dictionary

Consider using [jageocoder-converter](https://github.com/t-sagara/jageocoder-converter).

## ToDos

- Supporting address changes

    The functionality to handle address changes due to municipal consolidation, etc.
    has already been implemented in the C++ version, but will be implemented
    in this package in the future.

## Contributing

Address notation varies. So suggestions for logic improvements are welcome.
Please submit an issue with examples of address notations in use and how they should be parsed.

## Authors

* **Takeshi SAGARA** - [Info-proto Co.,Ltd.](https://www.info-proto.com/)

## License

This project is licensed under [the MIT License](https://opensource.org/licenses/mit-license.php).

This is not the scope of the dictionary data license. Please follow the license of the respective dictionary data.

## Acknowledgements

We would like to thank CSIS for allowing us to provide address matching services
on their institutional website for over 20 years.

We would also like to thank Professor Asanobu Kitamoto of NII for providing us
with a large sample of areas using the older address system and for his many help
in confirming the results of our analysis.
