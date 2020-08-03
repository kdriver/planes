import time
import copy
import json
from  json2html import *
from http.server import HTTPServer,BaseHTTPRequestHandler

import threading


planes = {}
the_lock = threading.Lock()



def page():
    global planes
    txt = '<input type="text" id="myInput" onkeyup="myFunction()" placeholder="Search for names.." title="Type in a name">'
    txt = txt + '<table id="myTable">'
    txt = txt + '<tr class="header">'
    txt = txt + '<th> ICOA </th>'
    txt = txt + '<th> flight </th>'
    txt = txt + '<th> tail </th>'
    txt = txt + '<th> distance </th>'
#    txt = txt + '<th> nearest </th>'
    txt = txt + '<th> type </th>'
    txt = txt + '<th> alt </th>'
    txt = txt + '</tr>'
    for plane in planes:
        p = planes[plane]
        txt = txt + '<tr>'
        for item in ['icoa','flight','tail','miles','plane','alt_baro']:
            txt = txt + '<td>'
            if item in p:
                txt = txt + str(p[item]  )
            txt = txt + '</td>'
        txt = txt + '</tr>'
    return  txt


class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global planes
        global lock
        self.send_response(200)
        self.send_header("Content-type","text/html")
        self.end_headers()
        self.wfile.write(b'''<head><style>
        * {
          box-sizing: border-box;
          }

          #myInput {
            background-image: url('/css/searchicon.png');
              background-position: 10px 10px;
                background-repeat: no-repeat;
                  width: 100%;
                    font-size: 16px;
                      padding: 12px 20px 12px 40px;
                        border: 1px solid #ddd;
                          margin-bottom: 12px;
                          }

                          #myTable {
                            border-collapse: collapse;
                              width: 100%;
                                border: 1px solid #ddd;
                                  font-size: 18px;
                                  }

                                  #myTable th, #myTable td {
                                    text-align: left;
                                      padding: 12px;
                                      }

                                      #myTable tr {
                                        border-bottom: 1px solid #ddd;
                                        }

                                        #myTable tr.header, #myTable tr:hover {
                                          background-color: #f1f1f1;
                                          }
                                          </style></head><body>''')

        self.wfile.write(b'''
<script>
function myFunction() {
          var input, filter, table, tr, td, i, txtValue;
          input = document.getElementById("myInput");
          filter = input.value.toUpperCase();
          table = document.getElementById("myTable");
          tr = table.getElementsByTagName("tr");
          for (i = 0; i < tr.length; i++) {
               txt = ""
               td = tr[i].getElementsByTagName("td")[0];
               if (td) {
                          txtValue = td.textContent || td.innerText;
                          txt = txt + txtValue
                }
               td = tr[i].getElementsByTagName("td")[1];
               if (td) {
                          txtValue = td.textContent || td.innerText;
                          txt = txt + txtValue
                }
               td = tr[i].getElementsByTagName("td")[2];
               if (td) {
                          txtValue = td.textContent || td.innerText;
                          txt = txt + txtValue
                }
               td = tr[i].getElementsByTagName("td")[4];
               if (td) {
                          txtValue = td.textContent || td.innerText;
                          txt = txt + txtValue
                }
                          if (txt.toUpperCase().indexOf(filter) > -1) {
                                   tr[i].style.display = "";
                           } else {
                                   tr[i].style.display = "none";
                           }
                }       
           }
</script>''')
         

        the_lock.acquire()
        self.wfile.write(bytes("num planes " + str(len(planes)),'utf-8'))
        self.wfile.write(bytes(page(),'utf-8'))
        the_lock.release()
        self.wfile.write(b'</body>')
        return


class myThread(threading.Thread):
    def __init__(self,number):
        threading.Thread.__init__(self)
        self.httpd = HTTPServer(('' ,4443), MyHandler)
        self.num = number
        print("thread initialised")
    def run(self):
        print("thread running")
        self.httpd.serve_forever()

thread1=None

def start_webserver():
    try:
        thread1 = myThread(1)
        thread1.start()
        print("thread OK")
    except:
        print("failed to start thread")

def update_plane_data(p):
    global planes
    global the_lock
    the_lock.acquire()
    planes = copy.deepcopy(p)
    the_lock.release()
    #print("update plane data for web {} {}".format(len(p),len(planes)))

