#! /bin/bash

export PATH=/usr/local/pig/bin:/usr/local/hadoop/bin:$PATH
export JAVA_HOME=/usr/lib/jvm/java-6-sun
export PIG_CLASSPATH=/usr/local/hadoop/conf/

hadoop dfs -rmr /user/hadoop/results/combined > /dev/null 2> /dev/null
/home/hadoop/pig_test_combined.pig

