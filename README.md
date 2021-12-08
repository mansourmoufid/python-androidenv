Build native packages for Android.


## Requirements

 - Python;
 - Android SDK;

The Android SDK can be installed from [Android Studio][].

Then set the environment variable [ANDROID_SDK_ROOT][] or ANDROID_HOME.

Finally, Python's [distutils][] package must be patched for cross-compiling.
The patch is in the patches directory.  Apply it like so:

    DESTLIB=$(python -c "import sysconfig; \
        print(sysconfig.get_config_var('DESTLIB'))")
    patch -p2 -d $DESTLIB < patches/patch-Python-3.10.0.txt

This patch should apply to any version of Python.

You may need to use sudo.


[Android Studio]: https://developer.android.com/studio/
[ANDROID_SDK_ROOT]: https://developer.android.com/studio/command-line/variables
[distutils]: https://docs.python.org/3/library/distutils.html


## Install androidenv

Install from the Python Package Index:

    pip install androidenv

You can also copy the file androidenv.py to where you need it,
it is self contained.


## Usage

Build something from source:

    cd thing
    python -m androidenv setup.py build
    python -m androidenv setup.py install

You really want to do this in a [virtual environment][venv].


[venv]: https://docs.python.org/3/library/venv.html


## Environment variables

This module works entirely with environment variables.

Input environment variables:

 - ANDROID_SDK_ROOT or ANDROID_HOME (required);
 - ABI (optional; armeabi-v7a or arm64-v8a);
 - API (optional);
 - DEBUG (optional; 0 or 1);

What is being built must respect the following evironment variables:

 - AR
 - AS
 - CC
 - CFLAGS
 - CPP
 - CPPFLAGS
 - CXX
 - CXXFLAGS
 - LD
 - LDFLAGS
 - PATH
 - RANLIB
 - READELF

Many packages do, many don't.  Python itself (distutils) does not respect
RANLIB; CMake does not respect CPPFLAGS; and many more.  Fixing that is
your homework.

### setup.cfg

Some useful configuration options when building for Android:

    [build]
    build-base = build
    build-temp = build/tmp
    build-lib = build/lib


## Examples

### NumPy

    test -d "$ANDROID_SDK_ROOT" || echo "uhoh"
    curl -L -O https://files.pythonhosted.org/packages/source/n/numpy/numpy-1.19.5.zip
    unzip numpy-1.19.5.zip
    cd numpy-1.19.5
    export BLAS=None LAPACK=None ATLAS=None
    ABI=arm64-v8a API=24 python -m androidenv setup.py build
    ABI=arm64-v8a API=24 python -m androidenv setup.py install
