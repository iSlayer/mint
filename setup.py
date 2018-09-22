# new version to pypi => python setup.py sdist upload
import os
from setuptools import setup

try:
    from pypandoc import convert
    read_md = lambda f: convert(f, 'rst')
except ImportError:
    print("warning: pypandoc module not found, could not convert Markdown to RST")
    read_md = lambda f: open(f, 'r').read()

readme = os.path.join(os.path.dirname(__file__), 'README.md')
setup(
    name='mint_analyzer',
    description='an analysis tool for Mint.com data',
    long_description=read_md(readme) if os.path.exists(readme) else '',
    version='1.00',
    packages=['mintapi'],
    license='The MIT License',
    author='David E Lester Jr'
    author_email='de.lester.jr@gmail.com',
    url='https://github.com/iSlayer/mint',
    install_requires=['mock', 'requests', 'selenium-requests', 'xmltodict', 'pandas'],
    entry_points=dict(
        console_scripts=[
            'mint = mint.mint_analyzer:main',
        ],
    ),
)
