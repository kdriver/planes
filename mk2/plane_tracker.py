"""Helpers for tracking aircraft positions near home."""

from __future__ import annotations

import time

from Haversine import Haversine
from my_queue import INFINITE, my_queue


class PlaneTracker:
    """Maintain the in-memory aircraft state used by the detector."""

    def __init__(self, home_coords, vrs=None):
        self.home = home_coords
        self.vrs = vrs
        self.all_planes = {}

    def update_from_dump(self, data, enrich_callback=None, report_callback=None):
        """Track aircraft data from dump1090 JSON."""
        planes = data.get('aircraft', [])
        for plane in planes:
            start_miles = 1000
            miles = start_miles
            try:
                icao = plane['hex'].strip().upper()
                if icao not in self.all_planes:
                    self.all_planes[icao] = {
                        'icao': icao,
                        'max_miles': 0.0,
                        'closest_miles': start_miles,
                        'closest_lat': 0.0,
                        'closest_lon': 0.0,
                        'miles': start_miles,
                        'tracks': my_queue(INFINITE, icao),
                    }
                this_plane = self.all_planes[icao]
                this_plane['touched'] = time.time()
            except Exception as exc:
                print(f'no icao code in plane record {exc}')
                continue

            for attr in ['lon', 'lat', 'flight', 'track', 'alt_baro']:
                if attr in plane:
                    this_plane[attr] = plane[attr]

            if 'lat' in this_plane and 'lon' in this_plane and 'alt_baro' in this_plane:
                try:
                    hv = Haversine(self.home, [this_plane['lon'], this_plane['lat']])
                    miles = hv.miles
                    bearing = int(hv.bearing)
                    this_plane['current_miles'] = miles
                    this_plane['tracks'].add({
                        'miles': miles,
                        'lon': this_plane['lon'],
                        'lat': this_plane['lat'],
                        'alt': this_plane['alt_baro'],
                    })
                    if miles < this_plane['miles']:
                        this_plane['closest_lat'] = float(this_plane['lat'])
                        this_plane['closest_lon'] = float(this_plane['lon'])
                        this_plane['closest_alt'] = this_plane['alt_baro']
                        this_plane['closest_miles'] = miles
                        this_plane['closest_time'] = time.time()
                        if this_plane['miles'] == start_miles:
                            pass
                        if 'reported' in this_plane:
                            del this_plane['reported']
                        this_plane['miles'] = miles
                    if miles > this_plane['max_miles']:
                        this_plane['max_miles'] = miles
                        this_plane['max_lon'] = this_plane['lon']
                        this_plane['max_lat'] = this_plane['lat']
                        if self.vrs is not None and isinstance(this_plane['alt_baro'], int):
                            self.vrs.update_entry(
                                bearing,
                                this_plane['lat'],
                                this_plane['lon'],
                                this_plane['alt_baro'],
                                miles,
                                this_plane['icao'],
                            )
                except Exception as exc:
                    print(f'oh dear haversine {exc} {this_plane}')
                    continue

            if miles < 200 and 'enriched' not in this_plane and enrich_callback is not None:
                enrich_callback(icao, this_plane)

            if (miles - this_plane['closest_miles']) > (this_plane['closest_miles'] * 0.1):
                if 'reported' not in this_plane and this_plane['closest_miles'] < 50 and report_callback is not None:
                    report_callback(this_plane)

    def prune_expired(self, now, report_callback=None, kml_writer=None, plane_seen_callback=None):
        """Remove stale aircraft entries and trigger expiry reporting."""
        delete_list = []
        for icao, record in list(self.all_planes.items()):
            if (now - record['touched']) > 60:
                delete_list.append(icao)

        for plane in delete_list:
            plane_record = self.all_planes[plane]
            if 'reported' not in plane_record and 'miles' in plane_record and plane_record['miles'] < 50:
                plane_record['expired'] = 1
                if report_callback is not None:
                    report_callback(plane_record)
            if kml_writer is not None:
                kml_writer(self.home, plane_record)
            if plane_seen_callback is not None and 'icao' in plane_record:
                plane_seen_callback(plane_record['icao'])
            del self.all_planes[plane]
