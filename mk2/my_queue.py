""" a class to manage a LIFO queue """

#from loggit import loggit
#from loggit import TO_DEBUG

INFINITE = 0

#inherit from dict to make class serialisable
class my_queue(dict):
    """ A generic LIFO queue """
    def __init__(self,size_q,name=None):
        dict.__init__(self)
        self.size_q = size_q
        self.q = []
        self.n = 0
        self.name = name
        #loggit("my_queue {} created".format(name),TO_DEBUG)

    def add(self,element):
        """ Add an element to the queue at the head of the queue """
        if self.size_q != INFINITE:
            if  len(self.q) >= self.size_q:
                del self.q[-1]
        self.q.insert(0,element)

    def get_values(self):
        """return the list object"""
        return self.q

    # def __del__(self):
    #     loggit("delete Q {} len {}".format(self.name,len(self.q)),TO_DEBUG)
    #     del self.q
    #     del self.size_q


if __name__ == "__main__":
    print("Tests")
    q = my_queue(10)
    for a in range(0,12):
        q.add(a+0.1)
        values = q.get_values()
        print("{}, {}".format(len(values),values))
        
