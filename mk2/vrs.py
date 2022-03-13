import sqlite3



class vrs():
    def __init__(self,dbname):
        self.db = sqlite3.connect(dbname)
        


if __name__ == '__main__':
    vserver = vrs("vrs_data.sqb")