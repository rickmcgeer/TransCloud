import mq_client
import mq_calc
import mq_process_results

def test_mq_calculation():
    PREFIX="testing_calc_"
    ncities = 5
    size = mq_calc.populate_cities(ncities, testing_prefix=PREFIX, testing=True)
    assert size == ncities, "There were not messages in the queue: %d"%(size)

    ndone = mq_client.process_cities(testing_prefix=PREFIX, testing=True)
    assert ndone == ncities, "Did not process fake cities" + str(ndone)

    results = mq_process_results.process_results(prefix=PREFIX, testing=True)
    assert len(results) == ncities, "ncities results not processed"

    print ">>",type(results[0]), results

    for items in results:
        for keys in items.keys():
            assert items[keys] == mq_calc.FAKE_RESULT[keys], "The key" + keys + "does not match" 

if __name__=="__main__":
    test_mq_calculation()
    
