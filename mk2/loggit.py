""" A generic logging Service """
TO_SCREEN=1
TO_FILE=2
TO_DEBUG=4
BOTH=3


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

log = open("output.txt","a",encoding="utf-8")
dlog = open("/tmp/debug.txt","w",encoding="utf-8")

def loggit(text,to=BOTH,col=None):
    """ A function t provide generic logging to file and screen """
    prefix=''
    suffix=CLEAR

    if col == YELLOW_TEXT:
        prefix=YELLOW
    if col == GREEN_TEXT:
        prefix=GREEN
    if col == RED_TEXT:
        prefix=RED
    if col == CYAN_TEXT:
        prefix=CYAN

    prefix = colour_map[col]

    if ( to & TO_DEBUG ) == TO_DEBUG:
        dlog.write(str(text)+"\n")
        dlog.flush()


    if (to & TO_FILE) == TO_FILE:
        log.write(str(text)+"\n")
        log.flush()

    if col is not None:
        text = prefix + str(text) + suffix

    if (to & TO_SCREEN) == TO_SCREEN:
        print(str(text))
