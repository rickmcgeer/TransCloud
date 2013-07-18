#! /usr/bin/env bash


if [ -z $1 ]; then
	fab all
else
	fab all:$1
fi