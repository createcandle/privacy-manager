#!/bin/bash -e

#python3 -m pip install --upgrade pip==21.3.1

export PYTHONIOENCODING=utf8

version=$(grep '"version"' manifest.json | cut -d: -f2 | cut -d\" -f2)

# Setup environment for building inside Dockerized toolchain
[ $(id -u) = 0 ] && umask 0

# Clean up from previous releases
echo "removing old files"
rm -rf *.tgz *.sha256sum package SHA256SUMS lib

if [ -z "${ADDON_ARCH}" ]; then
  TARFILE_SUFFIX=
else
  PYTHON_VERSION="$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d. -f 1-2)"
  TARFILE_SUFFIX="-${ADDON_ARCH}-v${PYTHON_VERSION}"
fi


# Prep new package
echo "creating package"
mkdir -p lib package

# Pull down Python dependencies
#CFLAGS="--disable-jpeg" pip3 install Pillow -t lib --no-binary :all: --prefix ""
python3 -m pip install --upgrade requests --no-dependencies -t lib --no-binary :all: --prefix ""
python3 -m pip install --upgrade cairosvg --no-dependencies -t lib --no-binary :all: --prefix ""
#python3 -m pip install --upgrade Pillow -t lib --no-binary :all: --prefix "" --global-option="build_ext" --global-option="--disable-jpeg" # Candle has pillow pre-installed
python3 -m pip install --upgrade cairocffi -t lib --no-binary :all: --prefix ""
python3 -m pip install --upgrade flit -t lib --no-binary :all: --prefix ""
python3 -m pip install --upgrade cssselect2 -t lib --no-binary :all: --prefix ""
python3 -m pip install --upgrade defusedxml -t lib --no-binary :all: --prefix ""
python3 -m pip install --upgrade tinycss2 -t lib --no-binary :all: --prefix ""
python3 -m pip install --upgrade qrcode -t lib --no-binary :all: --prefix ""
python3 -m pip install --upgrade pygal -t lib --no-binary :all: --prefix ""
python3 -m pip install --upgrade ppa6 --no-dependencies -t lib --no-binary :all: --prefix ""
#python3 -m pip install --upgrade matplotlib==3.0.2 -t lib --no-binary :all: --prefix ""

#pip3 install -r requirements.txt -t lib --no-binary :all: --prefix ""
#pip3 install -r requirements2.txt -t lib --no-binary :all: --prefix ""

# Put package together
cp -r lib pkg LICENSE manifest.json *.py README.md css js views images package/
find package -type f -name '*.pyc' -delete
find package -type f -name '._*' -delete
find package -type d -empty -delete
rm -rf package/pkg/pycache

# Generate checksums
echo "generating checksums"
cd package
find . -type f \! -name SHA256SUMS -exec shasum --algorithm 256 {} \; >> SHA256SUMS
cd -

# Make the tarball
echo "creating archive"
TARFILE="privacy-manager-${version}${TARFILE_SUFFIX}.tgz"
tar czf ${TARFILE} package

echo "creating shasums"
shasum --algorithm 256 ${TARFILE} > ${TARFILE}.sha256sum
cat ${TARFILE}.sha256sum
#sha256sum ${TARFILE}
#rm -rf SHA256SUMS package

