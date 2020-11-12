import os
import re

from pycrud import __version__


def test_version():
    project_file = open(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'pyproject.toml')), 'r', encoding='utf-8').read()
    m = re.search(r"version = \"(.+?)\"", project_file)
    assert m.group(1) == __version__
