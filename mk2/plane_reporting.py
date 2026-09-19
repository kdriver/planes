"""Reporting helpers for plane nearest-point events."""

from __future__ import annotations

import json
import math
import time
import zipfile

from home import home
from kml import kml_doc
from loggit import BOTH, CYAN_TEXT, GREEN_TEXT, RED_TEXT, YELLOW_TEXT, loggit
import sqldb
from runtime_config import ensure_runtime_dirs


def get_time(clock):
    """Return an ascii string of the current time."""
    return time.asctime(time.localtime(clock))


class PlaneReporter:
    """Format and persist nearest-point plane reports."""

    def __init__(self, osm_session, osm_file, place_pattern, term, tweet_radius=2.0):
        self.osm = osm_session
        self.osm_file = osm_file
        self.pattern = place_pattern
        self.term = term
        self.tweet_radius = tweet_radius
        self.osm_time = 0

    def get_term_width(self):
        return self.term.width

    def get_place(self, lat, lon):
        """Use OpenStreetMap to look up the nearest place."""
        place = 'unknown'
        pos = ''
        try:
            if time.time_ns() - self.osm_time < 1_000_000_000:
                loggit('sleeping for OSM\n')
                time.sleep(1)
            else:
                loggit(f'delta since last OSM is {(time.time_ns() - self.osm_time)/1000000000}')

            req = 'https://nominatim.openstreetmap.org/reverse?format=json&lat={}&lon={}'.format(lat, lon)
            resp = self.osm.get(
                url=req,
                headers={'referer': 'kddplanes', 'User-Agent': 'MyUKAddressApp/1.0 driver.keith@gmail.com'},
            )
            self.osm_time = time.time_ns()
            try:
                pos = json.loads(resp.text)
                if 'display_name' in pos:
                    place = pos['display_name']
                else:
                    place = 'somewhere'
            except Exception:
                loggit(' json {} resp {}  '.format(pos, resp.text), BOTH, RED_TEXT)
        except Exception as exc:
            loggit('could not access OSM API {} req: {} '.format(exc, req), BOTH, RED_TEXT)
            return None

        return place[0:90]

    def nearest_point(self, the_plane):
        """Write the nearest-point report and KMZ for a plane."""
        pd = '{} {}'.format(get_time(the_plane['closest_time']), the_plane['icao'])
        for item in ['icao_country', 'closest_miles', 'flight', 'tail', 'track', 'alt_baro', 'Owner', 'Manufacturer', 'plane', 'route']:
            if item in the_plane and the_plane[item] is not None:
                if item in {'closest_miles', 'track'}:
                    pd = pd + ' {:>7.2f} '.format(the_plane[item])
                elif item in {'flight', 'tail', 'alt_baro'}:
                    pd = pd + '{0:7} '.format(the_plane[item])
                elif item in {'icao_country'}:
                    pd = pd + f" {the_plane['icao_country']:<15}"
                else:
                    pd = pd + ' {:<} '.format(the_plane[item])
            else:
                if item in ['closest_miles', 'track', 'alt_baro']:
                    the_plane[item] = 0
                else:
                    the_plane[item] = 'unknown'

        try:
            sqldb.insert_data((
                time.time(),
                the_plane['flight'],
                the_plane['icao'],
                the_plane['tail'],
                the_plane['plane'],
                the_plane['alt_baro'],
                the_plane['track'],
                the_plane['closest_miles'],
                the_plane['closest_lat'],
                the_plane['closest_lon'],
            ))
        except Exception as exc:
            loggit('could not insert data iinto planes record {}'.format(exc))

        name = the_plane.get('tail', 'unknown')
        if 'alt_baro' not in the_plane:
            the_plane['alt_baro'] = '0'

        kml_text = kml_doc(
            the_plane['closest_lon'],
            the_plane['closest_lat'],
            home[0],
            home[1],
            the_plane['alt_baro'],
            name,
            the_plane['closest_miles'],
            the_plane['tracks'],
        )

        ensure_runtime_dirs()
        with zipfile.ZipFile('kmls/{}.kmz'.format(name), 'w') as zf:
            zf.writestr('{}.kml'.format(name), kml_text)
            zf.close()

        if 'expired' in the_plane:
            pd = pd + ' expired '

        linelen = 145
        pd = pd[0:linelen]
        if len(pd) < 145:
            pd = pd + ' ' * (linelen - len(pd))

        place = self.get_place(the_plane['closest_lat'], the_plane['closest_lon'])
        if place is None:
            place = ' API failed '

        the_plane['reported'] = 1
        width = self.get_term_width() - 1
        try:
            if 'miles' not in the_plane:
                pd = pd + ' ' + json.dumps(the_plane)
                loggit(pd, BOTH, CYAN_TEXT)
                return

            if the_plane['miles'] < 40.00:
                postcode = self.pattern.findall(place)
                if len(postcode) == 0:
                    postcode.append('unknown')
                self.osm_file.write(f'{the_plane["closest_lon"]},{the_plane["closest_lat"]},{the_plane["tail"]},{the_plane["miles"]},"{postcode[0]}","{get_time(time.time())}"\n')
                self.osm_file.flush()

            if the_plane['miles'] < self.tweet_radius:
                pd = pd + ' : ' + place
                loggit(pd[:width], BOTH, GREEN_TEXT)
                txt = 'the_plane overhead '
                if 'Owner' in the_plane:
                    txt = txt + ' ' + the_plane['Owner']
                m = int(the_plane['miles'])

                if 'alt_baro' in the_plane:
                    if the_plane['alt_baro'] != 'ground':
                        h = math.floor(int(the_plane['alt_baro']) / 100)
                        if h > 9:
                            txt = txt + ' at ' + str(h / 10) + ' thousand feet'
                        else:
                            txt = txt + ' at ' + str(h) + ' hundred feet'
                else:
                    txt = txt + ' on ground'

                txt = txt + ' distance {:>1.1f} miles'.format(m)
            else:
                pd = pd + ' : ' + place
                if 'plane' in the_plane:
                    if 'DA42' in the_plane['plane']:
                        loggit(pd[:width], BOTH, YELLOW_TEXT)
                    else:
                        loggit(pd[:width], BOTH, CYAN_TEXT)
        except Exception as exc:
            loggit('reporting failed {}'.format(exc))
