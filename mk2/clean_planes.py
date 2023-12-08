import os
import time

directory = "./planes/"

files = []

now =  time.time()
print(now)

two_months_ago = now - ( 60*24*60*60 )

def check_file(f):
    if f.endswith(".kmz"): 
        m = os.path.getmtime(f)
        if  m < two_months_ago :
            print(f' kill {f}')
            os.remove(f)

for f in os.listdir(directory):
    if os.path.isdir(directory+'/'+f):
        for file in os.listdir(directory+'/'+f):
            check_file(directory+'/'+f+'/'+file)
    else:
        check_file(f)
            
        

 



