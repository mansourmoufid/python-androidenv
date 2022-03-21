'''Build native packages for Android'''

import os
import platform
import re
import subprocess
import sys


__author__ = 'Mansour Moufid'
__copyright__ = 'Copyright 2021, 2022, Mansour Moufid'
__license__ = 'ISC'
__version__ = '0.8'
__email__ = 'mansourmoufid@gmail.com'
__status__ = 'Development'


abi = os.environ.get('ABI', 'arm64-v8a')
assert abi in ['armeabi-v7a', 'arm64-v8a', 'x86', 'x86_64'], abi
if abi == 'armeabi-v7a':
    arch = 'arm'
    march = 'armv7-a'
    triplet = 'arm-linux-androideabi'
elif abi == 'arm64-v8a':
    arch = 'arm64'
    march = 'armv8-a'
    triplet = 'aarch64-linux-android'
elif abi == 'x86':
    arch = 'x86'
    march = 'i686'
    triplet = 'i686-linux-android'
elif abi == 'x86_64':
    arch = 'x86_64'
    march = 'x86-64'
    triplet = 'x86_64-linux-android'

if abi in ('arm64-v8a', 'x86_64'):
    api = os.environ.get('API', '21')
else:
    api = os.environ.get('API', '19')

assert 'ANDROID_SDK_ROOT' in os.environ or 'ANDROID_HOME' in os.environ
sdk = os.environ.get('ANDROID_SDK_ROOT', None)
if sdk is None:
    home = os.environ.get('ANDROID_HOME', None)
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
    '-pie',
]


def splitescaped(xs):
    return re.split(r'(?<!\\) ', xs)


def search(exp, str):
    try:
        match = re.search(exp, str)
        if match:
            return match.group(0)
    except re.error:
        return str if exp == str else None
    return None


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
    elif abi == 'x86':
        target = 'i686-linux-android{}'.format(api)
    elif abi == 'x86_64':
        target = 'x86_64-linux-android{}'.format(api)
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

# distutils.command.build_ext.compiler.find_library_file
libdirs = [
    os.path.join(sysroot, 'usr', 'lib64'),
    os.path.join(sysroot, 'usr', 'lib'),
    os.path.join(sysroot, 'usr', 'lib', triplet, api),
]
for dir in libdirs:
    if os.path.exists(dir):
        LDFLAGS.append('-L{}'.format(dir))

CC = '{}-clang'.format(target)
CPP = '{} -E'.format(CC)
CXX = '{}-clang++'.format(target)
CFLAGS.append('--target={}'.format(target))
LDFLAGS.append('--target={}'.format(target))
CFLAGS.append('-march={}'.format(march))
CFLAGS.append('-mtune=generic')
if abi == 'armeabi-v7a':
    CFLAGS += ['-mfloat-abi=softfp', '-mfpu=vfpv3']
    LDFLAGS.append('-Wl,--fix-cortex-a8')
elif abi == 'arm64-v8a':
    CFLAGS.append('-mfpu=neon')
elif abi == 'x86':
    CFLAGS += ['-m32', '-mfpmath=sse', '-mssse3']
elif abi == 'x86_64':
    CFLAGS += ['-m64', '-mfpmath=sse', '-msse4.2']
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

if 'ANDROID_SDK_ROOT' not in os.environ:
    os.environ.update({'ANDROID_SDK_ROOT': sdk})
os.environ.update({'ABI': abi})
os.environ.update({'API': api})
os.environ.update({'TARGET': triplet})
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


def find(dirs, name):
    for dir in dirs:
        for root, _, files in os.walk(dir, topdown=False):
            for filename in files:
                match = search(name, filename)
                if match:
                    yield os.path.join(root, filename)
                    return


def find_library(name):
    dirs = [
        os.path.join(sysroot, 'usr', 'lib', triplet, api),
        os.path.join(sysroot, 'usr', 'lib', triplet),
        sysroot,
    ]
    if not name.startswith('lib'):
        name = 'lib' + name
    if not name.endswith('.so'):
        name = name + '.so'
    return find(dirs, name)


if __name__ == '__main__':

    if len(sys.argv) > 1:

        if sys.argv[1] == '--find-library':
            for lib in sys.argv[2:]:
                for path in find_library(lib):
                    print(path)
        elif sys.argv[1].endswith('.py'):
            os.execv(sys.executable, [sys.executable] + sys.argv[1:])
        else:
            os.execvp(sys.argv[1], sys.argv[1:])

    else:

        def p(x):
            if x in os.environ:
                print('export {}="{}"'.format(x, os.environ[x]))

        vars = (
            '_PYTHON_HOST_PLATFORM',
            'ABI',
            'ANDROID_SDK_ROOT',
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
            'LDSHARED',
            'PATH',
            'RANLIB',
            'READELF',
            'TARGET',
        )
        for var in vars:
            p(var)
