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
from settings import run_args
from scripts.settings import state

# from emme_configuration import main_log_file
from functools import wraps
from time import time
import datetime
import os, sys, errno

sys.path.append(os.getcwd())
# os.chdir(r'..')
import toml

state = state.generate_state(run_args.args.configs_dir)
# network_config = toml.load(
#     os.path.join(os.getcwd(), "configuration\\network_configuration.toml")
# )

def setup_custom_logger(name, log_file, level=logging.INFO):
    """To setup as many loggers as you want"""
    
    # create dir for main log file if it doesn't exist
    try:
        os.makedirs("outputs/logs")
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler = logging.FileHandler(log_file)        
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger

def create_skims_and_paths_logger():
    return setup_custom_logger('skims_logger', 'outputs/logs/skims_log.txt')

# def setup_custom_logger(name, file_name):
#     # create dir for main log file if it doesn't exist
#     try:
#         os.makedirs("outputs/logs")
#     except OSError as e:
#         if e.errno != errno.EEXIST:
#             raise
#     logging.basicConfig(
#         filename=file_name,
#         format="%(asctime)s %(message)s",
#         datefmt="%m/%d/%Y %I:%M:%S %p",
#     )
#     handler = logging.StreamHandler()
#     logger = logging.getLogger(name)
#     logger.setLevel(logging.INFO)
#     logger.addHandler(handler)
#     return logger


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
