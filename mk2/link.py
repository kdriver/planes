import os
import re

KMLS="/mnt/usb_stick/kmls"
PLANES="/mnt/usb_stick/planes"
new_planes=0

def process_file(f,the_original_file):
    """link a file if it doesnt exist"""
    global new_planes
    # plane = re.search('^.*__',f)
    plane = re.search('^.*[0-9A-F](__|--)',f)
    if plane is None:
        return
    id_text = plane.group(0)[:-2]
    plane_dir = os.path.join(PLANES,id_text)
    if os.path.isdir(plane_dir) is False:
        os.mkdir(plane_dir)
        new_planes = new_planes + 1
        
    new_linked_file_name = os.path.join(plane_dir,f)
    if os.path.exists(new_linked_file_name) is False:
        os.link(the_original_file,new_linked_file_name)
    return

def descend(directory):
    """ recursively descend dirs """
    for the_d in os.listdir(directory):
        filename=os.path.join(directory,the_d)
        if os.path.isdir(filename) is True:
            descend(filename)
        else:
            process_file(the_d,filename)



if __name__ == "__main__":
    descend(KMLS)
    print(f"kml files linked. {new_planes} new planes seen")
