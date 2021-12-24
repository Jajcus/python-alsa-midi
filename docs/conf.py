
import os
import sys

docs_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(docs_path))


project = 'python-alsa-midi'
copyright = '2021, Jacek Konieczny'
author = 'Jacek Konieczny'

version = ''
release = ''


needs_sphinx = '4.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']

source_suffix = '.rst'

master_doc = 'index'

language = None

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

pygments_style = None

autodoc_typehints = "description"
python_use_unqualified_type_names = True

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

intersphinx_mapping = {'https://docs.python.org/': None}
