#! /usr/bin/python3.5

#
# spoke something on GoogleHome
#
# use: ./ghome_say [ghome_ip] [text_to_say]
#
#

import pychromecast
import os
import os.path
from gtts import gTTS
import time
import hashlib
import socket
from multiprocessing import Process
from loggit import loggit,BOTH

#ip="192.168.0.107"
#ip="Google-Home"

#services, browser = pychromecast.discovery.discover_chromecasts()
#pychromecast.discovery.stop_discovery(browser)
#print(services[0][4])

def do_the_work(say):
    #********* retrieve local ip of my rpi3
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("192.168.0.1", 80))
    local_ip=s.getsockname()[0]
    s.close()
    #**********************

    fname=hashlib.md5(say.encode()).hexdigest()+".mp3" #create md5 filename for caching

    chromecasts, _browser = pychromecast.get_listed_chromecasts(friendly_names=["Back garden speaker"])
    castdevice = chromecasts[0]
    #castdevice = pychromecast.Chromecast(ip)
    castdevice.wait()
    vol_prec=castdevice.status.volume_level
    castdevice.set_volume(0.0) #set volume 0 for not hear the BEEEP

    try:
        os.mkdir("/var/www/html/mp3_cache/")
    except Exception:
        pass

    if not os.path.isfile("/var/www/html/mp3_cache/"+fname):
        tts = gTTS(say,lang='en')
        tts.save("/var/www/html/mp3_cache/"+fname)

    mc = castdevice.media_controller
    mc.play_media("http://"+local_ip+"/mp3_cache/"+fname, "audio/mp3")

    mc.block_until_active()

    mc.pause() #prepare audio and pause...

    time.sleep(1)
    castdevice.set_volume(0.2) #setting volume to precedent value
    time.sleep(0.2)

    mc.play() #play the mp3

    while not mc.status.player_is_idle:
        time.sleep(0.5)

    time.sleep(1)
    castdevice.set_volume(vol_prec) #setting volume to precedent value
    time.sleep(0.2)

    mc.stop()

    castdevice.quit_app()

#the cast object sometimes seems to block, so run in a sub process
def speak(say):

    if os.getenv("SPEAK_TO_ME") is not None:
        now = time.time()
        loggit("spawn a speaking process for {}".format(say),BOTH)
        p = Process(target=do_the_work,args=(say,))
        p.start()
        p.join(15)
        loggit(" speaking process for {} done , took {}".format(say,time.time()-now),BOTH)
