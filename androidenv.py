'''Build native packages for Android'''

import os
import platform
import re
import subprocess
import sys


__author__ = 'Mansour Moufid'
__copyright__ = 'Copyright 2021, Mansour Moufid'
__license__ = 'ISC'
__version__ = '0.1'
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
    '-Wno-macro-redefined',
    '-Wno-unused-command-line-argument',
]
CPPFLAGS = []
LDFLAGS = []

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
    sysroot = os.path.join(ndk, 'sysroot')
    assert os.path.exists(sysroot)
    target = triplet
    toolchain = '{}-{}-toolchain'.format(target, api)
    if not os.path.exists(toolchain):
        subprocess.run([
            os.path.join(ndk, 'build/tools/make_standalone_toolchain.py'),
            '--arch', arch,
            '--api', api,
            '--install-dir={}'.format(toolchain),
        ])
    assert os.path.exists(toolchain), toolchain
    AR = '{}-ar'.format(target)
    AS = '{}-clang'.format(target)
    LD = '{}-ld'.format(target)
    RANLIB = '{}-ranlib'.format(target)
else:
    host = '{}-{}'.format(platform.system(), platform.machine()).lower()
    if host == 'darwin-arm64':
        host = 'darwin-x86_64'
    toolchain = os.path.join(ndk, 'toolchains/llvm/prebuilt', host)
    if not os.path.exists(toolchain):
        toolchain = os.path.join(
            ndk,
            '.'.join(str(x) for x in ndk_version),
            'toolchains/llvm/prebuilt',
            host
        )
    assert os.path.exists(toolchain), toolchain
    sysroot = os.path.join(toolchain, 'sysroot')
    assert os.path.exists(sysroot)
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
    LDFLAGS.append('-L{}/usr/lib/{}'.format(sysroot, triplet))
    LDFLAGS.append('-L{}/usr/lib/{}/{}'.format(sysroot, triplet, api))
toolchain = os.path.realpath(toolchain)

CC = '{}-clang'.format(target)
CPP = '{} -E'.format(CC)
CXX = '{}-clang++'.format(target)
CFLAGS.append('--sysroot={}'.format(sysroot))
CFLAGS.append('--target={}'.format(target))
CFLAGS.append('-fpic')
CFLAGS.append('-march={}'.format(march))
CFLAGS.append('-mtune=generic')
CFLAGS.append('-mfloat-abi=softfp')
CPPFLAGS.append('-D__ANDROID_API__={}'.format(api))
CPPFLAGS.append('-isysroot {}'.format(sysroot))
CPPFLAGS.append('-isystem {}/usr/include/{}'.format(sysroot, triplet))
CXXFLAGS = CFLAGS
ldsysroot = '{}/platforms/android-{}/arch-{}'.format(ndk, api, arch)
LDFLAGS.append('--sysroot={}'.format(ldsysroot))

CFLAGS = ' '.join(CFLAGS)
CPPFLAGS = ' '.join(CPPFLAGS)
CXXFLAGS = ' '.join(CXXFLAGS)
LDFLAGS = ' '.join(LDFLAGS)

PATH = os.environ.get('PATH', '').split(os.pathsep)
PATH.insert(0, '{}/bin'.format(toolchain))
PATH.insert(0, '{}/{}/bin'.format(toolchain, triplet))
PATH = os.pathsep.join(PATH)

os.environ.update({'ABI': abi})
os.environ.update({'ANDROIDLDSYSROOT': ldsysroot})
os.environ.update({'ANDROIDSYSROOT': sysroot})
os.environ.update({'TARGET': target})
os.environ.update({'AR': AR})
os.environ.update({'AS': AS})
os.environ.update({'CC': CC})
os.environ.update({'CPP': CPP})
os.environ.update({'CXX': CXX})
os.environ.update({'LD': LD})
os.environ.update({'RANLIB': RANLIB})
os.environ.update({'CFLAGS': CFLAGS})
os.environ.update({'CPPFLAGS': CPPFLAGS})
os.environ.update({'CXXFLAGS': CXXFLAGS})
os.environ.update({'LDFLAGS': LDFLAGS})
os.environ.update({'PATH': PATH})

# Python setuptools
os.environ.update({'LDSHARED': '{} -shared'.format(LD)})
os.environ.update({'_PYTHON_HOST_PLATFORM': platform.system().lower()})


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1].endswith('.py'):
        os.execv(sys.executable, [sys.executable] + sys.argv[1:])
    else:
        os.execvp(sys.argv[1], sys.argv[1:])