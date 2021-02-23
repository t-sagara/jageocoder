import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "jageocoder",
    version = "0.1.0",
    author_email = "sagara@info-proto.com",
    description = ("A basic implementation of Japanese address geocoder."),
    license = "CC BY-SA 2.0",
    keywords = "geocoder, address, Japanese",
    url = "http://packages.python.org/an_example_pypi_project",
    packages=['jageocoder', 'tests'],
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 1 - Alpha",
        "Topic :: Utilities",
    ],
)
