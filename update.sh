#!/bin/sh
echo 'updating git submodules..'
git submodule update --remote

echo 'building tools..'
find . -maxdepth 2 -name update -type f -exec sh -c "echo running '{}' && '{}'" \;
