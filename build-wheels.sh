#!/bin/bash

set -e -u -x

PLAT=$1

function repair_wheel {
    wheel="$1"
    if ! auditwheel show "$wheel"; then
        echo "Skipping non-platform wheel $wheel"
    else
        auditwheel repair "$wheel" --plat "$PLAT" -w /io/wheelhouse/
    fi
}


# Install a system package required by our library
if [ -f /etc/redhat-release ] ; then
	# CenOS image
	yum install -y alsa-lib-devel libffi-devel
else
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
for PYBIN in /opt/python/cp{37,38,39}*/bin; do
    "${PYBIN}/pip" install -r /io/requirements.txt
    "${PYBIN}/pip" wheel /io/ --no-deps -w wheelhouse/
done

# Bundle external shared libraries into the wheels
for whl in wheelhouse/*.whl; do
    repair_wheel "$whl"
done

# Install packages and test
cd /
for PYBIN in /opt/python/cp{37,38,39}*/bin/; do
    "${PYBIN}/pip" install pytest pytest-asyncio
    "${PYBIN}/pip" install python-alsa-midi --no-index -f /io/wheelhouse
    "${PYBIN}/python" -m pytest -vv /io/tests
done
