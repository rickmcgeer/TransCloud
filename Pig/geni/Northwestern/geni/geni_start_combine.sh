#! /bin/bash

export PATH=/usr/local/pig/bin:/usr/local/hadoop/bin:$PATH
export JAVA_HOME=/usr/lib/jvm/java-6-sun
export PIG_CLASSPATH=/usr/local/hadoop/conf/

hadoop dfs -rmr /user/hadoop/results/geni-combine > /dev/null 2> /dev/null
/home/hadoop/geni/geni_combine.pig


rm -rf /home/hadoop/geni/geni-combine-results  > /dev/null 2> /dev/null
hadoop dfs -copyToLocal /user/hadoop/results/geni-combine/traffic_percent_per_protocol/part-m-00000 /home/hadoop/geni/geni-combine-results
python /home/hadoop/geni/uploadPigResult.py
