# Configuration file for the Sphinx documentation builder.
import jageocoder

# -- Project information

project = 'jageocoder'
copyright = '2022, sagara@info-proto.com'
author = 'Takeshi Sagara'

release = jageocoder.version()  # '1.3'
version = jageocoder.version()  # '1.3.0dev1'

# -- General configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',  # Numpy style pydoc
    'myst_parser',  # Use Markdown
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

# -- Options for HTML output

html_theme = 'sphinx_rtd_theme'

# -- Options for EPUB output
epub_show_urls = 'footnote'
