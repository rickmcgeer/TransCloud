#!/usr/local/pig/bin/pig

/*
	Traffic at Known Ports (aka pig_test.pig)
	Chris Pearson - pearson@cs.uvic.ca
	
	
	A test to calculate the total packet sizes for known ports (as 
	known by an edited Linux /etc/services file), and calculate
	the percent of the total traffic.
*/


-- Delete command:
--    hadoop dfs -rmr results/pig_test

-- Dump the files to the console.
-- *** NOTE: using the Pig DUMP command significantly increases the runtime
-- as it forces Pig run the statements leading to a DUMP separately.
-- Essentially, it runs a new Pig job for each DUMP statement in the code. 
-- Importantly, this means that the start/end times it gives are for a 
-- particular part of the total job and NOT for the complete job, as would
-- be the case is only STORE was used.
--    hadoop dfs -cat results/pig_test/total_traffic/part-r-00000; hadoop dfs -cat results/pig_test/total_known_traffic/part-r-00000; hadoop dfs -cat results/pig_test/total_traffic_per_known_protocol/part-r-00000;hadoop dfs -cat results/pig_test/traffic_percent_per_protocol/part-m-00000

-- Runtime with 94MB umass1.txt:  1:54
-- Runtime with ~1GB umass1_cat.txt:  4:56
-- Runtime with ~1GB umass1_cat.txt with DUMP statements: 12:07

-- Runtime at northwestern with 94MB umass1.txt:  2:45
-- Runtime at northwestern with ~1GB umass1_cat.txt:  7:12

-- Runtime at germany with 94MB umass1.txt:  2:38
-- Runtime at germany with ~1GB umass1_cat.txt:  4:11

A = LOAD 'data/umass1_100.txt' USING PigStorage('\t') AS (timestamp:double, record_ip_tlen:double, record_ip_id:int, record_ip_ttl:int, record_ip_protocol:int, protocol:chararray, record_ip_src:long, record_ip_dest:long, source_ip:chararray, dest_ip:chararray, source_port:int, dest_port:int, record_tcp_seqno:long, record_tcp_ackno:long, flag1:int, flag2:int, flag3:int, record_tcp_win:int);

B = LOAD 'data/services-list.txt' USING PigStorage('\t') AS (protocol_nameB:chararray, portB:int, protocolB:chararray);

-- Calculate the total packet lengths for all data
D = FOREACH A GENERATE source_ip, dest_ip, protocol, source_port, dest_port, record_ip_tlen;
D1 = GROUP D ALL;
D2 = FOREACH D1 GENERATE group, SUM(D.record_ip_tlen) AS total_lengths:double;
STORE D2 INTO 'results/pig_test/total_traffic';
-- DUMP D2;
-- ILLUSTRATE D2;


-- I'm assuming we only care about port numbers less than 10000. This allows
-- for the splitting of the input file early. Without this there is potential
-- for the same packet to be counted more than once below. (Rarely, but there
-- are examples of it.)
SPLIT A INTO E IF (dest_port <= 10000),
	F IF ((dest_port > 10000) AND (source_port <= 10000));

-- Add port names to matching source ports. Throws away non-matches.
G = JOIN E BY (protocol, source_port), B BY (protocolB, portB);
-- Add port names to matching destination ports. Throws away non-matches.
H = JOIN F BY (protocol, dest_port), B BY (protocolB, portB);

-- Combine the above two together to for counting
I = UNION G,H;
J = GROUP I BY protocol_nameB; -- group by port name
K = FOREACH J GENERATE group, SUM(I.record_ip_tlen) AS protocol_total:double; -- count total packet lengths for each port name
STORE K INTO 'results/pig_test/total_traffic_per_known_protocol';
-- DUMP K;

-- Summing through an entire file requires that it be made into
-- one big group. So, group it and sum that group.
L = GROUP K ALL;
M = FOREACH L GENERATE group, SUM(K.protocol_total) AS known_total:double;
STORE M INTO 'results/pig_test/total_known_traffic';
-- DUMP M;

-- Same as above, but output as the percent of total packet lengths 
N = FOREACH K GENERATE group, (protocol_total / D2.total_lengths) * 100 AS percent:double;
STORE N INTO 'results/pig_test/traffic_percent_per_protocol';
-- DUMP N;


