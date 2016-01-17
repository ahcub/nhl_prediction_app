import sys
from distutils.core import setup
from os.path import join, dirname

setup(
    windows=[{"script": "launcher.py", "icon_resources": [(1, join(dirname(sys.argv[0]), 'hokey.ico'))]}],
    options={"py2exe": {"includes": ["sip", 'lxml.etree', 'lxml._elementpath', 'gzip', 'pandas', 'numpy']}},
    requires=['requests', 'lxml', 'PyQt4', 'pandas'],
    data_files=[('.', [join(dirname(sys.argv[0]), 'up.png')]),
                ('.', [join(dirname(sys.argv[0]), 'down.png')]),
                ('.', [join(dirname(sys.argv[0]), 'hokey.png')])])
