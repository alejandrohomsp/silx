#!/usr/bin/python
# coding: utf8
# /*##########################################################################
#
# Copyright (c) 2015-2016 European Synchrotron Radiation Facility
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# ###########################################################################*/

__authors__ = ["Jérôme Kieffer", "Thomas Vincent"]
__date__ = "07/12/2015"
__license__ = "MIT"


import sys
import os
import platform

from numpy.distutils.misc_util import Configuration

try:
    from setuptools import setup
    from setuptools.command.build_py import build_py as _build_py
    from setuptools.command.build_ext import build_ext
except ImportError:
    from numpy.distutils.core import setup
    from distutils.command.build_py import build_py as _build_py
    from distutils.command.build_ext import build_ext

PROJECT = "silx"
cmdclass = {}


# Check if action requires build/install
DRY_RUN = len(sys.argv) == 1 or (len(sys.argv) >= 2 and (
    '--help' in sys.argv[1:] or
    sys.argv[1] in ('--help-commands', 'egg_info', '--version',
                    'clean', '--name')))


def get_version():
    import version
    return version.strictversion


def get_readme():
    dirname = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(dirname, "README.md"), "r") as fp:
        long_description = fp.read()
    return long_description


classifiers = ["Development Status :: 1 - Planning",
               "Environment :: Console",
               "Environment :: MacOS X",
               "Environment :: Win32 (MS Windows)",
               "Environment :: X11 Applications :: Qt",
               "Intended Audience :: Education",
               "Intended Audience :: Science/Research",
               "License :: OSI Approved :: MIT License",
               "Natural Language :: English",
               "Operating System :: Microsoft :: Windows",
               "Operating System :: POSIX",
               "Programming Language :: Cython",
               "Programming Language :: Python :: 2",
               "Programming Language :: Python :: 3",
               "Programming Language :: Python :: Implementation :: CPython",
               "Topic :: Documentation :: Sphinx",
               "Topic :: Scientific/Engineering :: Physics",
               "Topic :: Software Development :: Libraries :: Python Modules",
               ]


# ########## #
# version.py #
# ########## #

class build_py(_build_py):
    """
    Enhanced build_py which copies version.py to <PROJECT>._version.py
    """
    def find_package_modules(self, package, package_dir):
        modules = _build_py.find_package_modules(self, package, package_dir)
        if package == PROJECT:
            modules.append((PROJECT, '_version', 'version.py'))
        return modules


cmdclass['build_py'] = build_py


# ################### #
# build_doc commandes #
# ################### #

try:
    import sphinx
    import sphinx.util.console
    sphinx.util.console.color_terminal = lambda: False
    from sphinx.setup_command import BuildDoc
except ImportError:
    sphinx = None

if sphinx:
    class build_doc(BuildDoc):

        def run(self):
            # make sure the python path is pointing to the newly built
            # code so that the documentation is built on this and not a
            # previously installed version

            build = self.get_finalized_command('build')
            sys.path.insert(0, os.path.abspath(build.build_lib))

#             # Copy gui files to the path:
#             dst = os.path.join(
#                 os.path.abspath(build.build_lib), "pyFAI", "gui")
#             if not os.path.isdir(dst):
#                 os.makedirs(dst)
#             for i in os.listdir("gui"):
#                 if i.endswith(".ui"):
#                     src = os.path.join("gui", i)
#                     idst = os.path.join(dst, i)
#                     if not os.path.exists(idst):
#                         shutil.copy(src, idst)

            # Build the Users Guide in HTML and TeX format
            for builder in ('html', 'latex'):
                self.builder = builder
                self.builder_target_dir = os.path.join(self.build_dir, builder)
                self.mkpath(self.builder_target_dir)
                BuildDoc.run(self)
            sys.path.pop(0)
    cmdclass['build_doc'] = build_doc


# ############################# #
# numpy.distutils Configuration #
# ############################# #

def configuration(parent_package='', top_path=None):
    """Recursive construction of package info to be used in setup().

    See http://docs.scipy.org/doc/numpy/reference/distutils.html#numpy.distutils.misc_util.Configuration
    """  # noqa
    config = Configuration(None, parent_package, top_path)
    config.set_options(
        ignore_setup_xxx_py=True,
        assume_default_configuration=True,
        delegate_options_to_subpackages=True,
        quiet=True)
    config.add_subpackage(PROJECT)
    return config


config = configuration()


# ############## #
# OpenMP support #
# ############## #

def check_openmp():
    """Do we compile with OpenMP?

    Store the result in WITH_OPENMP environment variable

    :return: True if available and not disabled.
    """
    if "WITH_OPENMP" in os.environ:
        return os.environ["WITH_OPENMP"] == "False"

    elif "--no-openmp" in sys.argv:
        sys.argv.remove("--no-openmp")
        os.environ["WITH_OPENMP"] = "False"
        print("No OpenMP requested by command line")
        return False

    elif ("--openmp" in sys.argv):
        sys.argv.remove("--openmp")
        os.environ["WITH_OPENMP"] = "True"
        print("OpenMP requested by command line")
        return True

    if platform.system() == "Darwin":
        # By default Xcode5 & XCode6 do not support OpenMP, Xcode4 is OK.
        osx = tuple([int(i) for i in platform.mac_ver()[0].split(".")])
        if osx >= (10, 8):
            os.environ["WITH_OPENMP"] = "False"
            return False

    os.environ["WITH_OPENMP"] = "True"
    return True


USE_OPENMP = check_openmp()


# ############## #
# Compiler flags #
# ############## #

class BuildExtFlags(build_ext):
    """Handle compiler and linker flags.

    If OpenMP is disabled, it removes OpenMP compile flags.
    If building with MSVC, compiler flags are converted from gcc flags.
    """

    COMPILE_ARGS_CONVERTER = {'-fopenmp': '/openmp'}

    LINK_ARGS_CONVERTER = {'-fopenmp': ' '}

    def build_extensions(self):
        # Remove OpenMP flags if OpenMP is disabled
        if not USE_OPENMP:
            for ext in self.extensions:
                ext.extra_compile_args = [
                    f for f in ext.extra_compile_args if f != '-fopenmp']
                ext.extra_link_args = [
                    f for f in ext.extra_link_args if f != '-fopenmp']

        # Convert flags from gcc to MSVC if required
        if self.compiler.compiler_type == 'msvc':
            for ext in self.extensions:
                ext.extra_compile_args = [self.COMPILE_ARGS_CONVERTER.get(f, f)
                                          for f in ext.extra_compile_args]
                ext.extra_link_args = [self.LINK_ARGS_CONVERTER.get(f, f)
                                       for f in ext.extra_link_args]

        build_ext.build_extensions(self)


cmdclass['build_ext'] = BuildExtFlags


# ############## #
# Cython support #
# ############## #

CYTHON_MIN_VERSION = '0.18'


def check_cython():
    """
    Check if cython must be activated fron te command line or the environment.

    Store the result in WITH_CYTHON environment variable.

    :return: True if available and not disabled.
    """

    if "WITH_CYTHON" in os.environ:
        if os.environ["WITH_CYTHON"] in ["False", "0", 0]:
            os.environ["WITH_CYTHON"] = "False"
            return False

    if "--no-cython" in sys.argv:
        sys.argv.remove("--no-cython")
        print("No Cython requested by command line")
        os.environ["WITH_CYTHON"] = "False"
        return False

    try:
        import Cython.Compiler.Version
    except ImportError:
        os.environ["WITH_CYTHON"] = "False"
        return False
    else:
        if Cython.Compiler.Version.version < CYTHON_MIN_VERSION:
            os.environ["WITH_CYTHON"] = "False"
            return False

    os.environ["WITH_CYTHON"] = "True"
    return True


USE_CYTHON = check_cython()


def fake_cythonize(extensions):
    """Replace cython files by .c or .cpp files in extension's sources.

    It replaces the *.pyx and *.py source files of the extensions
    to either *.cpp or *.c source files.
    No compilation is performed.

    :param iterable extensions: List of extensions to patch.
    """
    for ext_module in extensions:
        new_sources = []
        for source in ext_module.sources:
            base, ext = os.path.splitext(source)
            if ext in ('.pyx', '.py'):
                if ext_module.language == 'c++':
                    source = base + '.cpp'
                else:
                    source = base + '.c'
                if not os.path.isfile(source):
                    raise RuntimeError("Source file not found: %s" % source)
            new_sources.append(source)
        ext_module.sources = new_sources


if not DRY_RUN and USE_CYTHON:
    # Cythonize extensions
    from Cython.Build import cythonize

    config.ext_modules = cythonize(
        config.ext_modules,
        force=True,
        compile_time_env={"HAVE_OPENMP": bool(USE_OPENMP)}
    )
else:
    # Do not use Cython but convert source names from .pyx to .c or .cpp
    fake_cythonize(config.ext_modules)


# ##### #
# setup #
# ##### #

setup_kwargs = config.todict()


install_requires = ["numpy"]
setup_requires = ["numpy"]

setup_kwargs.update(
    name=PROJECT,
    version=get_version(),
    url="https://github.com/silex-kit/silx",
    author="data analysis unit",
    author_email="silx@esrf.fr",
    classifiers=classifiers,
    description="Software library for X-Ray data analysis",
    long_description=get_readme(),
    install_requires=install_requires,
    setup_requires=setup_requires,
    cmdclass=cmdclass,
    )

setup(**setup_kwargs)
