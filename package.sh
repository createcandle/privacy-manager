#!/bin/bash

version=$(grep '"version":' manifest.json | cut -d: -f2 | cut -d\" -f2)

rm -rf SHA256SUMS package
rm -rf ._*
mkdir package
cp *.py manifest.json LICENSE README.md package/
cp -r pkg css images js views package/
cd package
find . -type f \! -name SHA256SUMS -exec sha256sum {} \; >> SHA256SUMS
cd ..

tar czf "privacy-manager-${version}.tgz" package
sha256sum "privacy-manager-${version}.tgz"
