import TCSendData

output = ""
first = True
file = open('/home/hadoop/geni/geni-process-results','r')
for line in file:
    if first == True:
        first = False
    else:
        output += ","
    line_split = line.split('\t')
    output += line_split[0] + ":" + line_split[1].strip()

print output

params = {'name': 'Processing1B', 'entries':output}
TCSendData.http_send('/jobs/api/add_batch_hadoop_result/', params, 'pigLog.log')
