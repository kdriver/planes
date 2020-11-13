import copy
from http.server import HTTPServer,BaseHTTPRequestHandler

import threading


planes = {}
the_lock = threading.Lock()

def page():
    global planes
    txt = '<input type="text" id="myInput" onkeyup="myFunction()" placeholder="Search for names.." title="Type in a name">'
    txt = txt + '<p><button onclick="sortTable()">Sort</button></p>'
    txt = txt + '<table id="myTable">'
    txt = txt + '<tr class="header">'
    txt = txt + '<th> ICOA </th>'
    txt = txt + '<th> flight </th>'
    txt = txt + '<th> tail </th>'
    txt = txt + '<th> closest </th>'
#    txt = txt + '<th> nearest </th>'
    txt = txt + '<th> cur dist </th>'
    txt = txt + '<th> type </th>'
    txt = txt + '<th> alt </th>'
    txt = txt + '<th> clat </th>'
    txt = txt + '<th> clon </th>'
    txt = txt + '<th> route </th>'
    txt = txt + '</tr>'
    for plane in planes:
        p = planes[plane]
        txt = txt + '<tr>'
        for item in ['icoa','flight','tail','closest_miles','current_miles','plane','alt_baro','closest_lat','closest_lon','route']:
            txt = txt + '<td>'
            if item in p:
                if type(p[item]) == float:
                    txt = txt + "{:>3.2f}".format(p[item])
                else:
                    txt = txt + str(p[item])
            txt = txt + '</td>'
        txt = txt + '</tr>'
    return  txt


class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global planes
        global lock
        #print("GET python request {} {}".format(self.path,self.headers))
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
            font-size: 12px;
            padding: 12px 20px 12px 40px;
            border: 1px solid #ddd;
            margin-bottom: 12px;
            }

            #myTable {
               border-collapse: collapse;
               width: 100%;
               border: 1px solid #ddd;
               font-size: 14;
            }

            #myTable th, #myTable td {
                text-align: left;
                padding: 2px;
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
var lessormore = 1;

function myFunction() {
          var input, filter, table, tr, td, i, txtValue;
          input = document.getElementById("myInput");
          filter = input.value.toUpperCase();
          table = document.getElementById("myTable");
          tr = table.getElementsByTagName("tr");
          for (i = 1; i < tr.length; i++) {
               txt = ""
               for (j=0;j<9;j++){
                       td = tr[i].getElementsByTagName("td")[j];
                       if (td) {
                          txtValue = td.textContent || td.innerText;
                          txt = txt + " " +  txtValue
                        }
               }
               if (txt.toUpperCase().indexOf(filter) > -1) {
                       tr[i].style.display = "";
               } else {
                       tr[i].style.display = "none";
               }
             }       
             sortTable();
           }
function sortTable() {
    var table, rows, switching, i, x, y, shouldSwitch;
    table = document.getElementById("myTable");
    if ( lessormore == 1 )
        lessormore = 0;
    else 
        lessormore = 1;

    switching = true;
    /* Make a loop that will continue until
    no switching has been done: */
    while (switching) {
    // Start by saying: no switching is done:
        switching = false;
        rows = table.rows;
        /* Loop through all table rows (except the first, which contains table headers): */
        for (i = 1; i < (rows.length - 1); i++) {
            // Start by saying there should be no switching:
            shouldSwitch = false;
            /* Get the two elements you want to compare, one from current row and one from the next: */
            x = rows[i].getElementsByTagName("TD")[3];
            y = rows[i + 1].getElementsByTagName("TD")[3];
            // Check if the two rows should switch place:
            a= parseFloat(x.innerHTML.toLowerCase())
            b= parseFloat(y.innerHTML.toLowerCase())
            if ( lessormore == 1 ){
                if ( a < b ) {
                    // If so, mark as a switch and break the loop:
                    shouldSwitch = true;
                    break;
                }
            }
            else {
                if ( a > b ){
                    // If so, mark as a switch and break the loop:
                    shouldSwitch = true;
                    break;
                }
            }

        }
        if (shouldSwitch) {
            /* If a switch has been marked, make the switch and mark that a switch has been done: */
            rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
            switching = true;
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
    except Exception as e:
        print("failed to start thread {}".format(e))

def update_plane_data(p):
    global planes
    global the_lock
    the_lock.acquire()
    planes = copy.deepcopy(p)
    the_lock.release()
    #print("update plane data for web {} {}".format(len(p),len(planes)))

