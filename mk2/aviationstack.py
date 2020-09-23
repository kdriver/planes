import requests

params = {
          'access_key': 'a1ea84c48e3a6a342058abdee06bcfbf',
          'flight_icao' : '44A839'
          }

api_result = requests.get('http://api.aviationstack.com/v1/flights', params)

api_response = api_result.json()

print(api_response)

for flight in api_response['results']:
        if (flight['live']['is_ground'] is False):
            print(u'%s flight %s from %s (%s) to %s (%s) is in the air.' % ( flight['airline']['name'], flight['flight']['iata'], flight['departure']['airport'], flight['departure']['iata'], flight['arrival']['airport'], flight['arrival']['iata']))
