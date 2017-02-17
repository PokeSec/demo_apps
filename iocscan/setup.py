"""
setup.py : Build script for app

This file is part of EPControl.

Copyright (C) 2016  Jean-Baptiste Galet & Timothe Aeberhardt

EPControl is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

EPControl is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with EPControl.  If not, see <http://www.gnu.org/licenses/>.
"""
from os import path, chdir
from setuptools import setup, find_packages
from spkbuilder.spk import bdist_spk, SpkDistribution

chdir(path.abspath(path.dirname(__file__)))

def get_long_description():
    """Get the long description from the README file"""
    here = path.abspath(path.dirname(__file__))
    try:
        with open(path.join(here, 'README.md'), encoding='utf-8') as ifile:
            return ifile.read()
    except OSError:
        return ""

setup(
    # Use the special SpkDistribution
    distclass=SpkDistribution,

    # The package name
    name='iocscan',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='0.0.2',

    title='IOCScanner',
    description='Hunt malicious items across your endpoints',
    # logo='logo.png',
    long_description=get_long_description(),

    # The project's main homepage.
    url='https://github.com/PokeSec/demo_apps',

    # Author details
    author='Jean-Baptiste Galet and Timothe Aeberhardt',
    author_email='epcontrol@jbgalet.fr',

    # Choose your license
    license='GNU General Public License v3 (GPLv3)',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3.5',
    ],
    # What does your project relate to?
    keywords='epcontrol,security,ioc,scanner',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(),

    # Alternatively, if you want to distribute just a my_module.py, uncomment
    # this:
    #   py_modules=["my_module"],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=[],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    extras_require={
        'dev': [],
        'test': [],
    },

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    package_data={
    },

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    data_files=[],

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
    },

    cmdclass={
        'bdist_spk': bdist_spk,
    },

    compatibility=dict(
        ostype=['server', 'workstation', 'mobile'],
        os=['windows', 'linux', 'macosx', 'android']
    ),

    configuration=[
        dict(
            title='.global',
            description='This configuration is used globally for the IOCScanner',
            variables=[
                dict(
                    name='schedule',
                    type='string',
                    description='Scan frequency',
                    default_value="weekly",
                    example='daily, weekly or monthly'
                )
            ]
        ),
        dict(
            title='IOCs',
            description='Configure the ruleset',
            variables=[
                dict(
                    name='RULES_FILE',
                    type='string',
                    description='Rules for the scanner',
                    default_value=""
                ),
            ],
        ),
    ],

    __old_config = [
        dict(
            title='Base config',
            description='Base configuration',
            variables=[
                dict(
                    name='SCAN_ROOTS',
                    type='list_of_strings',
                    description='Base paths to scan',
                    description_long=
"""
Scan the provided file paths

Windows roots must be specified as:
* Drive: (e.g. C:)
* Path member with either / or \ (e.g. \Windows)

Linux and android roots must be specified as:
* Path members with / (e.g. /sdcard)

You can use one text field per item or group multiple values in a single field, separated by a |

An empty list will scan all compatible file systems on the device
""",
                    example="C:|D:|/sdcard|/",
                    default_value="[]"
                ),
                dict(
                    name='SCAN_EXTENSIONS',
                    type='list_of_strings',
                    description='Extensions to scan',
                    description_long=
"""
The list of extensions to scan

You can use one text field per item or group multiple values in a single field, separated by a |

An ampty list will scan all files
""",
                    example=".exe|.dll|.scr|.sys|.pif'",
                    default_value="[]"
                ),
                dict(
                    name='MAX_SIZE',
                    type='integer',
                    description='Max size of files (MB)',
                    description_long='Files larger, than the provided size will not be scanned',
                    example="256",
                    default_value="256"
                ),
                dict(
                    name='EXCLUDE_FILES',
                    type='list_of_strings',
                    description='List of file exclusions',
                    description_long=
"""
Ignore the provided files

You can use one text field per item or group multiple values in a single field, separated by a |
""",
                    example="pagefile.sys|hiberfil.sys|swapfile.sys",
                    default_value="[]"
                ),
                dict(
                    name='EXCLUDE_DIRS',
                    type='list_of_strings',
                    description='List of directory exclusions',
                    description_long=
"""
Ignore the provided directories (and therefore all files below)

You can use one text field per item or group multiple values in a single field, separated by a |
""",
                    example="Program Files|Program Files (x86)|proc|run|dev|.git",
                    default_value="[]"
                )
            ]
        ),
        dict(
            title='Advanced config',
            description='Optional configuration',
            variables=[
                dict(
                    name='YARA_FASTSCAN_MODE',
                    type='boolean',
                    description='Enable the fast node of yara',
                    default_value="false"
                ),
                dict(
                    name='INCLUDE_DELETED',
                    type='boolean',
                    description='Also scan deleted files',
                    default_value="false"
                ),
            ],
        ),
    ],

    uappid='b59f9472-2d71-4ca7-be3e-8b6322e4cfba',
)
