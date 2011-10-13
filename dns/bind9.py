#write out new zone db
import subprocess
import time
template = """
;
; BIND data file for local loopback interface
;
$TTL	604800
@	IN	SOA	ns.genicloud.trans-cloud.net. root.genicloud.trans-cloud.net. (
			%d		; Serial
			604800		; Refresh
			86400		; Retry
			2419200		; Expire
			604800 )	; Negative Cache TTL
;
@	IN	NS	localhost.
@	IN	A	50.92.210.3
@	IN	AAAA	::1
test	IN	A	1.2.3.4
foo.bar	IN	CNAME	test
"""

def make_string(mappings):
    s = template%(time.time())
    for host in mappings:
        s = s + "%s\tIN\tA\t%s\n"%(host[0],host[1])
    return s
def write_out(mapping):
    s = make_string(mapping)
    try:
        f = open("/etc/bind/db.genicloud.trans-cloud.net", "w")
        f.write(s)
        f.close()
    except:
        print "failed to write the zones database"
        return
    #try:
    rc = subprocess.call(["/usr/sbin/rndc","reload"])
    #except e:
    #    print "failed reloading zonedb", str(e)
    #    return

if __name__ == "__main__":
    mappings = [("test3","3.4.5.6"),("test4","3.4.5.7"),("test5","3.4.5.8"),]
    write_out(mappings)
    print "done."
