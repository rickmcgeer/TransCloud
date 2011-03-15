#! /bin/bash

export PATH=/usr/local/pig/bin:/usr/local/hadoop/bin:$PATH
export JAVA_HOME=/usr/lib/jvm/java-6-sun
export PIG_CLASSPATH=/usr/local/hadoop/conf/

hadoop dfs -rmr /user/hadoop/results/geni > /dev/null 2> /dev/null
/home/hadoop/geni/geni_process_hp.pig

rm -rf /home/hadoop/geni/geni-results  > /dev/null 2> /dev/null
hadoop dfs -copyToLocal /user/hadoop/results/geni/traffic_percent_per_protocol/part-r-00000 /home/hadoop/geni/geni-results
python /home/hadoop/geni/uploadPigResult.py

