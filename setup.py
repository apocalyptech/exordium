#!/usr/bin/env python
# vim: set expandtab tabstop=4 shiftwidth=4:

import os
from setuptools import find_packages, setup
from exordium import __version__

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-exordium',
    version=__version__,
    packages=find_packages(),
    include_package_data=True,
    license='BSD License',
    description='A Django-based readonly web music library application.',
    long_description=README,
    url='https://apocalyptech.com/exordium/',
    author='CJ Kucera',
    author_email='pez@apocalyptech.com',
    install_requires=[
        'django >= 1.10',
        'mutagen >= 1.34.1',
        'Pillow >= 3.3.1',
        'django-tables2 >= 1.2.5',
        'django-dynamic-preferences >= 0.8.2',
    ],
    # https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.10',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Multimedia :: Sound/Audio',
    ],
)

