import os
import re

kmls="/mnt/usb_stick/kmls"
planes="/mnt/usb_stick/planes"
new_planes=0

def process_file(f,the_original_file):
    global new_planes
    plane = re.search('^.*__',f)
#    plane = re.search('^[A-Z0-9-]*_[[A-Z0-9-]*__',f)
    id = plane.group(0)[:-2]
    plane_dir = os.path.join(planes,id)
    if os.path.isdir(plane_dir) is False:
        os.mkdir(plane_dir)
        new_planes = new_planes + 1
        
    new_linked_file_name = os.path.join(plane_dir,f)
    if os.path.exists(new_linked_file_name) is False:
        os.link(the_original_file,new_linked_file_name)
    return

def descend(directory):
    for d in os.listdir(directory):
        filename=os.path.join(directory,d)
        if os.path.isdir(filename) is True:
            descend(filename)
        else:
            process_file(d,filename)



if __name__ == "__main__":
    descend(kmls)
    print(f"kml files linked. {new_planes} new planes seen")
