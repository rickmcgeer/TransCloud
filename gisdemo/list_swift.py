import subprocess

command = ["swift", "-A",
           "https://swift.gcgis.trans-cloud.net:8080/auth/v1.0",
           "-U",
           "system:gis",
           "-K",
           "uvicgis"]
containers = list(command)
containers.append("list")
p = subprocess.Popen(containers, stdout=subprocess.PIPE)
p.wait()
out, err = p.communicate()
print out,err

to_crawl = []
for line in out.split("\n"):
    if line[0] == "p":
        print line
        new_command = list(containers)
        new_command.append(line)
        p = subprocess.Popen(new_command, stdout=subprocess.PIPE)
        p.wait()
        out, err = p.communicate()
        print out
        all_files =  out.split("\n"):
        to_crawl.append((line, all_files[0], all_files))

print to_crawl
to_crawl[:] = [f for f in to_crawl if f != ""]

for files in to_crawl:
    
    download_command = list(command)
    download_command.append("download")
    download_command.append(files[0])
    download_command.append(files[1])
    rest = files[2]
    for rest:
        insert into DB
    print download_command
    #p = subprocess.Popen(new_command, stdout=subprocess.PIPE)
    #out, err = p.communicate()
            



