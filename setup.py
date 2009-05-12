#
# Copyright 2009 Paul J. Davis <paul.joseph.davis@gmail.com>
#
# This file is part of the python-spidermonkey package released
# under the MIT license.
#

"""\
Python/JavaScript bridge module, making use of Mozilla's spidermonkey
JavaScript implementation.  Allows implementation of JavaScript classes,
objects and functions in Python, and evaluation and calling of JavaScript
scripts and functions respectively.  Borrows heavily from Claes Jacobssen's
Javascript Perl module, in turn based on Mozilla's 'PerlConnect' Perl binding.
""",

from glob import glob
# I haven't the sligthest, but this appears to fix
# all those EINTR errors. Pulled and adapted for OS X
# from twisted bug #733
# 
# Definitely forgot to comment this out before distribution.
#
# import ctypes
# import signal
# libc = ctypes.CDLL("libc.dylib")
# libc.siginterrupt(signal.SIGCHLD, 0)

import os
import subprocess as sp
import sys
from distutils.dist import Distribution
import ez_setup
ez_setup.use_setuptools()
from setuptools import setup, Extension

use_system_library = '--system-library' in sys.argv
DEBUG = "--debug" in sys.argv

def find_sources(extensions=[".c", ".cpp"]):
    if use_system_library:
        return reduce(lambda x, y: x + y,
                      [glob('spidermonkey/*' + x) for x in extensions])
    else:
        sources = []
        for dpath, dnames, fnames in os.walk('./spidermonkey'):
            sources += [os.path.join(dpath, f)
                        for f in fnames
                        if os.path.splitext(f)[1] in extensions]
        return sources

def pkg_config(package):
    pipe = sp.Popen("pkg-config --cflags --libs %s" % package,
                        shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    (stdout, stderr) = pipe.communicate()
    if pipe.wait() != 0:
        raise RuntimeError("Failed to get package config flags for '%s'." %
                           package)
    flags = {
        "include_dirs": [],
        "library_dirs": [],
        "libraries": [],
        "extra_compile_args": [],
        "extra_link_args": []
    }
    prefixes = {
        "-I": ("include_dirs", 2),
        "-L": ("library_dirs", 2),
        "-l": ("libraries", 2),
        "-D": ("extra_compile_args", 0),
        "-Wl": ("extra_link_args", 0)
    }
    for flag in stdout.split():
        for prefix in prefixes:
            if flag.startswith(prefix):
                # hack for xulrunner
                if flag.endswith('/stable'):
                    flag = flag[:-6] + 'unstable'
                name, trim = prefixes[prefix]
                flags[name].append(flag[trim:])
    return flags

def nspr_config():
    return pkg_config('nspr')

def js_config(prefix='mozilla'):
    cfg = pkg_config(prefix + '-js')
    if '-DJS_THREADSAFE' not in cfg['extra_compile_args']:
        raise RuntimeError('python-spidermonkey requires a threadsafe ' + \
                           'spidermonkey library to link against.')
    return cfg

def platform_config():
    sysname = os.uname()[0]
    machine = os.uname()[-1]

    if use_system_library:
        config = js_config()
    else:
        config = nspr_config()
        config['include_dirs'].append('spidermonkey/libjs')
    config["include_dirs"].append("spidermonkey/%s-%s" % (sysname, machine))
    config["extra_compile_args"].extend([
        "-DJS_THREADSAFE",
        "-DPOSIX_SOURCE",
        "-D_BSD_SOURCE",
        "-Wno-strict-prototypes"
    ])
    if DEBUG:
        config["extra_compile_args"].extend([
            "-UNDEBG",
            "-DDEBUG",
            "-DJS_PARANOID_REQUEST"
        ])


    if sysname in ["Linux", "FreeBSD"]:
        config["extra_compile_args"].extend([
            "-DHAVE_VA_COPY",
            "-DVA_COPY=va_copy"
            ])

    if sysname in ["Darwin", "Linux", "FreeBSD"]:
        config["extra_compile_args"].append("-DXP_UNIX")
    else:
        raise RuntimeError("Unknown system name: %s" % sysname)

    return config

Distribution.global_options.append(('system-library', None,
                                    'Use system JS library instead of bundled'))
Distribution.global_options.append(("debug", None,
                    "Build a DEBUG version of spidermonkey"))

setup(
    name = "python-spidermonkey",
    version = "0.0.6",
    license = "MIT",
    author = "Paul J. Davis",
    author_email = "paul.joseph.davis@gmail.com",
    description = "JavaScript / Python bridge.",
    long_description = __doc__,
    url = "http://github.com/davisp/python-spidermonkey",
    download_url = "http://github.com/davisp/python-spidermonkey.git",
    zip_safe = False,
    
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: C',
        'Programming Language :: JavaScript',
        'Programming Language :: Other',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Browsers',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    
    setup_requires = [
        'setuptools>=0.6c8',
        'nose>=0.10.0',
    ],

    ext_modules =  [
        Extension(
            "spidermonkey",
            sources=find_sources(),
            **platform_config()
        )
    ],

    test_suite = 'nose.collector',

)
