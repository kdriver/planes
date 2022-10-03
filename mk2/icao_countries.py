import csv


def read_icao_countries(file: str)-> list[str]:
    with open(file) as csvfile:
        lines = csv.reader(csvfile,delimiter=',')
        for row in lines:
            yield row
 
    

if __name__ == '__main__':
    table = read_icao_countries("icao_countries.csv")
    for row in table:
        print(row)
        print(row[0],row[1],row[2])
        from_value = int(row[0],16)
        to_value = int(row[1],16)
        print(f"{from_value} {to_value}")