'''Build native packages for Android'''

import os
import platform
import re
import subprocess
import sys


__author__ = 'Mansour Moufid'
__copyright__ = 'Copyright 2021, Mansour Moufid'
__license__ = 'ISC'
__version__ = '0.5'
__email__ = 'mansourmoufid@gmail.com'
__status__ = 'Development'


abi = os.environ.get('ABI', 'arm64-v8a')
if abi == 'armeabi-v7a':
    api = os.environ.get('API', '19')
    arch = 'arm'
    march = 'armv7-a'
    triplet = 'arm-linux-androideabi'
elif abi == 'arm64-v8a':
    api = os.environ.get('API', '21')
    arch = 'arm64'
    march = 'armv8-a'
    triplet = 'aarch64-linux-android'
else:
    raise NotImplementedError('ABI={}'.format(abi))

sdk = os.environ.get('ANDROID_SDK_ROOT', None)
if sdk is None:
    sdk = os.environ.get('ANDROIDSDK', None)
if sdk is None:
    home = os.environ.get('ANDROID_HOME', None)
    if home is None:
        home = os.environ.get('ANDROIDHOME', None)
    sdk = os.path.join(home, 'sdk')
else:
    home = os.path.dirname(sdk)
assert os.path.exists(home), 'ANDROID_HOME={}'.format(home)
assert os.path.exists(sdk), 'ANDROID_SDK_ROOT={}'.format(sdk)
ndk = os.environ.get('ANDROIDNDK', os.path.join(sdk, 'ndk-bundle'))
if not os.path.exists(ndk):
    ndk = os.path.join(sdk, 'ndk')
assert os.path.exists(ndk), ndk

CFLAGS = [
    '-fno-strict-aliasing',
    '-fno-strict-overflow',
    '-fpic',
    '-fwrapv',
    '-Wno-macro-redefined',
    '-Wno-unused-command-line-argument',
]
CPPFLAGS = [
    '-D_FORTIFY_SOURCE=1',
]
LDFLAGS = [
    '-Wl,-z,noexecstack',
    '-Wl,-z,relro',
]


def splitescaped(xs):
    return re.split(r'(?<!\\) ', xs)


for x in splitescaped(os.environ.get('CPPFLAGS', '')):
    match = re.search(r'-I(.+)', x)
    if match:
        path = match.group(1).replace('\\ ', ' ')
        if os.path.exists(os.path.join(path, 'Python.h')):
            CPPFLAGS.append(x)
            break
libpython = None
for x in splitescaped(os.environ.get('LDFLAGS', '')):
    match = re.search(r'-l(python.*)', x)
    if match:
        libpython = match.group(1)
        LDFLAGS.append(x)
        break
if libpython is not None:
    for x in splitescaped(os.environ.get('LDFLAGS', '')):
        match = re.search(r'-L(.+)', x)
        if match:
            path = match.group(1).replace('\\ ', ' ')
            lib = os.path.join(path, 'lib{}.so'.format(libpython))
            if os.path.exists(lib):
                LDFLAGS.append(x)
                break

debug = bool(int(os.environ.get('DEBUG', 1)))
if debug:
    CFLAGS.append('-g')
    CFLAGS.append('-O0')
else:
    CFLAGS.append('-Os')
    CPPFLAGS.append('-DNDEBUG=1')
    LDFLAGS.append('-Wl,-S')

if os.path.exists(os.path.join(ndk, 'source.properties')):
    for line in open(os.path.join(ndk, 'source.properties'), 'rt'):
        match = re.search(r'Pkg.Revision = ([0-9.]+)', line)
        if match:
            ndk_version = match.group(1)
else:
    versions = list(sorted(
        (x.name for x in os.scandir(ndk)),
        key=lambda x: x.split('.')
    ))
    ndk_version = versions[-1]
ndk_version = tuple(int(x) for x in ndk_version.split('.'))

if ndk_version < (19,):
    target = triplet
    toolchain = '{}-{}-toolchain'.format(target, api)
    if not os.path.exists(toolchain):
        subprocess.run([
            os.path.join(
                ndk, 'build', 'tools', 'make_standalone_toolchain.py',
            ),
            '--arch', arch,
            '--api', api,
            '--install-dir={}'.format(toolchain),
        ])
    toolchain = os.path.realpath(toolchain)
    assert os.path.exists(toolchain), toolchain
    AR = '{}-ar'.format(target)
    AS = '{}-clang'.format(target)
    # LD = '{}-ld'.format(target)
    LD = '{}-clang'.format(target)
    RANLIB = '{}-ranlib'.format(target)
    READELF = '{}-readelf'.format(target)
else:
    host = '{}-{}'.format(platform.system(), platform.machine()).lower()
    if host == 'darwin-arm64':
        host = 'darwin-x86_64'
    toolchain = os.path.join(ndk, 'toolchains', 'llvm', 'prebuilt', host)
    if not os.path.exists(toolchain):
        toolchain = os.path.join(
            ndk,
            '.'.join(str(x) for x in ndk_version),
            'toolchains', 'llvm', 'prebuilt',
            host
        )
    assert os.path.exists(toolchain), toolchain
    if abi == 'armeabi-v7a':
        target = 'armv7a-linux-androideabi{}'.format(api)
    elif abi == 'arm64-v8a':
        target = 'aarch64-linux-android{}'.format(api)
    else:
        raise NotImplementedError
    AR = 'llvm-ar'
    AS = 'llvm-as'
    # LD = 'ld.lld'
    LD = '{}-clang'.format(target)
    LDFLAGS.append('-fuse-ld=lld')
    RANLIB = 'llvm-ranlib'
    READELF = 'llvm-readelf'
toolchain = os.path.realpath(toolchain)
sysroot = os.path.join(toolchain, 'sysroot')
assert os.path.exists(sysroot), sysroot

CC = '{}-clang'.format(target)
CPP = '{} -E'.format(CC)
CXX = '{}-clang++'.format(target)
CFLAGS.append('--target={}'.format(target))
CFLAGS.append('-march={}'.format(march))
CFLAGS.append('-mtune=generic')
CFLAGS.append('-mfloat-abi=softfp')
CFLAGS.append('--sysroot={}'.format(sysroot))
CPPFLAGS.append('-D__ANDROID_API__={}'.format(api))
CPPFLAGS.append('-isysroot {}'.format(sysroot))
CPPFLAGS.append('-isystem {}'.format(
    os.path.join(sysroot, 'usr', 'include', triplet)
))
CXXFLAGS = CFLAGS

CFLAGS = ' '.join(CFLAGS)
CPPFLAGS = ' '.join(CPPFLAGS)
CXXFLAGS = ' '.join(CXXFLAGS)
LDFLAGS = ' '.join(LDFLAGS)

PATH = os.environ.get('PATH', '').split(os.pathsep)
PATH.append(os.path.join(toolchain, 'bin'))
PATH.append(os.path.join(toolchain, triplet, 'bin'))
PATH = os.pathsep.join(PATH)

os.environ.update({'ABI': abi})
os.environ.update({'API': api})
os.environ.update({'TARGET': target})
os.environ.update({'AR': AR})
os.environ.update({'AS': AS})
os.environ.update({'CC': CC})
os.environ.update({'CPP': CPP})
os.environ.update({'CXX': CXX})
os.environ.update({'LD': LD})
os.environ.update({'RANLIB': RANLIB})
os.environ.update({'READELF': READELF})
os.environ.update({'CFLAGS': CFLAGS})
os.environ.update({'CPPFLAGS': CPPFLAGS})
os.environ.update({'CXXFLAGS': CXXFLAGS})
os.environ.update({'LDFLAGS': LDFLAGS})
os.environ.update({'PATH': PATH})

# Python setuptools
os.environ.update({'LDSHARED': '{} -shared'.format(LD)})
os.environ.update({'_PYTHON_HOST_PLATFORM': platform.system().lower()})


if __name__ == '__main__':

    if len(sys.argv) > 1:

        if sys.argv[1].endswith('.py'):
            os.execv(sys.executable, [sys.executable] + sys.argv[1:])
        else:
            os.execvp(sys.argv[1], sys.argv[1:])

    else:

        def p(x):
            if x in os.environ:
                print('export {}="{}"'.format(x, os.environ[x]))

        vars = (
            'ABI',
            'API',
            'AR',
            'AS',
            'CC',
            'CFLAGS',
            'CPP',
            'CPPFLAGS',
            'CXX',
            'CXXFLAGS',
            'LD',
            'LDFLAGS',
            'PATH',
            'RANLIB',
            'TARGET',
        )
        for var in vars:
            p(var)
