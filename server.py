"""ETHAN LMS optional account server. Python 3.10+, standard library only."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, unquote
from http.cookies import SimpleCookie
import sqlite3, json, os, hashlib, secrets, time, re, argparse, getpass, mimetypes, threading
ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('ETHAN_DATA_DIR',str(ROOT/'data'))).resolve(); DATA.mkdir(exist_ok=True,parents=True)
DB=DATA/'lms.sqlite3';BASE=json.loads((ROOT/'catalogue.json').read_text());CATS={c['category'] for c in BASE}
LOCK=threading.Lock();ATTEMPTS={}
def connect():
 c=sqlite3.connect(DB,timeout=30);c.row_factory=sqlite3.Row;return c
def initialise():
 with connect() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,email TEXT UNIQUE,name TEXT,password TEXT,role TEXT DEFAULT 'student');CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT,expires REAL);CREATE TABLE IF NOT EXISTS states(user_id TEXT PRIMARY KEY,value TEXT);CREATE TABLE IF NOT EXISTS courses(id TEXT PRIMARY KEY,value TEXT);CREATE TABLE IF NOT EXISTS files(owner TEXT,key TEXT,name TEXT,mime TEXT,value BLOB,PRIMARY KEY(owner,key));CREATE TABLE IF NOT EXISTS assignments(id TEXT PRIMARY KEY,user_id TEXT,course_id TEXT,lesson INTEGER,text TEXT,file_key TEXT,status TEXT,score INTEGER,feedback TEXT,created REAL);''')
def password_hash(password,salt=None):
 salt=salt or secrets.token_hex(16);return salt+':'+hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
def user_public(u):return {k:u[k] for k in ('id','name','email','role')}
def course_validate(v):
 if not isinstance(v,dict) or v.get('id') in ['__proto__','constructor','prototype'] or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',str(v.get('id',''))):raise ValueError('Invalid course ID')
 if v.get('category') not in CATS:raise ValueError('Choose a digital course category')
 for k,maxlen in [('title',160),('description',2000),('project',2000)]:
  if not isinstance(v.get(k),str) or not 1<=len(v[k])<=maxlen:raise ValueError('Invalid '+k)
 lessons=v.get('lessons',[])
 if not isinstance(lessons,list) or not 1<=len(lessons)<=30:raise ValueError('Provide between 1 and 30 lessons')
 for lesson in lessons:
  if not isinstance(lesson,dict):raise ValueError('Invalid lesson')
  for k in ['title','intro','concept','example','task']:
   if not isinstance(lesson.get(k),str) or not 1<=len(lesson[k])<=20000:raise ValueError('Invalid lesson '+k)
  if not isinstance(lesson.get('steps'),list) or not 1<=len(lesson['steps'])<=20 or any(not isinstance(x,str) or len(x)>3000 for x in lesson['steps']):raise ValueError('Invalid workflow')
  qs=lesson.get('quiz',[])
  if not isinstance(qs,list) or not 1<=len(qs)<=20:raise ValueError('Provide quiz questions')
  for q in qs:
   if not isinstance(q,dict) or not isinstance(q.get('question'),str) or not 1<=len(q['question'])<=2000 or not isinstance(q.get('answers'),list) or not 2<=len(q['answers'])<=6 or any(not isinstance(a,str) or len(a)>2000 for a in q['answers']) or type(q.get('correct'))!=int or not 0<=q['correct']<len(q['answers']):raise ValueError('Invalid quiz')
 return {k:v[k] for k in ['id','title','category','description','project','lessons']}|{'level':'Foundation','color':'#e9f1ff'}
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT),**kw)
 def end_headers(self):
  self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','same-origin');self.send_header('X-Frame-Options','SAMEORIGIN');super().end_headers()
 def reply(self,status,value,cookie=None):
  payload=json.dumps(value).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(payload)))
  if cookie:self.send_header('Set-Cookie',cookie)
  self.end_headers();self.wfile.write(payload)
 def user(self):
  cookies=SimpleCookie();cookies.load(self.headers.get('Cookie',''));token=cookies.get('ethan_session');hashed=hashlib.sha256(token.value.encode()).hexdigest() if token else ''
  with connect() as c:return c.execute('SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>?',(hashed,time.time())).fetchone()
 def require(self,admin=False):
  u=self.user()
  if not u:raise PermissionError('Sign in to continue')
  if admin and u['role']!='admin':raise PermissionError('Administrator access required')
  return u
 def body(self,limit=2_000_000):
  n=int(self.headers.get('Content-Length','0'))
  if not 0<n<=limit:raise ValueError('Request is empty or exceeds the size limit')
  return self.rfile.read(n)
 def jsonbody(self):return json.loads(self.body())
 def same_origin(self):
  origin=self.headers.get('Origin')
  if origin and urlparse(origin).netloc!=self.headers.get('Host'):raise PermissionError('Cross-origin writes are blocked')
 def do_GET(self):
  path=urlparse(self.path).path
  if path.startswith('/api/'):
   try:self.api('GET',path)
   except PermissionError as e:self.reply(403,{'error':str(e)})
   except (ValueError,KeyError,TypeError,UnicodeError,json.JSONDecodeError) as e:self.reply(400,{'error':str(e)})
   return
  if path=='/':self.path='/index.html'
  allowed={'index.html','styles.css','app.js','courses.js','foundations.js','catalogue.json','manifest.json','sw.js','README.md','AUDIT.md'}
  rel=unquote(urlparse(self.path).path).lstrip('/')
  if rel not in allowed and rel!='assets/ethan-lms-logo.png':self.send_error(404);return
  super().do_GET()
 def do_HEAD(self):
  rel=unquote(urlparse(self.path).path).lstrip('/')
  if rel not in {'','index.html','styles.css','app.js','courses.js','foundations.js','catalogue.json','manifest.json','sw.js','assets/ethan-lms-logo.png','README.md','AUDIT.md'}:self.send_error(404);return
  super().do_HEAD()
 def do_POST(self):self.write_api('POST')
 def do_PUT(self):self.write_api('PUT')
 def do_DELETE(self):self.write_api('DELETE')
 def write_api(self,method):
  try:self.same_origin();self.api(method,urlparse(self.path).path)
  except PermissionError as e:self.reply(403,{'error':str(e)})
  except (ValueError,KeyError,TypeError,UnicodeError,json.JSONDecodeError) as e:self.reply(400,{'error':str(e)})
  except sqlite3.IntegrityError:self.reply(409,{'error':'This record already exists'})
 def api(self,method,path):
  if path=='/api/health' and method=='GET':self.reply(200,{'server':True});return
  if path=='/api/me' and method=='GET':
   u=self.user();self.reply(200,{'user':user_public(u) if u else None});return
  if path in ['/api/register','/api/login'] and method=='POST':
   b=self.jsonbody();email=str(b.get('email','')).strip().lower();pw=b.get('password','')
   if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or not isinstance(pw,str) or not 10<=len(pw)<=256:raise ValueError('Use a valid email and a password of 10–256 characters')
   key=(self.client_address[0],email)
   with LOCK:
    attempts=[t for t in ATTEMPTS.get(key,[]) if t>time.time()-600]
    if len(attempts)>=15:self.reply(429,{'error':'Too many attempts. Try again in 10 minutes.'});return
    ATTEMPTS[key]=attempts+[time.time()]
   with connect() as c:
    if path=='/api/register':
     name=str(b.get('name','')).strip()
     if not 1<=len(name)<=120:raise ValueError('Enter your name')
     c.execute('INSERT INTO users VALUES(?,?,?,?,?)',(secrets.token_hex(12),email,name,password_hash(pw),'student'))
    u=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
    if not u or not secrets.compare_digest(u['password'],password_hash(pw,u['password'].split(':')[0])):self.reply(401,{'error':'Incorrect email or password'});return
    token=secrets.token_urlsafe(32);c.execute('DELETE FROM sessions WHERE expires<?',(time.time(),));c.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),u['id'],time.time()+86400*7))
   secure='; Secure' if os.environ.get('ETHAN_SECURE_COOKIE')=='1' else ''
   self.reply(200,{'user':user_public(u)},'ethan_session='+token+'; HttpOnly; SameSite=Lax; Path=/; Max-Age=604800'+secure);return
  if path=='/api/logout' and method=='POST':
   cookies=SimpleCookie();cookies.load(self.headers.get('Cookie',''));token=cookies.get('ethan_session')
   if token:
    with connect() as c:c.execute('DELETE FROM sessions WHERE token=?',(hashlib.sha256(token.value.encode()).hexdigest(),))
   self.reply(200,{'ok':True},'ethan_session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0');return
  if path=='/api/state':
   u=self.require()
   with connect() as c:
    if method=='GET':
     row=c.execute('SELECT value FROM states WHERE user_id=?',(u['id'],)).fetchone();self.reply(200,{'state':json.loads(row[0]) if row else None});return
    if method=='PUT':
     b=self.jsonbody()
     if not isinstance(b,dict) or not isinstance(b.get('enrolled'),list) or not isinstance(b.get('notes'),dict) or not isinstance(b.get('completed'),dict):raise ValueError('Invalid learning record')
     c.execute('INSERT OR REPLACE INTO states VALUES(?,?)',(u['id'],json.dumps(b)));self.reply(200,{'ok':True});return
  if path=='/api/courses':
   with connect() as c:
    if method=='GET':self.reply(200,{'courses':[json.loads(x[0]) for x in c.execute('SELECT value FROM courses')]});return
    self.require(True)
    if method=='PUT':
     b=course_validate(self.jsonbody());c.execute('INSERT OR REPLACE INTO courses VALUES(?,?)',(b['id'],json.dumps(b)));self.reply(200,{'ok':True});return
  if path=='/api/assignments':
   u=self.require()
   with connect() as c:
    if method=='GET':
     rows=c.execute('SELECT a.*,u.name,u.email FROM assignments a JOIN users u ON u.id=a.user_id'+('' if u['role']=='admin' else ' WHERE a.user_id=?')+' ORDER BY created DESC',() if u['role']=='admin' else (u['id'],)).fetchall();self.reply(200,{'assignments':[dict(r) for r in rows]});return
    if method=='POST':
     b=self.jsonbody();text=str(b.get('text','')).strip();cid=str(b.get('course_id',''));n=b.get('lesson');file_key=str(b.get('file_key',''))
     known={x['id'] for x in BASE}|{r[0] for r in c.execute('SELECT id FROM courses')}
     if cid not in known or type(n)!=int or not 0<=n<30 or not 20<=len(text)<=20000 or len(file_key)>150:raise ValueError('Provide a valid course, lesson and reflection of at least 20 characters')
     aid=secrets.token_hex(12);c.execute('INSERT INTO assignments VALUES(?,?,?,?,?,?,?,?,?,?)',(aid,u['id'],cid,n,text,file_key,'submitted',None,'',time.time()));self.reply(200,{'id':aid});return
  if path.startswith('/api/assignments/') and method=='PUT':
   self.require(True);b=self.jsonbody();score=b.get('score');feedback=str(b.get('feedback',''))
   if type(score)!=int or not 0<=score<=100 or not 1<=len(feedback)<=5000:raise ValueError('Enter score 0–100 and feedback')
   with connect() as c:
    r=c.execute('UPDATE assignments SET score=?,feedback=?,status=? WHERE id=?',(score,feedback,'reviewed',path.rsplit('/',1)[1]))
    if not r.rowcount:raise ValueError('Assignment not found')
   self.reply(200,{'ok':True});return
  if path=='/api/report' and method=='GET':
   self.require(True)
   with connect() as c:
    users=[user_public(u) for u in c.execute('SELECT * FROM users')];states={r['user_id']:json.loads(r['value']) for r in c.execute('SELECT * FROM states')}
   self.reply(200,{'users':users,'states':states});return
  if path.startswith('/api/files/'):
   u=self.require();bits=unquote(path[len('/api/files/'):]).split('/',1);owner=u['id'];key=bits[-1]
   if len(bits)==2 and bits[0]=='shared':owner='shared'
   elif len(bits)==2:
    if u['role']!='admin':raise PermissionError('Administrator access required')
    owner=bits[0]
   if not re.fullmatch(r'[a-zA-Z0-9_-]{1,150}',key):raise ValueError('Invalid resource key')
   if method in ['PUT','DELETE'] and owner!=u['id']:self.require(True)
   with connect() as c:
    if method=='GET':
     r=c.execute('SELECT * FROM files WHERE owner=? AND key=?',(owner,key)).fetchone()
     if not r:self.reply(404,{'error':'File not found'});return
     self.send_response(200);self.send_header('Content-Type',r['mime']);self.send_header('Content-Length',str(len(r['value'])));self.send_header('Cache-Control','private, no-store');self.send_header('X-File-Name',r['name'].encode('ascii','replace').decode());self.end_headers();self.wfile.write(r['value']);return
    if method=='PUT':
     raw=self.body(25*1024*1024);mime=self.headers.get('Content-Type','application/octet-stream').split(';')[0];name=re.sub(r'[\x00-\x1f\x7f]','',unquote(self.headers.get('X-File-Name','resource')))[:200]
     allowed={'application/pdf','image/png','image/jpeg','image/webp','text/plain','application/zip','video/mp4','video/webm','video/ogg','audio/mpeg','audio/wav'}
     if mime not in allowed:raise ValueError('Unsupported resource format')
     if mime=='application/pdf' and not raw.startswith(b'%PDF-'):raise ValueError('Invalid PDF file')
     used=c.execute('SELECT COALESCE(SUM(length(value)),0) FROM files WHERE owner=? AND key!=?',(owner,key)).fetchone()[0]
     if used+len(raw)>200*1024*1024:raise ValueError('200 MB resource quota reached')
     c.execute('INSERT OR REPLACE INTO files VALUES(?,?,?,?,?)',(owner,key,name,mime,raw));self.reply(200,{'ok':True});return
    if method=='DELETE':c.execute('DELETE FROM files WHERE owner=? AND key=?',(owner,key));self.reply(200,{'ok':True});return
  if path=='/api/files' and method=='GET':
   u=self.require()
   with connect() as c:rows=[dict(r) for r in c.execute('SELECT owner,key,name,mime,length(value) AS size FROM files WHERE owner IN (?,?)',(u['id'],'shared'))]
   self.reply(200,{'files':rows});return
  self.reply(404,{'error':'Endpoint not found'})
def main():
 initialise();parser=argparse.ArgumentParser();parser.add_argument('--host',default='127.0.0.1');parser.add_argument('--port',type=int,default=8080);group=parser.add_mutually_exclusive_group();group.add_argument('--create-admin',metavar='EMAIL');group.add_argument('--reset-password',metavar='EMAIL');args=parser.parse_args()
 if args.reset_password:
  pw=os.environ.get('ETHAN_RESET_PASSWORD') or getpass.getpass('New password (at least 10 characters): ')
  if not 10<=len(pw)<=256:raise SystemExit('Use 10–256 characters')
  with connect() as c:
   result=c.execute('UPDATE users SET password=? WHERE email=?',(password_hash(pw),args.reset_password.lower().strip()))
   if not result.rowcount:raise SystemExit('Account not found')
   c.execute('DELETE FROM sessions WHERE user_id=(SELECT id FROM users WHERE email=?)',(args.reset_password.lower().strip(),))
  print('Password reset. Existing sessions were invalidated.');return
 if args.create_admin:
  pw=os.environ.get('ETHAN_ADMIN_PASSWORD') or getpass.getpass('Admin password (at least 10 characters): ')
  if not 10<=len(pw)<=256:raise SystemExit('Use 10–256 characters')
  with connect() as c:
   email=args.create_admin.lower().strip()
   existing=c.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()
   if existing:c.execute('UPDATE users SET role=?,password=? WHERE email=?',('admin',password_hash(pw),email))
   else:c.execute('INSERT INTO users VALUES(?,?,?,?,?)',(secrets.token_hex(12),email,'Ethan Administrator',password_hash(pw),'admin'))
  print('Administrator account ready. Start the server without --create-admin.');return
 raise SystemExit('For v3 accounts, payments and verification, run python app.py. The legacy HTTP preview server is not a production entry point.')
if __name__=='__main__':main()
