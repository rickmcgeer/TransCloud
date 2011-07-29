#! /bin/bash

export PATH=/home/hadoop/jre1.6.0_24/bin/:/home/hadoop/hadoop/bin/:/home/hadoop/pig/bin/:$PATH
export JAVA_HOME=/home/hadoop/jre1.6.0_24/
export PIG_CLASSPATH=/home/hadoop/hadoop/conf/


hadoop dfs -rmr /user/hadoop/results/geni > /dev/null 2> /dev/null
pig /home/hadoop/geni/geni_process.pig

rm -rf /home/hadoop/geni/geni-results > /dev/null 2> /dev/null
hadoop dfs -copyToLocal /user/hadoop/results/geni/traffic_percent_per_protocol/part-m-00000 /home/hadoop/geni/geni-results
python /home/hadoop/geni/uploadPigResult.py

