import json

#inherit from dict to make class serialisable
class my_queue(dict):
    def __init__(self,size_q):
        self.size_q = size_q
        self.q = []
        self.n = 0
    
    # def toJSON(self):
    #     return json.dumps(self, default=lambda o: o.__dict__, 
    #         sort_keys=True, indent=4)

    def add(self,element):
        if len(self.q) >= self.size_q:
            del self.q[-1]
        self.q.insert(0,element)

    def get_values(self):
        return self.q


if __name__ == "__main__":
    print("Tests")
    q = my_queue(10)        
    for a in range(0,12):
        q.add(a+0.1)
        values = q.get_values()
        print("{}, {}".format(len(values),values))


