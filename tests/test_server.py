import urllib.request,urllib.error,http.cookiejar,json,time
import os,sys,threading,importlib.util,tempfile
from pathlib import Path
temporary=tempfile.TemporaryDirectory(prefix='ethan-lms-test-')
ROOT=Path(__file__).resolve().parents[1]
os.environ['ETHAN_DATA_DIR']=temporary.name
spec=importlib.util.spec_from_file_location('ethan_server',str(ROOT/'server.py'));srv=importlib.util.module_from_spec(spec);spec.loader.exec_module(srv);srv.initialise()
with srv.connect() as c:
 c.execute("INSERT OR REPLACE INTO users VALUES(?,?,?,?,?)",('admin-test','admin@example.test','Admin',srv.password_hash('TestAdmin12345'),'admin'))
srv.Handler.log_message=lambda *a:None
testhttp=srv.ThreadingHTTPServer(('127.0.0.1',0),srv.Handler);threading.Thread(target=testhttp.serve_forever,daemon=True).start()
BASE='http://127.0.0.1:'+str(testhttp.server_port)
def client():return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def request(c,path,method='GET',data=None,headers=None):
 raw=json.dumps(data).encode() if isinstance(data,(dict,list)) else data
 h=headers or {}
 if isinstance(data,(dict,list)):h={'Content-Type':'application/json',**h}
 try:
  r=c.open(urllib.request.Request(BASE+path,data=raw,method=method,headers=h));return r.status,r.read(),r.headers
 except urllib.error.HTTPError as e:return e.code,e.read(),e.headers
admin=client();a=client();b=client();stamp=str(int(time.time()*1000))
assert request(admin,'/api/login','POST',{'email':'admin@example.test','password':'TestAdmin12345'})[0]==200
for c,name in [(a,'alice'),(b,'bob')]:
 assert request(c,'/api/register','POST',{'email':name+stamp+'@example.test','name':name,'password':'StudentPass12345'})[0]==200
assert json.loads(request(a,'/api/me')[1])['user']['role']=='student'
assert request(a,'/api/report')[0]==403
assert request(a,'/api/courses','PUT',{})[0]==403
state={'enrolled':['c011'],'notes':{'c011-0':'A private reflection belonging to Alice.'},'completed':{'c011':[0]}}
assert request(a,'/api/state','PUT',state)[0]==200
assert json.loads(request(a,'/api/state')[1])['state']==state
assert json.loads(request(b,'/api/state')[1])['state'] is None
assert request(a,'/api/state','PUT',state,{'Origin':'https://other.example'})[0]==403
pdf=b'%PDF-1.4\n%%EOF';headers={'Content-Type':'application/pdf','X-File-Name':'sample.pdf'}
assert request(a,'/api/files/c011-0-pdf','PUT',pdf,headers)[0]==200
assert request(a,'/api/files/c011-0-pdf')[1]==pdf
assert request(b,'/api/files/c011-0-pdf')[0]==404
assert request(a,'/api/files/shared/c011-0-pdf','PUT',pdf,headers)[0]==403
assert request(admin,'/api/files/shared/c011-0-pdf','PUT',pdf,headers)[0]==200
assert request(b,'/api/files/shared/c011-0-pdf')[1]==pdf
assert request(a,'/api/files/bad-pdf','PUT',b'not a pdf',headers)[0]==400
assert request(a,'/api/files/script','PUT',b'<script>bad</script>',{'Content-Type':'text/html'})[0]==400
r=request(a,'/api/assignments','POST',{'course_id':'c011','lesson':0,'text':'I built a profile and tested keyboard navigation.','file_key':'c011-0-pdf'});assert r[0]==200;aid=json.loads(r[1])['id']
assert request(b,'/api/assignments/'+aid,'PUT',{'score':90,'feedback':'Good work.'})[0]==403
assert request(admin,'/api/assignments/'+aid,'PUT',{'score':90,'feedback':'Good semantic structure. Improve the image description.'})[0]==200
assert json.loads(request(a,'/api/assignments')[1])['assignments'][0]['score']==90
assert json.loads(request(b,'/api/assignments')[1])['assignments']==[]
course={'id':'test-digital','title':'Digital practice course','category':'Web Development','description':'An authored digital lesson.','project':'Create a webpage.','lessons':[{'title':'HTML','intro':'Learn HTML.','concept':'HTML gives structure.','steps':['Create a file.'],'example':'<h1>Hello</h1>','task':'Create a page.','quiz':[{'question':'Which tag is a heading?','answers':['h1','p'],'correct':0,'explanation':'h1 is a heading.'}]}]}
assert request(admin,'/api/courses','PUT',course)[0]==200
assert any(c['id']=='test-digital' for c in json.loads(request(b,'/api/courses')[1])['courses'])
invalid={**course,'category':'Mathematics'};assert request(admin,'/api/courses','PUT',invalid)[0]==400
for path in ['/data/lms.sqlite3','/server.py','/../qa/server-data/lms.sqlite3']:
 assert request(a,path)[0]==404
 assert request(a,path,'HEAD')[0]==404
assert request(a,'/api/files/c011-0-pdf','DELETE')[0]==200
assert request(a,'/api/files/c011-0-pdf')[0]==404
assert request(a,'/api/logout','POST',{})[0]==200
assert json.loads(request(a,'/api/me')[1])['user'] is None
assert request(a,'/api/state')[0]==403
print('PASS: registration, login/logout, roles, user state/file isolation, CSRF rejection, published resources, format checks, assignment review, course authoring, digital-only categories, private-file protection.')

testhttp.shutdown();testhttp.server_close();temporary.cleanup()
