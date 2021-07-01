import math
from math import radians, cos, sin, asin, sqrt


class Haversine:
    '''
    use the haversine class to calculate the distance between
    two lon/lat coordnate pairs.
    output distance available in kilometers, meters, miles, and feet.
    example usage: Haversine([lon1,lat1],[lon2,lat2]).feet

    '''
    def __init__(self,coord1,coord2):
        lon1,lat1=coord1
        lon2,lat2=coord2
        self.miles=h3(lon1,lat1,lon2,lat2)
        #print("miles {}".format(self.miles))
        return


from math import radians, cos, sin, asin, sqrt

def h3( lon1,lat1,lon2,lat2 ):
      R = 3959.87433 # this is in miles.  For Earth radius in kilometers use 6372.8 km
      dLat = radians(lat2 - lat1)
      dLon = radians(lon2 - lon1)
      lat1 = radians(lat1)
      lat2 = radians(lat2)

      a = sin(dLat/2)**2 + cos(lat1)*cos(lat2)*sin(dLon/2)**2
      c = 2*asin(sqrt(a))

      return R * c

def test():
    home=[ -1.9591988377888176,50.835736602072664]
    p1 = [-1.37825,50.749155]
    h = Haversine(home,p1).miles
    print(h)
    d = h3(home[0],home[1],p1[0],p1[1])
    print(d)

if __name__ == "__main__":
    test()
