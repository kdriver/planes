import requests
import inspect

flight="RYR63HE "
orgurl="https://ae.roplan.es/api/callsign-origin_IATA.php?callsign="
sorgurl="https://ae.roplan.es/api/callsign-origin_IATA.php"
purl=orgurl+flight
purl=purl.strip()
print(purl)
payload={ "callsign" : flight.strip() }
response = requests.post(sorgurl,params=payload)
print(type(response))
print(inspect.getmembers(response))


print("respnse url",response.url)
print("report ",response.text)
print("status ",response.status_code)
