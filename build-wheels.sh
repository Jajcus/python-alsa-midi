#!/bin/bash

set -e -u -x

PLAT=$1

function repair_wheel {
    wheel="$1"
    if ! auditwheel show "$wheel"; then
        echo "Skipping non-platform wheel $wheel"
    else
        auditwheel repair "$wheel" --plat "$PLAT" -w "$GITHUB_WORKSPACE/wheelhouse/"
    fi
}

function rename_wheel {
    # bundling libasound.so.2 won't work but the ABI should be stable enough
    # to satisfy PEP600: "This tag is a promise: the wheel's creator promises
    # that the wheel will work on any mainstream Linux distro that uses glibc
    # version ${GLIBCMAJOR}.${GLIBCMINOR} or later"

    wheel="$1"

    filename="$(basename "$wheel")"
    prefix="${filename%-linux_*.whl}"
    if [ "$prefix" = "$wheel" ] ; then
        echo "Skipping non-platform wheel $wheel"
	return
    fi
    suffix="${filename##$prefix}"

    cp "$wheel" wheelhouse/"${prefix}-$PLAT.whl"
}



# Install a system package required by our library
if [ -f /etc/redhat-release ] ; then
	# CenOS image
	yum install -y alsa-lib-devel libffi-devel
else
	ID=""
	ID_LIKE=""
	. /etc/os-release

	if [ "$ID" = "debian" -o "$ID_LIKE" = "debian" ] ; then
		apt update
		apt install -y libasound-dev libffi-dev
	else
		echo "Unsupported OS: $ID"
		exit 1
	fi
fi

# Compile wheels
for PYBIN in /opt/python/cp{37,38,39,310}*/bin; do
    [ -d "$PYBIN" ] || continue
    "${PYBIN}/pip" install --upgrade pip setuptools
    "${PYBIN}/pip" install -r "$GITHUB_WORKSPACE/requirements.txt"

    pwd
    ls -la
    git status
    git tag -l
    git describe

    "${PYBIN}/pip" wheel "$GITHUB_WORKSPACE" --no-deps -w wheelhouse/
done

# Was: Bundle external shared libraries into the wheels-
# Now: change platform tag
for whl in wheelhouse/*.whl; do
    rename_wheel "$whl"
done

# remove 'bad' linux_* wheels
rm wheelhouse/*-linux_*.whl

# Install packages and test
cd /
for PYBIN in /opt/python/cp{37,38,39,310}*/bin/; do
    [ -d "$PYBIN" ] || continue

    "${PYBIN}/pip" install pytest pytest-asyncio
    "${PYBIN}/pip" install alsa-midi --no-index -f "$GITHUB_WORKSPACE/wheelhouse/"
    "${PYBIN}/python" -m pytest -vv "$GITHUB_WORKSPACE/tests"
done
