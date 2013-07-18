
import gcswift


proxy = "http://165.124.51.144:8080/auth/v1.0"

try:
    ret = gcswift.do_swift_command(proxy, "list", "", 1)
    bucketlist = ret.communicate()[0].split()
except gcswift.SwiftFailure as e:
    print "failed to get list of existing buckets:", str(e)
    sys.exit()

for b in bucketlist:

    print b

    try:
        ret = gcswift.do_swift_command(proxy, "post --read-acl='.r:*,.rlistings' "+b, "", 1)
        bucketlist = ret.communicate()[0].split()
    except gcswift.SwiftFailure as e:
        print "failed to get list of existing buckets:", str(e)
        sys.exit()


# ret = gcswift.do_swift_command(proxy, "list -p p0", "", 1)
# imgsfromdb = ret.communicate()[0].split()
    
# ret = gcswift.do_swift_command(proxy, "list -p p1", "", 1)
# imgsfromdb += ret.communicate()[0].split()

# ret = gcswift.do_swift_command(proxy, "list -p p2", "", 1)
# imgsfromdb += ret.communicate()[0].split()
