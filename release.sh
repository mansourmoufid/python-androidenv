#!/bin/sh
set -e
set -x
v="$1"
rm -rf "androidenv-${v}"
mkdir "androidenv-${v}"
cp androidenv.py "androidenv-${v}/"
cp setup.py "androidenv-${v}/"
cp LICENSE.txt "androidenv-${v}/"
cp README.md "androidenv-${v}/"
cp MANIFEST.in "androidenv-${v}/"
cp -r patches "androidenv-${v}/"
rm -f "androidenv-${v}.tar"
tar -c -f "androidenv-${v}.tar" --format ustar "androidenv-${v}"
rm -f "androidenv-${v}.tar.gz"
gzip "androidenv-${v}.tar"
rm -rf "androidenv-${v}"
