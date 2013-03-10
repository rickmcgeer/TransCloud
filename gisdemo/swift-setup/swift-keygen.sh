#! /bin/bash

# generates a key for a swift cluster to use.
#  This key must be in the file /etc/swift/swift.conf
#  and must be presenton and identical to
#  all nodes in the same swift cluster.

cat >/tmp/swift.conf <<EOF
[swift-hash]
# random unique string that can never change (DO NOT LOSE)
swift_hash_path_suffix = `od -t x8 -N 8 -A n </dev/random`
EOF
