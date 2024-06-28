import os
from datetime import datetime 
from dateutil.relativedelta import relativedelta
import shutil

directory = os.fsencode("kmls")

dirs = []

    
for file in os.listdir(directory):
     filename = os.fsdecode(file)
     if filename.endswith(".asm") or filename.endswith(".py") or filename.startswith(".") or filename.endswith(".tgz"):
        # print(os.path.join(directory, filename))
        continue
     else:
        the_date = datetime.strptime(filename,"%d-%b-%Y")
        dirs.append(the_date)
        continue

dirs.sort()

last_date = dirs[-1]

print(f'Current date {last_date.strftime("%d-%b-%Y")}')

two_months_ago = last_date - relativedelta(months=2)

print(f"{two_months_ago}")

for d in dirs:
    fn = f'kmls/{d.strftime("%d-%b-%Y")}'
    if d < two_months_ago:
        print(f'removing {fn}')
        shutil.rmtree(fn)

