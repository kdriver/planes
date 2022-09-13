""" A Python script to find new kml files and catalogue them under directories names after planes"""

import os
import re

KMLS="/mnt/usb_stick/kmls"
PLANES="/mnt/usb_stick/planes"

class Counter :
    """ A simple class to count the number of new planes found this cycle"""
    def __init__(self):
        self.planes = 0

    def incr(self)->None:
        """ Add one to the planes"""
        self.planes = self.planes + 1

    def num(self)->int:
        """ retrun the number of counted planes """
        return self.planes

def process_file(filename:str,the_original_file:str)->None:
    """link a file if it doesnt exist"""

    # Awful regex becaise I sarted off with using __ as a separator, 
    # but then that go used in the single digit days
    # So now the filenames use -- as a separator, but this regexp copes with both

    plane = re.search('^.*[0-9A-F](__|--)',filename)
    if plane is None:
        return
    # plane id is the regex match minus the two last characters.
    id_text = plane.group(0)[:-2]
    plane_dir = os.path.join(PLANES,id_text)
    if os.path.isdir(plane_dir) is False:
        os.mkdir(plane_dir)
        counter.incr()
        print(f"new plane {id_text}")

    new_linked_file_name = os.path.join(plane_dir,filename)
    if os.path.exists(new_linked_file_name) is False:
        os.link(the_original_file,new_linked_file_name)


def descend(directory: str)->None:
    """ recursively descend dirs """
    for the_d in os.listdir(directory):
        filename=os.path.join(directory,the_d)
        if os.path.isdir(filename) is True:
            descend(filename)
        else:
            process_file(the_d,filename)

if __name__ == "__main__":
    counter = Counter()
    descend(KMLS)
    print(f"kml files linked. {counter.num()} new planes seen")
