#!/bin/sh

set -e
set -x

dir="$(cd $(dirname $0) && pwd)"
TARGET="$(python -m androidenv /bin/sh -c 'echo ${TARGET}')"
export DESTDIR="${dir}/build/${TARGET}"
export PREFIX="${PREFIX:=/usr}"

export API="${API:=21}"

PYTHON_VERSION="${PYTHON_VERSION:=3.7.11}"
PYTHON_VERSION_XY="$(echo ${PYTHON_VERSION} | awk -F. '{print $1 "." $2}')"
test -f ${DESTDIR}${PREFIX}/bin/python3 || (
    test -f Python-${PYTHON_VERSION}.tgz || \
        curl -O https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz
    test -d Python-${PYTHON_VERSION} || \
        gunzip < Python-${PYTHON_VERSION}.tgz | tar -f - -x
    (
        patch -f -p1 -d Python-${PYTHON_VERSION} < patches/patch-Python-3.10.0.txt
    ) || true
    cd Python-${PYTHON_VERSION}
    test -f configure.ac.orig || (
        cp configure.ac configure.ac.orig
        sed -e 's/ $host / "$host" /' -e 's/"$host"/"$build"/' \
            < configure.ac.orig \
            > configure.ac
        autoreconf -f -i
    )
    CC="${CC:=clang}"
    HOST="$(
        ${CC} ${CFLAGS} -dumpmachine \
        | sed -e 's/[0-9.]*$//' -e 's/arm64/aarch64/'
    )"
    python -m androidenv ./configure \
        --host=${HOST} \
        --build=${TARGET} \
        --enable-shared \
        --disable-ipv6 \
        --without-ensurepip \
        --without-pydebug \
        --without-pymalloc \
        --prefix="${PREFIX}" \
        ac_cv_file__dev_ptmx=no \
        ac_cv_file__dev_ptc=no
    python -m androidenv make python.exe
    mkdir -p "${DESTDIR}"
    DESTDIR="${DESTDIR}" python -m androidenv make install
    (
        find "${DESTDIR}" -name '*.pyc'
        find "${DESTDIR}" -name '__pycache__'
    ) | while read f; do rm -rf "${f}"; done
)

test -d "${DESTDIR}${PREFIX}/include/python${PYTHON_VERSION_XY}"
test -f "${DESTDIR}${PREFIX}/lib/libpython${PYTHON_VERSION_XY}.so"
export CPPFLAGS="-I${DESTDIR}${PREFIX}/include/python${PYTHON_VERSION_XY}"
export LDFLAGS="-L${DESTDIR}${PREFIX}/lib -lpython${PYTHON_VERSION_XY}"

NUMPY_VERSION="${NUMPY_VERSION:=1.20.3}"
test -d ${DESTDIR}${PREFIX}/lib/python${PYTHON_VERSION_XY}/site-packages/numpy || (
    test -f numpy-${NUMPY_VERSION}.zip || \
        curl -L -O https://github.com/numpy/numpy/releases/download/v${NUMPY_VERSION}/numpy-${NUMPY_VERSION}.zip
    rm -rf numpy-${NUMPY_VERSION}
    unzip numpy-${NUMPY_VERSION}.zip
    cd numpy-${NUMPY_VERSION}
    export BLAS=None LAPACK=None ATLAS=None
    test -f numpy/core/setup.py.orig || (
        cp numpy/core/setup.py numpy/core/setup.py.orig
        sed -e '/halffloat/d' < numpy/core/setup.py.orig > numpy/core/setup.py
    )
    python -m androidenv setup.py build
    python -m androidenv setup.py install \
        --prefix=${DESTDIR}${PREFIX} \
        --single-version-externally-managed \
        --record=install.txt
)
