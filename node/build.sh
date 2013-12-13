#!/bin/bash

#################################################################
#################################################################
## CONFIG
#################################################################
#################################################################

WORK_DIRECTORY=/home/omnibot/omni
REVIEW_HOST=gerrit.omnirom.org
REVIEW_PORT=29418


#################################################################
#################################################################
# Actual script
#################################################################
#################################################################

if [[ $# != 2 ]]; then
        echo "Usage: ./build.sh <id> <ref>"
        exit 1
fi

echo =====
echo "Script starting build $1 (patch set $2)"
echo =====

# Go into the work directory
cd $WORK_DIRECTORY

echo In work directory $WORK_DIRECTORY

# Sync the sources
#repo forall -j12 -c "git reset --hard"
repo sync -j12 -d

echo Done repo sync.

# Prepare the build env
. build/envsetup.sh

# Pick our patch
repopick -c $1

# Test the build env
. build/envsetup.sh >/tmp/envsetup_$1.log 2>&1

if [[$? != 0]]; then
	LOG_URL=$(curl -d private=1 -d name=OmniBot --data-urlencode text@/tmp/envsetup_$1.log http://paste.omnirom.org/api/create)
	ssh -p $REVIEW_PORT $REVIEW_HOST gerrit review --message="'This is a message from OmniBot automated verifier. This patch breaks envsetup.sh. See $LOG_URL'" --verified=-1 $1,$2
	exit
fi

# Test Syncing
repo sync -j12 -d >/tmp/sync_$1.log 2>&1

if [[$? != 0]]; then
	LOG_URL=$(curl -d private=1 -d name=OmniBot --data-urlencode text@/tmp/sync_$1.log http://paste.omnirom.org/api/create)
	ssh -p $REVIEW_PORT $REVIEW_HOST gerrit review --message="'This is a message from OmniBot automated verifier. This patch breaks syncing. See $LOG_URL'" --verified=-1 $1,$2
	exit
fi

# Try to build a safe device, e.g. hammerhead

# TODO: Detect if it's a device-specific
# change and build that device.

# TODO: Build another device to make sure
# it isn't breaking tablets for instance.
rm -f /tmp/build_$1.log
lunch omni_hammerhead-userdebug
mka otapackage >/tmp/build_$1.log 2>&1

if [[ $? == 0 ]]; then
        ssh -p $REVIEW_PORT $REVIEW_HOST gerrit review --message="'This is a message from OmniBot automated verifier. This patch builds fine in the tree.'" --verified=+1 $1,$2
else
        # Upload the log
        LOG_URL=$(curl -d private=1 -d name=OmniBot --data-urlencode text@/tmp/build_$1.log http://paste.omnirom.org/api/create)
        ssh -p $REVIEW_PORT $REVIEW_HOST gerrit review --message="'This is a message from OmniBot automated verifier. This patch does NOT build in the tree! See '$LOG_URL" --verified=-1 $1,$2
fi

