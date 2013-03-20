import urllib2
# Simple MessageQueue access
    
# # Get package here: https://github.com/iron-io/iron_mq_python
# from iron_mq import *
 
# ironmq = IronMQ()
# # you can pass configuration data directly:
# # ironmq = IronMQ(
# #    token = "WhLXpdmOTjeihOiR27rzmSqy3Gw",
# #    project_id = "5112b9efd4297935a900204a"
# # )
 
# # Put a message on the queue
# ironmq.postMessage(queue_name="my_queue", messages=["Hello world"])
 
# # Get a message
# msgs = ironmq.getMessage(queue_name="my_queue")
# msg = msgs['messages'][0]
 
# # Delete the message
# ironmq.deleteMessage(queue_name="my_queue", message_id=msg["id"])
from iron_mq import *
import time

TEST_MESSAGE = "hello world" 

_ironmq=None

debug = True

def test_ironmq():
    """Test to make sure ironmq is working at all."""
     
    # you can pass configuration data directly:
    ironmq = IronMQ(token = "WhLXpdmOTjeihOiR27rzmSqy3Gw", project_id = "5112b9efd4297935a900204a")
 
    # Put a message on the queue
    ironmq.postMessage(queue_name="my_test_queue", messages=[TEST_MESSAGE])
 
    # Get a message
    msgs = ironmq.getMessage(queue_name="my_test_queue")
    msg = msgs['messages'][0]
    assert msg['body'] == TEST_MESSAGE
 
    # Delete the message
    ironmq.deleteMessage(queue_name="my_test_queue", message_id=msg["id"])

def setup():
    global _ironmq
    if _ironmq == None:
        _ironmq = IronMQ(token = "WhLXpdmOTjeihOiR27rzmSqy3Gw", project_id = "5112b9efd4297935a900204a")
    print "Info:", _ironmq.getQueues()

def push_job(message, queue, timeout=120):
    if debug:
        print "Pushing onto", queue, "message:", message
    _ironmq.postMessage(queue_name=queue, messages=[{'body': message, 'timeout': timeout}])

def get_job(queue):
    msgs = _ironmq.getMessage(queue_name=queue, max=1)
    if len(msgs['messages'])==0:
        if debug:
            print "No message were returned by ironmq on queue", queue, "max=",max
        return None, None
 
    msg = msgs['messages'][0]
    return msg['body'], msg["id"]


def done(queue, jobid):
    _ironmq.deleteMessage(queue_name=queue, message_id=jobid)


def clear_queue(queue):
    print "WARNING: cleaning queue", str(queue)
    try:
        _ironmq.clearQueue(queue_name=queue)
    except      :
        print "Warning: tried to clear a queue which does not exisit", queue


def sizeof(queue):
    return _ironmq.getQueueDetails(queue_name=queue)['size']

def all_queues():
    global _ironmq
    if _ironmq == None:
        _ironmq = IronMQ(token = "WhLXpdmOTjeihOiR27rzmSqy3Gw", project_id = "5112b9efd4297935a900204a")
    return _ironmq.getQueues()
    

def test_jobqueue():
    """Hook for the unit tests"""
    setup()
    push_job(TEST_MESSAGE, "test_queue_2")
    obj, jobid = get_job("test_queue_2")
    assert obj == TEST_MESSAGE
    done("test_queue_2", jobid)


def test_semantics():
    """Hook for the unit tests"""
    setup()
    clear_queue("test_queue_2")
    push_job(TEST_MESSAGE, "test_queue_2")
    obj, jobid = get_job("test_queue_2")
    assert obj == TEST_MESSAGE
    obj2, jobid2 = get_job("test_queue_2")
    assert obj2 == None, "%s"%(obj2)
    assert jobid2 == None
    done("test_queue_2", jobid)


def test_timeout():
    setup()
    return
    clear_queue("test_queue_2")
    push_job(TEST_MESSAGE, "test_queue_2", timeout=120)
    obj, jobid = get_job("test_queue_2")
    assert obj == TEST_MESSAGE, "Message is not in the queue"
    obj, jobid = get_job("test_queue_2")
    assert obj == None, "Message was not removed form the queue"
    time.sleep(61)
    obj2, jobid2 = get_job("test_queue_2")
    assert obj2 == None, "time was not obeyed"
    time.sleep(125-61)
    obj2, jobid2 = get_job("test_queue_2")
    assert obj2 == TEST_MESSAGE, "Message did not go back in the queue."
    done("test_queue_2", jobid2)


