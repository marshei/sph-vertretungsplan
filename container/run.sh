#!/usr/bin/env bash

SCRIPT_HOME="$(dirname $(readlink -f $0))"

/usr/libexec/platform-python "${SCRIPT_HOME}"/sph_vertretung.py $@
