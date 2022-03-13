import json
try:
        #with open('/var/run/dump1090-fa/aircraft.json', 'r') as f:
        with open('tilda.json', 'r') as f:
            try:
                data = json.load(f)
                print(data)
            except  Exception as e:
                print(e)


