""" A generic logging Service """
TO_SCREEN=1
TO_FILE=2
TO_DEBUG=4
TO_VRS=8
BOTH=3
ALL=15

GREEN_TEXT=1
RED_TEXT=2
YELLOW_TEXT=3
CYAN_TEXT=4

YELLOW="\033[1;33;40m"
RED="\033[1;31;40m"
GREEN="\033[1;32;40m"
CYAN="\033[1;36;40m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
GREEN="\033[1;32m"
CYAN="\033[1;36m"
CLEAR="\033[0m"
colour_map = { GREEN_TEXT : GREEN, RED_TEXT : RED ,
                CYAN_TEXT : CYAN , YELLOW_TEXT : YELLOW , None : '' }


LOG = None
DLOG = None
VRS = None

def init_loggit(logging,dlogging,vrslogging):
    """ Initialise logging files"""
    global LOG,DLOG,VRS
    LOG = open(logging,"a",encoding="utf-8")
    DLOG = open(dlogging,"w",encoding="utf-8")
    VRS  = open(vrslogging,"a",encoding="utf-8")

def loggit(text,to_log=BOTH,col=None):
    """ A function t provide generic logging to_log file and screen """
    prefix=''
    suffix=CLEAR

    prefix = colour_map[col]

    if ( to_log & TO_DEBUG ) == TO_DEBUG:
        DLOG.write(str(text)+"\n")
        DLOG.flush()


    if (to_log & TO_FILE) == TO_FILE:
        LOG.write(str(text)+"\n")
        LOG.flush()

    if col is not None:
        text = prefix + str(text) + suffix

    if (to_log & TO_VRS) == TO_VRS:
        VRS.write(str(text)+"\n")
        VRS.flush()

    if (to_log & TO_SCREEN) == TO_SCREEN:
        print(str(text))
