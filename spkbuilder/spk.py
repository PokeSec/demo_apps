"""
spk.py : Builkd spk distributions

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

Inspired by setuptools/command/bdist_egg.py
"""
from distutils.dir_util import remove_tree, mkpath
from distutils import log
from distutils.dist import Distribution
import os
import marshal
from hashlib import sha256
from pathlib import Path
import textwrap
import json
from sysconfig import get_path
import shutil

from pkg_resources import get_build_platform
from setuptools.extension import Library
from setuptools import Command


def _get_purelib():
    return get_path("purelib")


def strip_module(filename):
    if '.' in filename:
        filename = os.path.splitext(filename)[0]
    if filename.endswith('module'):
        filename = filename[:-6]
    return filename


def write_stub(resource, pyfile):
    _stub_template = textwrap.dedent("""
        def __bootstrap__():
            global __bootstrap__, __loader__, __file__
            import sys, pkg_resources, imp
            __file__ = pkg_resources.resource_filename(__name__, %r)
            __loader__ = None; del __bootstrap__, __loader__
            imp.load_dynamic(__name__,__file__)
        __bootstrap__()
        """).lstrip()
    with open(pyfile, 'w') as f:
        f.write(_stub_template % resource)


class SpkDistribution(Distribution):
    def __init__(self, attrs=None):
        self.attrs = attrs
        super().__init__(attrs)


class bdist_spk(Command):
    description = "create an \"spk\" distribution"

    user_options = [
        ('bdist-dir=', 'b',
         "temporary directory for creating the distribution"),
        ('plat-name=', 'p', "platform name to embed in generated filenames "
                            "(default: %s)" % get_build_platform()),
        ('exclude-source-files', None,
         "remove all .py files from the generated spk"),
        ('keep-temp', 'k',
         "keep the pseudo-installation tree around after " +
         "creating the distribution archive"),
        ('dist-dir=', 'd',
         "directory to put final built distributions in"),
        ('skip-build', None,
         "skip rebuilding everything (for testing/debugging)"),
    ]

    boolean_options = [
        'keep-temp', 'skip-build', 'exclude-source-files'
    ]

    def initialize_options(self):
        self.bdist_dir = None
        self.plat_name = None
        self.keep_temp = 0
        self.dist_dir = None
        self.skip_build = 0
        self.egg_output = None
        self.exclude_source_files = True

    def finalize_options(self):
        # ei_cmd = self.ei_cmd = self.get_finalized_command("egg_info")
        # self.egg_info = ei_cmd.egg_info

        if self.bdist_dir is None:
            bdist_base = self.get_finalized_command('bdist').bdist_base
            self.bdist_dir = os.path.join(bdist_base, 'spk')

        if self.plat_name is None:
            self.plat_name = get_build_platform()

        self.set_undefined_options('bdist', ('dist_dir', 'dist_dir'))

        self.egg_output = os.path.join(self.dist_dir, self.distribution.get_name() + '.spk')

    def do_install_data(self):
        # Hack for packages that install data to install's --install-lib
        self.get_finalized_command('install').install_lib = self.bdist_dir

        site_packages = os.path.normcase(os.path.realpath(_get_purelib()))
        old, self.distribution.data_files = self.distribution.data_files, []

        for item in old:
            if isinstance(item, tuple) and len(item) == 2:
                if os.path.isabs(item[0]):
                    realpath = os.path.realpath(item[0])
                    normalized = os.path.normcase(realpath)
                    if normalized == site_packages or normalized.startswith(
                        site_packages + os.sep
                    ):
                        item = realpath[len(site_packages) + 1:], item[1]
                        # XXX else: raise ???
            self.distribution.data_files.append(item)

        try:
            log.info("installing package data to %s" % self.bdist_dir)
            self.call_command('install_data', force=0, root=None)
        finally:
            self.distribution.data_files = old

    def get_outputs(self):
        return [self.egg_output]

    def call_command(self, cmdname, **kw):
        """Invoke reinitialized command `cmdname` with keyword args"""
        for dirname in INSTALL_DIRECTORY_ATTRS:
            kw.setdefault(dirname, self.bdist_dir)
        kw.setdefault('skip_build', self.skip_build)
        kw.setdefault('dry_run', self.dry_run)
        cmd = self.reinitialize_command(cmdname, **kw)
        self.run_command(cmdname)
        return cmd

    def byte_compile(self, base_path, path):
        log.info("Compiling %s" % path)
        relpath = path.relative_to(base_path)
        ext = path.suffix

        module = 'apps.{}'.format(
            str(relpath.as_posix()).replace(ext, '').replace('/', '.'))

        is_pkg = False
        if path.stem == '__init__':
            module = module.replace('.__init__', '')
            is_pkg = True

        print(module)
        filename = sha256(module.encode('ascii')).hexdigest()

        data = compile(
            path.read_bytes(),
            '<app | {} | {}>'.format(self.distribution.get_name(), relpath.as_posix()),
            'exec',
            dont_inherit=False,
            optimize=2)
        bincode = marshal.dumps(data)
        with open(os.path.join(self.bdist_dir, filename), 'wb') as ofile:
            ofile.write(bincode)
        metadata = {
            'module': module,
            'filename': filename,
            'is_pkg': is_pkg
        }

        return metadata

    def run(self):
        # Generate metadata first
        # self.run_command("egg_info")
        # We run install_lib before install_data, because some data hacks
        # pull their data path from the install_lib command.
        log.info("installing library code to %s" % self.bdist_dir)
        instcmd = self.get_finalized_command('install')
        old_root = instcmd.root
        instcmd.root = None
        if self.distribution.has_c_libraries() and not self.skip_build:
            self.run_command('build_clib')
        cmd = self.call_command('install_lib', warn_dir=0, compile=False, optimize=0)
        instcmd.root = old_root

        all_outputs, ext_outputs = self.get_ext_outputs()
        self.stubs = []
        to_compile = []

        for (p, ext_name) in enumerate(ext_outputs):
            filename, ext = os.path.splitext(ext_name)
            pyfile = os.path.join(self.bdist_dir, strip_module(filename) +
                                  '.py')
            self.stubs.append(pyfile)
            log.info("creating stub loader for %s" % ext_name)
            if not self.dry_run:
                write_stub(os.path.basename(ext_name), pyfile)
            to_compile.append(pyfile)
            ext_outputs[p] = ext_name.replace(os.sep, '/')

        modules = []
        bdist_path = Path(self.bdist_dir)
        for item in bdist_path.glob('**/*.py'):
            modules.append(self.byte_compile(bdist_path, item))

        app_config = dict(
            name=self.distribution.get_name(),
            title=self.distribution.attrs.get('title'),
            logo=os.path.basename(self.distribution.attrs.get('logo')) if self.distribution.attrs.get('logo') else None,
            compatibility=self.distribution.attrs.get('compatibility'),
            description=self.distribution.get_description(),
            version=self.distribution.get_version(),
            developer=dict(
                email=self.distribution.get_author_email(),
                name=self.distribution.get_author(),
                website=self.distribution.get_url(),
            ),
            uappid=self.distribution.attrs.get('uappid'),
            category=self.distribution.get_keywords(),
            configuration=self.distribution.attrs.get('configuration')
        )

        manifest = dict(
            app_config=app_config,
            modules=modules
        )
        with open(os.path.join(self.bdist_dir, 'manifest.json'), 'w') as ofile:
            json.dump(manifest, ofile)

        # Add the logo in the package
        if self.distribution.attrs.get('logo'):
            shutil.copy(self.distribution.attrs.get('logo'), self.bdist_dir)

        if to_compile:
            cmd.byte_compile(to_compile)
        if self.distribution.data_files:
            self.do_install_data()

        # Make the EGG-INFO directory
        archive_root = self.bdist_dir

        if self.exclude_source_files:
            self.zap_pyfiles()

        # Make the archive
        make_zipfile(self.egg_output, archive_root, verbose=self.verbose,
                     dry_run=self.dry_run, mode='w')
        if not self.keep_temp:
            remove_tree(self.bdist_dir, dry_run=self.dry_run)

    def zap_pyfiles(self):
        log.info("Removing .py files from temporary directory")
        for base, dirs, files in walk_spk(self.bdist_dir):
            for name in files:
                if name.endswith('.py'):
                    path = os.path.join(base, name)
                    log.debug("Deleting %s", path)
                    os.unlink(path)

    def get_ext_outputs(self):
        """Get a list of relative paths to C extensions in the output distro"""

        all_outputs = []
        ext_outputs = []

        paths = {self.bdist_dir: ''}
        for base, dirs, files in os.walk(self.bdist_dir):
            for filename in files:
                if os.path.splitext(filename)[1].lower() in NATIVE_EXTENSIONS:
                    all_outputs.append(paths[base] + filename)
            for filename in dirs:
                paths[os.path.join(base, filename)] = (paths[base] +
                                                       filename + '/')

        if self.distribution.has_ext_modules():
            build_cmd = self.get_finalized_command('build_ext')
            for ext in build_cmd.extensions:
                if isinstance(ext, Library):
                    continue
                fullname = build_cmd.get_ext_fullname(ext.name)
                filename = build_cmd.get_ext_filename(fullname)
                if not os.path.basename(filename).startswith('dl-'):
                    if os.path.exists(os.path.join(self.bdist_dir, filename)):
                        ext_outputs.append(filename)

        return all_outputs, ext_outputs


NATIVE_EXTENSIONS = dict.fromkeys('.dll .so .dylib .pyd'.split())


def walk_spk(egg_dir):
    """Walk an unpacked egg's contents, skipping the metadata directory"""
    walker = os.walk(egg_dir)
    base, dirs, files = next(walker)
    yield base, dirs, files
    for bdf in walker:
        yield bdf

# Attribute names of options for commands that might need to be convinced to
# install to the egg build directory

INSTALL_DIRECTORY_ATTRS = [
    'install_lib', 'install_dir', 'install_data', 'install_base'
]


def make_zipfile(zip_filename, base_dir, verbose=0, dry_run=0, compress=True,
                 mode='w'):
    """Create a zip file from all the files under 'base_dir'.  The output
    zip file will be named 'base_dir' + ".zip".  Uses either the "zipfile"
    Python module (if available) or the InfoZIP "zip" utility (if installed
    and found on the default search path).  If neither tool is available,
    raises DistutilsExecError.  Returns the name of the output zip file.
    """
    import zipfile

    mkpath(os.path.dirname(zip_filename), dry_run=dry_run)
    log.info("creating '%s' and adding '%s' to it", zip_filename, base_dir)

    def visit(z, dirname, names):
        for name in names:
            path = os.path.normpath(os.path.join(dirname, name))
            if os.path.isfile(path):
                p = path[len(base_dir) + 1:]
                if not dry_run:
                    z.write(path, p)
                log.debug("adding '%s'" % p)

    compression = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    if not dry_run:
        z = zipfile.ZipFile(zip_filename, mode, compression=compression)
        for dirname, dirs, files in os.walk(base_dir):
            visit(z, dirname, files)
        z.close()
    else:
        for dirname, dirs, files in os.walk(base_dir):
            visit(None, dirname, files)
    return zip_filename
