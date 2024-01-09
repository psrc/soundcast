# Copyright [2014] [Puget Sound Regional Council]

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

# from emme_configuration import main_log_file
from functools import wraps
from time import time
import datetime
import os, sys, errno

sys.path.append(os.getcwd())
# os.chdir(r'..')
import toml


network_config = toml.load(
    os.path.join(os.getcwd(), "configuration\\network_configuration.toml")
)


def setup_custom_logger(name):
    # create dir for main log file if it doesn't exist
    try:
        os.makedirs("outputs/logs")
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    logging.basicConfig(
        filename=network_config["main_log_file"],
        format="%(asctime)s %(message)s",
        datefmt="%m/%d/%Y %I:%M:%S %p",
    )
    handler = logging.StreamHandler()
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger


def timed(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        main_logger = logging.getLogger("main_logger")

        start = datetime.datetime.now()
        main_logger.info(" %s starting" % (f.__name__))

        result = f(*args, **kwds)

        elapsed = datetime.datetime.now() - start
        main_logger.info("%s took %s" % (f.__name__, str(elapsed)))
        return result

    return wrapper
