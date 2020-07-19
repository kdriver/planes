
TO_SCREEN=1
TO_FILE=2
BOTH=3


GREEN_TEXT=1
RED_TEXT=2

RED="\033[1;31;40m"
GREEN="\033[1;32;40m"
CLEAR="\033[0m"

log = open("output.txt","a")

def loggit(text,to=BOTH,col=None):
    prefix=''
    suffix=''
    if col == GREEN_TEXT:
        prefix=GREEN
        suffix=CLEAR
    if col == RED_TEXT:
        prefix=RED
        suffix=CLEAR

    if (to & TO_FILE) == TO_FILE:
        log.write(text+"\n")
        log.flush()

    if col != None:
        text = prefix + text + suffix

    if (to & TO_SCREEN) == TO_SCREEN:
        print(text)


