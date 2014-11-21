import logging
from input_configuration import *

class Logger():
    def _init_(self, name):
        logging.basicConfig(filename=main_log_file,format='%(asctime)s %(message)s', datefmt='%m/%d/%Y        %I:% M:%S %p')
        handler = logging.StreamHandler()
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
   
    def timed(f):
        @wraps(f)
        def wrapper(*args, **kwds):
            start = time()
            result = f(*args, **kwds)
            elapsed = time() - start
            print "%s took %s time to finish" % (f.__name__, elapsed)

            main_logger = logging.getLogger('main_logger')
            main_logger.info("%s took %s time to finish" % (f.__name__, elapsed))
        return result
    return wrapper
        
