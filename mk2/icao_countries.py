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
        if isinstance(icao, str):
            icao = int(icao,16)
        for entry in self.countries_map:
            if entry[0] <= icao <= entry[1]:
                return entry[2]
        return "not found"
        
                
                
            
            
        


def read_icao_countries(file: str)-> list[str]:
    with open(file,encoding='utf-8') as csvfile:
        lines = csv.reader(csvfile,delimiter=',')
        for row in lines:
            yield row
 
    

if __name__ == '__main__':
    my_map = ICAOCountries()
    print(f"{my_map.icao_to_country(0x40624f)}")
    print(f'{my_map.icao_to_country("40624f")}')
    # table = read_icao_countries("icao_countries.csv")
    # for row in table:
    #     # print(row)
    #     # print(row[0],row[1],row[2])
    #     # print(f" {type(row[0])} , {type(row[1])}")
    #     from_value = int(row[0],16)
    #     to_value = int(row[1],16)
    #     print(f"{from_value:x} {to_value:x}")