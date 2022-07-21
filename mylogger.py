import logging
import coloredlogs
from logging.handlers import TimedRotatingFileHandler

def get_logger(module_name):

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(module_name)

    # By default the install() function installs a handler on the root logger,
    # this means that log messages from your code and log messages from the
    # libraries that you use will all show up on the terminal.

    #coloredlogs.install(level='DEBUG')

    # If you don't want to see log messages from libraries, you can pass a
    # specific logger object to the install() function. In this case only log
    # messages originating from that logger will show up on the terminal.

    #coloredlogs.install(level='DEBUG', logger=logger)

    # create a file handler
    #handler = logging.FileHandler('log.log')
    handler = TimedRotatingFileHandler(filename='log.log', when='D', interval=1, backupCount=90, encoding='utf-8',
                                       delay=False)
    handler.setLevel(logging.INFO)

    # create a logging format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    LEVEL_STYLES = dict(
        debug=dict(color='magenta'),
        info=dict(color='green'),
        verbose=dict(),
        warning=dict(color='blue'),
        error=dict(color='yellow'),
        critical=dict(color='red', bold=True))

    # FORMAT = "%(asctime)s;%(levelname)s|%(message)s"
    FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    DATEF = "%H-%M-%S"

    coloredlogs.install(level=logging.DEBUG, fmt=FORMAT, datefmt=DATEF, level_styles=LEVEL_STYLES)

    handler.setFormatter(formatter)

    # add the file handler to the logger
    logger.addHandler(handler)

    return logger
