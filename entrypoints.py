import configparser
import glob
from importlib import import_module
import io
import itertools
import os.path as osp
import sys
import zipfile

class EntryPoint(object):
    def __init__(self, name, module_name, object_name, distro):
        self.name = name
        self.module_name = module_name
        self.object_name = object_name
        self.distro = distro
    
    def __repr__(self):
        return "EntryPoint(%r, %r, %r, %r)" % \
            (self.name, self.module_name, self.object_name, self.distro)

    def load(self):
        obj_name_parts = self.object_name.split('.')
        mod = import_module(self.module_name)
        obj = mod
        for attr in obj_name_parts:
            obj = getattr(obj, attr)
        return obj
    
    @classmethod
    def from_string(cls, epstr, name, distro):
        mod, obj = epstr.split(':', 1)
        return cls(name, mod, obj, distro)

class Distribution(object):
    def __init__(self, name, version):
        self.name = name
        self.version = version
    
    def __repr__(self):
        return "Distribution(%r, %r)" % (self.name, self.version)


def iter_files_distros(path=None):
    if path is None:
        path = sys.path
    for folder in path:
        if folder.rstrip('/\\').endswith('.egg'):
            # Gah, eggs
            egg_name = osp.basename(folder)
            if '-' in egg_name:
                distro = Distribution(*egg_name.split('-')[:2])
            else:
                distro = None
            
            if osp.isdir(folder):
                ep_path = osp.join(folder, 'EGG-INFO', 'entry_points.txt')
                if osp.isfile(ep_path):
                    cp = configparser.ConfigParser()
                    cp.read(ep_path)
                    yield cp, distro

            elif zipfile.is_zipfile(folder):
                z = zipfile.ZipFile(folder)
                try:
                    info = z.getinfo('EGG-INFO/entry_points.txt')
                except KeyError:
                    continue
                cp = configparser.ConfigParser()
                with z.open(info) as f:
                    fu = io.TextIOWrapper(f)
                    cp.read_file(fu,
                        source=osp.join(folder, 'EGG-INFO', 'entry_points.txt'))
                yield cp, distro
            
        for path in itertools.chain(
            glob.iglob(osp.join(folder, '*.dist-info', 'entry_points.txt')),
            glob.iglob(osp.join(folder, '*.egg-info', 'entry_points.txt'))
        ):
            distro_name_version = osp.splitext(osp.basename(osp.dirname(path)))[0]
            if '-' in distro_name_version:
                distro = Distribution(*distro_name_version.split('-', 1))
            else:
                distro = None
            cp = configparser.ConfigParser()
            cp.read(path)
            yield cp, distro

def get_single(group, name, path=None):
    for config, distro in iter_files_distros(path=path):
        if (group in config) and (name in config[group]):
            epstr = config[group][name]
            return EntryPoint.from_string(epstr, name, distro)

def get_group_named(group, path=None):
    result = {}
    for ep in get_group_all(path=path):
        if ep.name not in result:
            result[ep.name] = ep
    return result

def get_group_all(group, path=None):
    result = []
    for config, distro in iter_files_distros(path=path):
        if group in config:
            for name, epstr in config[group].items():
                result.append(EntryPoint.from_string(epstr, name, distro))

    return result

if __name__ == '__main__':
    import pprint
    pprint.pprint(get_group_all('console_scripts'))
