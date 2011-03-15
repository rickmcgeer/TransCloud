#!/usr/local/pig/bin/pig

/*
	Sum the results from other clusters(aka Combiner)
	Chris Pearson - pearson@cs.uvic.ca
	
	
	This takes the results from other nodes and sums them together.
	It is the "third cluster" in the transcontinental experiment.
*/

--    hadoop dfs -cat results/combined/total_traffic/part-r-00000; hadoop dfs -cat results/combined/total_known_traffic/part-r-00000; hadoop dfs -cat results/combined/total_traffic_per_known_protocol/part-r-00000;hadoop dfs -cat results/combined/traffic_percent_per_protocol/part-m-00000;hadoop dfs -cat results/combined/known_traffic_percent_per_protocol/part-m-00000




-- Load the total traffic amounts and sum them
A = LOAD 'hdfs://opencirrus-01101.hpl.hp.com:54310/user/hadoop/results/geni/total_traffic/part-r-00000' USING PigStorage('\t') AS (title:chararray, total:double);

B = LOAD 'hdfs://131.246.112.35:54310/user/hadoop/results/geni/total_traffic/part-r-00000' USING PigStorage('\t') AS (title:chararray, total:double);

-- Combine the above two together to for counting
C = UNION A,B;
D = GROUP C BY title; -- group by port name
E = FOREACH D GENERATE group, SUM(C.total) AS total_traffic:double; -- count total packet lengths for each port name
STORE E INTO 'results/geni-combine/total_traffic';
-- DUMP E;



-- Load the list of protocols / services and the total packet sizes
F = LOAD 'hdfs://opencirrus-01101.hpl.hp.com:54310/user/hadoop/results/geni/total_traffic_per_known_protocol/part-r-00000' USING PigStorage('\t') AS (protocol:chararray, protocol_total:double);

G = LOAD 'hdfs://131.246.112.35:54310/user/hadoop/results/geni/total_traffic_per_known_protocol/part-r-00000' USING PigStorage('\t') AS (protocol:chararray, protocol_total:double);

-- Combine the above two together to for counting
H = UNION F,G;
I = GROUP H BY protocol; -- group by port name
J = FOREACH I GENERATE group, SUM(H.protocol_total) AS protocol_total:double; -- count total packet lengths for each port name
STORE J INTO 'results/geni-combine/total_traffic_per_known_protocol';
-- DUMP J;




-- Calculate the percent of total traffic for each protocol
K = FOREACH J GENERATE group, (protocol_total / E.total_traffic) * 100 AS percent:double;
STORE K INTO 'results/geni-combine/traffic_percent_per_protocol';
-- DUMP K;



-- Load the total known traffic results
L = LOAD 'hdfs://opencirrus-01101.hpl.hp.com:54310/user/hadoop/results/geni/total_known_traffic/part-r-00000' USING PigStorage('\t') AS (title:chararray, total_known_traffic:double);

M = LOAD 'hdfs://131.246.112.35:54310/user/hadoop/results/geni/total_known_traffic/part-r-00000' USING PigStorage('\t') AS (title:chararray, total_known_traffic:double);

N = UNION L,M;
O = GROUP N BY title; -- group by port name
P = FOREACH O GENERATE group, SUM(N.total_known_traffic) AS total_known_traffic:double;
STORE P INTO 'results/geni-combine/total_known_traffic';


-- Find the percent of known traffic made up by each protocol
Q = FOREACH J GENERATE group, (protocol_total / P.total_known_traffic) * 100 AS percent:double;
STORE Q INTO 'results/geni-combine/known_traffic_percent_per_protocol';
-- DUMP Q;
