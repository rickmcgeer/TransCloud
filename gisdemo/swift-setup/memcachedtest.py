import swift.common.memcached as memc
from getmyip import *


def test_memcached():
    ip = getmyip()

    m = memc.MemcacheRing([ip+':11211'])
    token = m.get('AUTH_/user/system:gis')

    print "XAuthToken:", token
    print "", m.get("AUTH_/token/" + str(token))


if __name__ == "__main__":
    test_memcached()
