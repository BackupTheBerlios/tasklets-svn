#!/usr/bin/env python

from distutils.core import setup

setup(
    name='Softlets',
    version='0.1',
    description='A generic cooperative thread scheduler',
    author='Antoine Pitrou',
    author_email='antoine@pitrou.net',
    url='http://developer.berlios.de/projects/tasklets',
    download_url='http://developer.berlios.de/svn/?group_id=2599',
    packages=['softlets', 'softlets.core'],
    license="GNU LGPL",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
        'Natural Language :: English',
        'Natural Language :: French',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
#         'Topic :: Communications',
        'Topic :: Software Development :: Libraries',
    ],
)


