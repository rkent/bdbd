#!/usr/bin/env bash

source /home/kent/github/rkent/bdbd/devel/setup.bash
export ROSCONSOLE_FORMAT='[${severity}] [${time}]: ${node}: ${message}'
export ROS_MASTER_URI=http://nano.dryrain.org:11311/
exec "$@"