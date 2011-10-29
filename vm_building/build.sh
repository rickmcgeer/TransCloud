#!/bin/bash

vmbuilder xen ubuntu \
--suite lucid \
--flavour server \
--part ./partitions \
--arch amd64 \
--overwrite \
--rootpass=QYummXMoiRkC04etHVJNp4cqn \
--addpkg unattended-upgrades \
--addpkg acpid \
--addpkg openssh-server \
--addpkg wget

