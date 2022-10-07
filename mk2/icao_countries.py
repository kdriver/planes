""" Map a table of icao number ranges to countries and allow lookup"""
import csv
from typing import Optional


class ICAOCountries:
   
    def __init__(self,file : Optional[str] = "icao_countries.csv"):
        with open(file,encoding='utf-8') as csvfile:
            self.countries_map =[]
            lines = csv.reader(csvfile,delimiter=',')
            for row in lines:
                from_value = int(row[0],16)
                to_value = int(row[1],16)
                country = row[2]
                self.countries_map = self.countries_map + [[from_value,to_value,country]]
    
    def print_map(self):
        print(self.countries_map)
        
    def icao_to_country(self,icao ):
        try:
            if isinstance(icao, str):
                if '~' in icao:
                    return "TISB"
                icao = int(icao,16)
                for entry in self.countries_map:
                    if entry[0] <= icao <= entry[1]:
                        return entry[2]
            else:
                return f"icao not a string {icao}"
        except Exception as my_ex:
            print(f"icao_to_country exception {my_ex} for {icao}")
        return "not found"
        
 
    
if __name__ == '__main__':
    my_map = ICAOCountries()
    print(f"{my_map.icao_to_country(0x40624f)}")
    print(f'{my_map.icao_to_country("40624f")}')
