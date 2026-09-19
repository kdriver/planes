"""A program to detect planes and tweet."""

import json
import math
import os
import re
import time

import requests
import sqldb
from blessed import Terminal
from vrs import Vrs

from Haversine import Haversine
from kml import three_d_vrs, write_kmz
from loggit import BOTH, CYAN_TEXT, GREEN_TEXT, RED_TEXT, TO_DEBUG, TO_SCREEN, YELLOW_TEXT, init_loggit, loggit
from reference_data import add_reference_data, flush_suppression_list, init_reference_data, is_suppressed, plane_seen, update_reference_data
from runtime_config import AIRCRAFT_JSON_PATH, ensure_runtime_dirs
from web import start_webserver, update_plane_data
from home import home
from plane_reporting import PlaneReporter
from plane_tracker import PlaneTracker


term = Terminal()
all_planes = {}
tracker = None

# planes with closest approach to home of less that TWEET_RADIUS miles will be tweeted
TWEET_RADIUS = 2.0

osm_file = open('./osm_file.csv', 'a')
# get the postcode string from open street map return
pattern = re.compile(r'([A-Z][A-HJ-Y][0-9]* [0-9][A-Z][A-Z])')

osm = requests.Session()
dump_planes = False
dump_icao = None
dump_time = 0
reporter = None


def get_term_width() -> int:
    """Return the current terminal width."""
    return term.width


def get_time(clock):
    """Return an ascii string of the current time."""
    return time.asctime(time.localtime(clock))


def enrich(icao_hex, the_plane):
    """Given the icao hex, enrich the plane data from reference data."""
    if is_suppressed(icao_hex):
        return
    try:
        result = add_reference_data(icao_hex, the_plane)
    except Exception as my_exp:
        print(f'enrich exception {my_exp}')
        return

    if result is None and '~' not in icao_hex:
        loggit('could not enrich plane {}'.format(icao_hex))
        return
    if result is None and '~' in icao_hex:
        global dump_time, dump_icao, dump_planes
        dump_time = time.time() + 60
        dump_icao = icao_hex
        dump_planes = False
    the_plane['enriched'] = 1


def read_planes():
    """Read in the planes from dump1090 and cache the data."""
    global all_planes, tracker
    try:
        ensure_runtime_dirs()
        with open(AIRCRAFT_JSON_PATH, 'r') as f:
            try:
                data = json.load(f)
            except Exception:
                print("error - can't open aircraft.json")
                return

            if tracker is None:
                tracker = PlaneTracker(home)
            tracker.update_from_dump(data, enrich_callback=enrich, report_callback=reporter.nearest_point)
            all_planes = tracker.all_planes
    except Exception as exc:
        print(f' error in read_planes {exc}\n')


def dump_the_planes(icao_hex):
    """Called to dump planes with similar height and distance."""
    loggit(f'Dump planes with similar distance to {icao_hex}')
    if icao_hex not in all_planes:
        loggit(f'could not find {icao_hex} in all_planes')
        return
    target = all_planes[icao_hex]

    if 'miles' not in target:
        loggit("could not find 'miles' in all_planes")
        return

    if 'lat' not in target or 'lon' not in target:
        loggit('target plane does not have both lat and lon - exit')
        return

    ll_target = [target['lat'], target['lon']]
    alt = int(target['alt_baro'])
    target_time = target['touched']
    for the_plane, _a_plane in all_planes.items():
        this_plane = all_planes[the_plane]
        proximity = 100
        if 'lat' in this_plane and 'lon' in this_plane:
            ll_this = [this_plane['lat'], this_plane['lon']]
            hv = Haversine(ll_target, ll_this)
            proximity = hv.miles

        h_diff = 1001
        if 'alt_baro' in this_plane and this_plane['alt_baro'] != 'ground':
            h_diff = abs(alt - int(this_plane['alt_baro']))

        if proximity < 20 and h_diff < 1000:
            txt = '{' + " hex:'{}',proximity:'{:.2f}'".format(icao_hex, proximity)
            for item in ['icao', 'alt_baro', 'miles', 'track', 'tail', 'lat', 'lon']:
                if item in this_plane:
                    txt = txt + ",{}:'{}'".format(item, this_plane[item])
            txt = txt + ",version:'1'"
            txt = txt + ",tdiff:'{:.2f}', tn:'{}' ".format(
                (target_time - this_plane['touched']), get_time(time.time())) + '},'
            loggit(txt)


init_loggit('output.txt', '/tmp/debug.txt', 'vrs_update_logging.txt')
init_reference_data()
update_reference_data()
start_webserver()
last_tick = time.time()
last_log = last_tick
sqldb.attach_sqldb()
reporter = PlaneReporter(osm, osm_file, pattern, term, TWEET_RADIUS)

vrs = Vrs('vrs_data.sqb')
tracker = PlaneTracker(home, vrs)
all_planes = tracker.all_planes

min_time = 100.0
max_time = 0.0
ave_time = 0.0
readings = 0

while 1:
    loop_timer_now = time.time()
    read_planes()
    now = time.time()
    if tracker is not None:
        tracker.prune_expired(now, report_callback=reporter.nearest_point, kml_writer=write_kmz, plane_seen_callback=plane_seen)
        all_planes = tracker.all_planes

    update_reference_data()
    update_plane_data(all_planes)

    if dump_planes:
        if now > dump_time:
            dump_the_planes(dump_icao)
            dump_planes = False

    if os.path.exists('check_icao'):
        with open('check_icao') as f:
            s = f.read()
            dump_the_planes(str(s).strip().upper())
        os.remove('check_icao')

    if (now - last_tick) > 60:
        if (now - last_log) > 300:
            loggit('{} planes being tracked '.format(len(all_planes)), TO_SCREEN)
            last_log = now
            flush_suppression_list()
        three_d_vrs(all_planes)
        last_tick = now

    elapsed = time.time() - loop_timer_now
    min_time = min(min_time, elapsed)
    max_time = max(max_time, elapsed)
    readings += 1
    ave_time = ave_time + (elapsed - ave_time) / readings
    loggit(f'{elapsed: .2f} secs , min {min_time: .2f} , max {max_time: .2f} , ave {ave_time: .2f}', TO_DEBUG)

    time.sleep(5)
