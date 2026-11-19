"""Build reference_index.sqb: a compact, indexed hex -> (tail, type) table.

Built from the downloaded bulk databases so DataService.lookup() can resolve
planes locally before trying the online APIs:
  basic-ac-db.json               ADS-B Exchange (preferred)
  opensky-aircraft-database.csv  OpenSky snapshot (fills gaps; falls back to the
                                 older aircraftDatabase.csv if not downloaded yet)

Run by update_BaseStation.sh after downloads, or by hand:  python build_reference_index.py
"""

import csv
import json
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, 'reference_index.sqb')
ADSBX = os.path.join(HERE, 'basic-ac-db.json')
OPENSKY = os.path.join(HERE, 'opensky-aircraft-database.csv')  # symlink to newest snapshot
if not os.path.exists(OPENSKY):
    OPENSKY = os.path.join(HERE, 'aircraftDatabase.csv')


def adsbx_rows():
    with open(ADSBX, errors='replace') as f:
        for line in f:
            try:
                ac = json.loads(line)
            except ValueError:
                continue
            tail = (ac.get('reg') or '').strip()
            if ac.get('icao') and tail:
                yield ac['icao'].lower(), tail, (ac.get('icaotype') or '').strip(), 'adsbx'


def opensky_rows():
    csv.field_size_limit(sys.maxsize)
    with open(OPENSKY, errors='replace', newline='') as f:
        # the 2025+ snapshots quote with ' ; the older aircraftDatabase.csv with "
        quote = "'" if f.readline().startswith("'") else '"'
        f.seek(0)
        for row in csv.DictReader(f, quotechar=quote, escapechar='\\'):
            tail = (row.get('registration') or '').strip()
            hex_ = (row.get('icao24') or '').strip().lower()
            if hex_ and tail:
                yield hex_, tail, (row.get('typecode') or '').strip(), 'opensky'


def build():
    start = time.time()
    tmp = INDEX + '.tmp'
    if os.path.exists(tmp):
        os.remove(tmp)
    db = sqlite3.connect(tmp)
    db.execute('CREATE TABLE ref (hex text primary key, tail text, type text, source text)')
    counts = {}
    # ADS-B Exchange first; OpenSky only adds hexes ADSBx doesn't have
    for path, rows, verb in ((ADSBX, adsbx_rows, 'INSERT OR REPLACE'), (OPENSKY, opensky_rows, 'INSERT OR IGNORE')):
        if not os.path.exists(path):
            print(f'skipping missing {path}')
            continue
        before = db.total_changes
        db.executemany(f'{verb} INTO ref VALUES (?,?,?,?)', rows())
        counts[os.path.basename(path)] = db.total_changes - before
    db.commit()
    total = db.execute('SELECT count(*) FROM ref').fetchone()[0]
    db.close()
    os.replace(tmp, INDEX)  # atomic: readers see the old or new file, never a partial one
    print(f'reference index built: {total} planes {counts} in {time.time() - start:.0f}s')


if __name__ == '__main__':
    build()
