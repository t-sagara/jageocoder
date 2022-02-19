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

Requires Python 3.6.x or later.

The following packages will be installed automatically.

- [marisa-trie](https://pypi.org/project/marisa-trie/)
    for building and retrieving TRIE index
- [SQLAlchemy](https://pypi.org/project/SQLAlchemy/)
    for abstracting access to the RDBMS

## Install instructions

- Install the package with `pip install jageocoder`
- Install the dictionary with `install-dictionary` command

```sh
pip install jageocoder
python -m jageocoder install-dictionary
```

The dictionary database will be created under
`{sys.prefix}/jageocoder/db/`, or if the user doesn't have 
write permission there `{site.USER_DATA}/jageocoder/db/`
by default.

If you need to know the location of the directory containing
the dictionary database, perform `get-db-dir` command as follows,
or call `jageocoder.get_db_dir()` in your script.

```sh
python -m jageocoder get-db-dir
```

If you prefer to create it in another location, set the environment
variable `JAGEOCODER_DB_DIR` before executing `install_dictionary()`
to specify the directory.

```sh
export JAGEOCODER_DB_DIR='/usr/local/share/jageocoder/db'
python -m jageocoder install-dictionary
```

## Update dictinary

The `install-dictionary` command will download and install
a version of the address dictionary file that is compatible with
the currently installed jageocoder package.

If you upgrade the jageocoder package after installing
the address dictionary file, it may no longer be compatible with
the installed address dictionary file.
In which case you will need to reinstall or update the dictionary.

To update the dictionary, run the `upgrade-dictionary` command.
This process may take a long time.

```sh
python -m jageocoder upgrade-dictionary
```

## Uninstall instructions

Remove the directory containing the database, or perform 
`uninstall-dictionary` command as follows.

```sh
python -m jageocoder uninstall-dictionary
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
python -m jageocoder search 新宿区西新宿２－８－１
```

If you want to look up an address from longitude and latitude,
specify `reverse` instead of `search`.

```sh
python -m jageocoder reverse 139.6917 35.6896
```

You can check the list of available commands with `--help`.

```sh
python -m jageocoder --help
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

Use `reverse()` to find addresses by longitude and latitude
(so called 'reverse geocoding').

The `reverse()` function returns the three addresses surrounding
the specified longitude and latitude.
(The results are formatted for better viewing)

The `candidate` of each element contains information about
the address node (AddressNode), and the `dist` contains
the distance (geodesic distance, in meters)
from the specified point to the representative point of the address.

```
>>> jageocoder.reverse(139.6917, 35.6896)
[
  {
    'candidate': {
      'id': 12299330, 'name': '二丁目',
      'x': 139.691774, 'y': 35.68945, 'level': 6,
      'note': 'postcode:1600023',
      'fullname': ['東京都', '新宿区', '西新宿', '二丁目']
    },
    'dist': 17.940303970792183
  }, {
    'candidate': {
      'id': 12300198, 'name': '六丁目',
      'x': 139.690969, 'y': 35.693426, 'level': 6,
      'note': 'postcode:1600023',
      'fullname': ['東京都', '新宿区', '西新宿', '六丁目']
    },
    'dist': 429.6327545403412
  }, {
    'candidate': {
      'id': 12300498, 'name': '四丁目',
      'x': 139.68762, 'y': 35.68754, 'level': 6,
      'note': 'postcode:1600023',
      'fullname': ['東京都', '新宿区', '西新宿', '四丁目']
    },
    'dist': 434.31591285255234
  }
]
```

If the `level` optional parameter is specified,
it will return a more detailed address.
However, it takes time to calculate.

```
>>> jageocoder.reverse(139.6917, 35.6896, level=7)
[
  {
    'candidate': {
      'id': 12299340, 'name': '8番',
      'x': 139.691778, 'y': 35.689627, 'level': 7,
      'note': None,
      'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番']
    },
    'dist': 7.669497303543382
  }, {
    'candidate': {
      'id': 12299330, 'name': '二丁目',
      'x': 139.691774, 'y': 35.68945, 'level': 6,
      'note': 'postcode:1600023',
      'fullname': ['東京都', '新宿区', '西新宿', '二丁目']
    },
    'dist': 17.940303970792183
  }, {
    'candidate': {
      'id': 12300588, 'name': '15番',
      'x': 139.688172, 'y': 35.689264, 'level': 7,
      'note': None,
      'fullname': ['東京都', '新宿区', '西新宿', '四丁目', '15番']
    },
    'dist': 321.50874020809823
  }
]
```

### Explore the attribute information of an address

Use `searchNode()` to retrieve information about an address.

This function returns a list of type `jageocoder.result` .
You can access the address node directly from this result.

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

# For developers

## Running the unittests

```python
python -m unittest
``` 

`tests.test_search` tests for some special address notations.

- Street address in Sapporo city such as '北3西1' for '北三条西一丁目'
- Toorina in Kyoto city such as '下立売通新町西入薮ノ内町' for '薮ノ内町'

## Create your own dictionary

Please use the dictionary coverter
[jageocoder-converter](https://github.com/t-sagara/jageocoder-converter).

## Sample Web Application

A sample of a simple web app using Flask is available under
`flask-demo`.

Perform the following steps. Then, access port 5000.

```
cd flask-demo
pip install flask flask-cors
bash run.sh
```

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
