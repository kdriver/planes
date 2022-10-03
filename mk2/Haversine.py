""" Calculate the distance around the globe between two points"""
# import math
from math import radians, cos, sin, asin, sqrt,degrees,atan2,atan
# from geographiclib.geodesic import Geodesic
#from numpy import arctan2,sin,cos,degrees



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
        # b = Geodesic.WGS84.Inverse(lat1, lon1, lat2, lon2)['azi1']
        dL = lon2-lon1
        # print("lat2 {} Dl {}".format(lat2,dL))
        X = cos(radians(lat2))*sin(radians(dL))
        # print("X = {}".format(X))
        Y = cos(radians(lat1))*sin(radians(lat2)) - sin(radians(lat1))*cos(radians(lat2))*cos(radians(dL))
        # print("Y = {}".format(Y))
        B = atan2(X,Y)
        # print("B ",B)
        deg = degrees(B)
        if  deg < 0 :
            deg = 360+deg
        self.bearing = deg
        # print("Bearing {}".format(self.bearing))
        # self.get_bearing(coord1,coord2)

    def get_bearing(self,coord1,coord2):
        lon1,lat1=coord1
        lon2,lat2=coord2
        dLon = lon2 - lon1
        dLat = lat2 - lat1
        print("dLon {} dLat {}".format(dLon,dLat))
        if dLat != 0:
            angle = degrees(atan(dLon/dLat))
            print("angle = {}".format(angle))
        else:
            angle = 0
        return angle


def h3( lon1,lat1,lon2,lat2 ):
    R = 3959.87433 # this is in miles.  For Earth radius in kilometers use 6372.8 km
    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    lat1 = radians(lat1)
    lat2 = radians(lat2)

    a = sin(dLat/2)**2 + cos(lat1)*cos(lat2)*sin(dLon/2)**2
    c = 2*asin(sqrt(a))

    return R * c


# lon(-1.95) , lat (50.xx)
home=[ -1.9591988377888176,50.835736602072664]
south = [home[0]-.1,home[1]]
north = [home[0]+.1,home[1]]
north_e = [ -0.8277038156488696, 51.543650136330484]
north_w = [ -3.2776203339186836, 51.446628477355695]
south_w = [ -2.9260790560059236, 50.157204773905306]
south_e = [ -0.6030073278832201, 49.95010672073919]
kansas = [-94.581213, 39.099912]
stlouis = [ -90.200203 , 38.627089 ]
nnw = [-2.1778306175482243,51.6567366874194]

west  = [home[0],home[1]-1]
east  = [home[0],home[1]+1]
west_s  = [home[0]-0.01,home[1]-1]
def test():
    home=[ -1.9591988377888176,50.835736602072664]
    p1 = [-1.37825,50.749155]
    hv = Haversine(home,p1)
    h = hv.miles
    print(h)
    b = hv.bearing
    print(int(b))

def test1():

    for point in [north_e,north_w,south_e,south_w]:
        print("\n",point[1],point[0])
        hv = Haversine(home,point)

    hv = Haversine(home,nnw)
    
    print("south {}".format(hv.bearing))
    # hv = Haversine(home,north)
    # print("north {}".format(hv.bearing))
    # hv = Haversine(home,west)
    # print("west {}".format(hv.bearing))
    # hv = Haversine(home,west_s)
    # print("west_s {}".format(hv.bearing))
    # hv = Haversine(home,east)
    # print("east {}".format(hv.bearing))


if __name__ == "__main__":
    test1()
