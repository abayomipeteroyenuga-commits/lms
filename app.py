"""Account-enabled ETHAN LMS with WSGI deployment, verified email and Paystack."""
from pathlib import Path
import os
ROOT=Path(__file__).resolve().parent
if (ROOT/'.env').exists():
 for line in (ROOT/'.env').read_text().splitlines():
  if line.strip() and not line.lstrip().startswith('#') and '=' in line:
   k,v=line.split('=',1);os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))
import server as legacy
import zipfile
import json,io,time,secrets,hashlib,hmac,sqlite3,urllib.request,urllib.error,re,html
from urllib.parse import urlparse,quote
from flask import Flask,request,jsonify,Response,send_file,redirect,abort
from werkzeug.middleware.proxy_fix import ProxyFix
app=Flask(__name__,static_folder=None);app.config['MAX_CONTENT_LENGTH']=26*1024*1024
if os.environ.get('ETHAN_TRUST_PROXY')=='1':app.wsgi_app=ProxyFix(app.wsgi_app,x_for=1,x_proto=1,x_host=0)
PRODUCTION=os.environ.get('ETHAN_ENV')=='production'
if PRODUCTION:
 if not os.environ.get('ETHAN_BASE_URL','').startswith('https://'):raise RuntimeError('Set an HTTPS ETHAN_BASE_URL before production startup')
 if os.environ.get('ETHAN_SECURE_COOKIE')!='1':raise RuntimeError('Production requires ETHAN_SECURE_COOKIE=1')
 if os.environ.get('ETHAN_REQUIRE_VERIFIED_EMAIL','1')!='1':raise RuntimeError('Production requires verified email access')
BASE_URL=os.environ.get('ETHAN_BASE_URL','http://localhost:8080').rstrip('/')
REQUIRE_VERIFIED=os.environ.get('ETHAN_REQUIRE_VERIFIED_EMAIL','1')=='1'
legacy.initialise()
with legacy.connect() as c:
 c.execute('PRAGMA journal_mode=WAL')
 c.executescript('''CREATE TABLE IF NOT EXISTS user_flags(user_id TEXT PRIMARY KEY,verified INTEGER DEFAULT 0);CREATE TABLE IF NOT EXISTS auth_tokens(hash TEXT PRIMARY KEY,user_id TEXT,kind TEXT,expires REAL,used INTEGER DEFAULT 0,created REAL);CREATE TABLE IF NOT EXISTS prices(course_id TEXT PRIMARY KEY,amount INTEGER,enabled INTEGER DEFAULT 0);CREATE TABLE IF NOT EXISTS payments(reference TEXT PRIMARY KEY,user_id TEXT,course_id TEXT,amount INTEGER,currency TEXT,mode TEXT,status TEXT,email TEXT,created REAL,updated REAL);CREATE TABLE IF NOT EXISTS entitlements(user_id TEXT,course_id TEXT,reference TEXT,status TEXT,PRIMARY KEY(user_id,course_id));CREATE TABLE IF NOT EXISTS rate_limits(key TEXT PRIMARY KEY,window REAL,count INTEGER);CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,actor TEXT,action TEXT,resource TEXT,created REAL);''')
 bootstrap_email=os.environ.get('ETHAN_ADMIN_EMAIL','').strip().lower();bootstrap_pw=os.environ.get('ETHAN_ADMIN_PASSWORD','')
 if bootstrap_email and bootstrap_pw and not c.execute('SELECT 1 FROM users WHERE email=?',(bootstrap_email,)).fetchone():
  if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',bootstrap_email) or not 10<=len(bootstrap_pw)<=256:raise RuntimeError('Invalid bootstrap administrator details')
  uid=secrets.token_hex(12);c.execute('INSERT INTO users VALUES(?,?,?,?,?)',(uid,bootstrap_email,'Ethan Administrator',legacy.password_hash(bootstrap_pw),'admin'));c.execute('INSERT INTO user_flags VALUES(?,1)',(uid,))
def verified(uid):
 with legacy.connect() as c:
  row=c.execute('SELECT verified FROM user_flags WHERE user_id=?',(uid,)).fetchone();return bool(row and row[0])
def public_user(u):return legacy.user_public(u)|{'verified':verified(u['id'])}
class Bridge(legacy.Handler):
 def __init__(self):
  self.headers=request.headers;self.client_address=(request.remote_addr or '',0);self.rfile=io.BytesIO(request.get_data());self.wfile=io.BytesIO();self.status=200;self.response_headers=[]
 def send_response(self,status,*a):self.status=status
 def send_header(self,k,v):self.response_headers.append((k,str(v)))
 def end_headers(self):pass
 def reply(self,status,value,cookie=None):
  if isinstance(value,dict) and value.get('user'):
   with legacy.connect() as c:
    u=c.execute('SELECT * FROM users WHERE id=?',(value['user']['id'],)).fetchone()
   value['user']=public_user(u)
  self.status=status;self.response_headers=[('Content-Type','application/json'),('Cache-Control','no-store')]
  if cookie:self.response_headers.append(('Set-Cookie',cookie))
  self.wfile=io.BytesIO(json.dumps(value).encode())
 def response(self):return Response(self.wfile.getvalue(),status=self.status,headers=self.response_headers)
def who(required=False,admin=False):
 b=Bridge();return b.require(admin) if required else b.user()
def rate(name,limit=10,window=600):
 key=hashlib.sha256((name+'|'+(request.remote_addr or '')).encode()).hexdigest();now=time.time()
 with legacy.connect() as c:
  c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT * FROM rate_limits WHERE key=?',(key,)).fetchone();count=(r['count'] if r and r['window']>now-window else 0)+1;start=r['window'] if r and r['window']>now-window else now
  c.execute('INSERT OR REPLACE INTO rate_limits VALUES(?,?,?)',(key,start,count));c.execute('DELETE FROM rate_limits WHERE window<?',(now-86400,))
 if count>limit:abort(429,description='Too many attempts. Please try again later.')
def all_courses():
 courses={c['id']:c for c in legacy.BASE}
 with legacy.connect() as db:
  for row in db.execute('SELECT value FROM courses'):
   c=json.loads(row[0]);courses[c['id']]={**courses.get(c['id'],{}),**c}
 return courses
def course(cid):
 c=all_courses().get(cid)
 if not c:abort(404,description='Course not found')
 return c
def price(cid):
 with legacy.connect() as c:r=c.execute('SELECT * FROM prices WHERE course_id=?',(cid,)).fetchone()
 return {'amount':r['amount'] if r else None,'currency':'NGN','enabled':bool(r and r['enabled'])}
def allowed(u,cid):
 if u and u['role']=='admin':return True
 if not u or (REQUIRE_VERIFIED and not verified(u['id'])):return False
 p=price(cid)
 if p['enabled'] and p['amount']==0:return True
 with legacy.connect() as db:r=db.execute('SELECT status FROM entitlements WHERE user_id=? AND course_id=?',(u['id'],cid)).fetchone()
 return bool(r and r[0]=='active')
def metadata(c):
 return {k:c[k] for k in ['id','title','category','description','project','level','color','prerequisites'] if k in c}|{'lesson_count':len(c['lessons']),'lesson_titles':[l['title'] for l in c['lessons']],'content_kind':'Course-specific','price':price(c['id'])}
def log(actor,action,resource):
 with legacy.connect() as c:c.execute('INSERT INTO audit(actor,action,resource,created) VALUES(?,?,?,?)',(actor,action,resource,time.time()))
def provider(url,key,payload=None):
 raw=json.dumps(payload).encode() if payload is not None else None;req=urllib.request.Request(url,data=raw,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','User-Agent':'ETHAN-LMS/3.0'},method='POST' if raw is not None else 'GET')
 try:
  with urllib.request.urlopen(req,timeout=15) as r:return json.load(r)
 except (urllib.error.URLError,TimeoutError,ValueError) as e:raise RuntimeError('Provider request failed. Check provider configuration and logs.') from e

def send_auth_email(u,kind):
 key=os.environ.get('RESEND_API_KEY','');sender=os.environ.get('ETHAN_EMAIL_FROM','')
 if not key or not sender:abort(503,description='Email delivery is not configured. The administrator must set the Resend key and a verified sender.')
 rate('auth-mail:'+u['id']+':'+kind,limit=3,window=600)
 token=secrets.token_urlsafe(32);hashed=hashlib.sha256(token.encode()).hexdigest();expires=time.time()+(86400 if kind=='verify' else 1800)
 with legacy.connect() as c:
  c.execute('BEGIN IMMEDIATE');c.execute('UPDATE auth_tokens SET used=1 WHERE user_id=? AND kind=?',(u['id'],kind));c.execute('INSERT INTO auth_tokens VALUES(?,?,?,?,0,?)',(hashed,u['id'],kind,expires,time.time()));c.execute('DELETE FROM auth_tokens WHERE expires<?',(time.time()-86400,))
 link=BASE_URL+'/#'+kind+'/'+token;title='Verify your ETHAN LMS email' if kind=='verify' else 'Reset your ETHAN LMS password';label='Verify email' if kind=='verify' else 'Reset password'
 try:
  result=provider('https://api.resend.com/emails',key,{'from':sender,'to':[u['email']],'subject':title,'html':f'<h2>{html.escape(title)}</h2><p>Hello {html.escape(u["name"])},</p><p><a href="{html.escape(link)}">{label}</a></p><p>This link expires in {"24 hours" if kind=="verify" else "30 minutes"} and can be used once.</p><p>If you did not request this, ignore this email.</p>','text':title+'\n'+link+'\nThis link is temporary and single-use.'})
  if not result.get('id'):raise RuntimeError('Email provider did not accept the message')
 except Exception:
  with legacy.connect() as c:c.execute('UPDATE auth_tokens SET used=1 WHERE hash=?',(hashed,))
  raise
 log(u['id'],'email-'+kind,'accepted');return result['id']
def use_token(token,kind,password=None):
 if not isinstance(token,str) or not 20<=len(token)<=200:abort(400,description='Invalid or expired link')
 h=hashlib.sha256(token.encode()).hexdigest()
 with legacy.connect() as c:
  c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT * FROM auth_tokens WHERE hash=? AND kind=? AND used=0 AND expires>?',(h,kind,time.time())).fetchone()
  if not r:abort(400,description='Invalid, expired or already used link. Request a new email.')
  if kind=='verify':c.execute('INSERT OR REPLACE INTO user_flags VALUES(?,1)',(r['user_id'],))
  else:
   if not isinstance(password,str) or not 10<=len(password)<=256:abort(400,description='Use a password of 10–256 characters')
   c.execute('UPDATE users SET password=? WHERE id=?',(legacy.password_hash(password),r['user_id']));c.execute('DELETE FROM sessions WHERE user_id=?',(r['user_id'],))
  c.execute('UPDATE auth_tokens SET used=1 WHERE hash=?',(h,))
 return r['user_id']

def settle(ref,data):
 with legacy.connect() as c:
  c.execute('BEGIN IMMEDIATE');p=c.execute('SELECT * FROM payments WHERE reference=?',(ref,)).fetchone()
  if not p:return False
  if data.get('reference')!=ref or data.get('status')!='success' or type(data.get('amount'))!=int or data['amount']!=p['amount'] or data.get('currency')!=p['currency'] or data.get('domain')!=p['mode'] or str(data.get('customer',{}).get('email','')).lower()!=p['email'].lower():raise ValueError('Payment confirmation does not match the recorded purchase')
  if p['status']=='revoked':return False
  c.execute('UPDATE payments SET status=?,updated=? WHERE reference=?',('success',time.time(),ref));c.execute('INSERT OR REPLACE INTO entitlements VALUES(?,?,?,?)',(p['user_id'],p['course_id'],ref,'active'))
 return True

@app.before_request
def checks():
 if os.environ.get('ETHAN_ALLOWED_HOSTS'):
  hosts={h.strip() for h in os.environ['ETHAN_ALLOWED_HOSTS'].split(',')}
  if request.host.split(':')[0] not in hosts:abort(400,description='Unrecognised host')
 if request.method in ['POST','PUT','DELETE','PATCH'] and request.path!='/api/payments/webhook':
  origin=request.headers.get('Origin')
  if origin and urlparse(origin).netloc!=request.host:abort(403,description='Cross-origin writes are blocked')
  if request.path.startswith('/api/') and request.path not in ['/api/payments/webhook'] and not request.is_json and not request.path.startswith('/api/files/'):abort(415,description='Use application/json')
 if request.method in ('POST','PUT','PATCH') and request.is_json and not isinstance(request.get_json(silent=True),dict):abort(400,description='Use a JSON object')
 if request.path in ['/api/login','/api/register']:rate('account',limit=30,window=600)

@app.after_request
def headers(response):
 response.headers['X-Content-Type-Options']='nosniff';response.headers['Referrer-Policy']='same-origin';response.headers['X-Frame-Options']='SAMEORIGIN'
 if request.path.startswith('/api/'):response.headers['Cache-Control']='no-store'
 if PRODUCTION:response.headers['Strict-Transport-Security']='max-age=31536000'
 return response
@app.errorhandler(Exception)
def error(e):
 from werkzeug.exceptions import HTTPException
 if isinstance(e,HTTPException):return jsonify(error=e.description),e.code
 if isinstance(e,PermissionError):return jsonify(error=str(e)),403
 if isinstance(e,(ValueError,KeyError,TypeError,UnicodeError,json.JSONDecodeError)):return jsonify(error=str(e)),400
 if isinstance(e,sqlite3.IntegrityError):return jsonify(error='This record already exists'),409
 if isinstance(e,RuntimeError):return jsonify(error=str(e)),502
 app.logger.exception('Unhandled LMS error');return jsonify(error='The request could not be completed'),500
@app.get('/api/config')
def config():return jsonify(server=True,production=PRODUCTION,require_verified=REQUIRE_VERIFIED,email_ready=bool(os.environ.get('RESEND_API_KEY') and os.environ.get('ETHAN_EMAIL_FROM')),payments_ready=bool(os.environ.get('PAYSTACK_SECRET_KEY')),payment_mode='live' if os.environ.get('PAYSTACK_SECRET_KEY','').startswith('sk_live_') else 'test' if os.environ.get('PAYSTACK_SECRET_KEY','').startswith('sk_test_') else 'unconfigured')
@app.get('/api/health')
def health():
 with legacy.connect() as c:c.execute('SELECT 1').fetchone()
 return jsonify(server=True,version=3)
@app.route('/api/auth/verify',methods=['POST'])
def verify():use_token(request.get_json().get('token'),'verify');return jsonify(ok=True)
@app.post('/api/auth/resend')
def resend():u=who(True);send_auth_email(u,'verify');return jsonify(ok=True,message='Verification email accepted by the mail provider.')
@app.post('/api/auth/forgot')
def forgot():
 b=request.get_json();email=str(b.get('email','')).lower().strip();rate('forgot',limit=5,window=600)
 if not os.environ.get('RESEND_API_KEY') or not os.environ.get('ETHAN_EMAIL_FROM'):abort(503,description='Email delivery is not configured')
 with legacy.connect() as c:u=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
 if u:send_auth_email(u,'reset')
 return jsonify(ok=True,message='If that account exists, a reset message has been requested.')
@app.post('/api/auth/reset')
def reset():b=request.get_json();use_token(b.get('token'),'reset',b.get('password'));return jsonify(ok=True)
@app.get('/api/courses')
def catalogue():return jsonify(courses=[metadata(c) for c in all_courses().values()])
@app.get('/api/learning/<cid>')
def learning(cid):
 c=course(cid);u=who();access=allowed(u,cid);m=metadata(c);m['lessons']=c['lessons'] if access else [c['lessons'][0]]+[{'title':l['title'],'locked':True} for l in c['lessons'][1:]];m['access']={'allowed':access,'verified':bool(u and verified(u['id'])),'signed_in':bool(u)};return jsonify(course=m)
@app.get('/api/admin/curriculum')
def admin_curriculum():who(True,True);return jsonify(courses=list(all_courses().values()))
@app.get('/api/teaching/<cid>/<kind>')
def teaching(cid,kind):
 c=course(cid)
 if kind not in ['pdf','video']:abort(404)
 if kind=='pdf' and not allowed(who(),cid):abort(403,description='Verify your email and obtain course access to download this study guide')
 # Overview videos introduce the curriculum; detailed PDF notes are protected.
 rel=c.get(kind)
 if not rel:abort(404,description='Teaching media is not available for this custom course')
 f=(ROOT/rel).resolve()
 if ROOT/'teaching' not in f.parents:abort(404)
 archive=ROOT/'teaching'/f'pack-{(int(cid[1:])-1)%55:02d}.zip'
 if not f.exists():
  try:
   with zipfile.ZipFile(archive) as z:media=io.BytesIO(z.read(rel))
  except (OSError,KeyError,ValueError):abort(404)
 else:media=f
 return send_file(media,mimetype='application/pdf' if kind=='pdf' else 'video/mp4',conditional=True,as_attachment=kind=='pdf' and request.args.get('inline')!='1',download_name=c['title'].replace('/','-')+('.pdf' if kind=='pdf' else '.mp4'))
@app.get('/api/prices')
def prices():return jsonify(prices={cid:price(cid) for cid in all_courses()})
@app.put('/api/prices/<cid>')
def set_price(cid):
 u=who(True,True);course(cid);b=request.get_json();amount=b.get('amount');enabled=b.get('enabled')
 if type(amount)!=int or not 0<=amount<=100_000_000 or type(enabled)!=bool:abort(400,description='Use a price in kobo from 0 to 100000000 and an enabled boolean')
 with legacy.connect() as c:c.execute('INSERT OR REPLACE INTO prices VALUES(?,?,?)',(cid,amount,int(enabled)))
 log(u['id'],'price-update',cid);return jsonify(ok=True,price=price(cid))
@app.get('/api/payments')
def payments():
 u=who(True)
 with legacy.connect() as c:
  rows=c.execute('SELECT * FROM payments'+('' if u['role']=='admin' else ' WHERE user_id=?')+' ORDER BY created DESC',() if u['role']=='admin' else (u['id'],)).fetchall()
 return jsonify(payments=[dict(r) for r in rows])
@app.post('/api/payments/checkout')
def checkout():
 u=who(True);cid=str(request.get_json().get('course_id',''));course(cid);p=price(cid)
 if REQUIRE_VERIFIED and not verified(u['id']):abort(403,description='Verify your email before purchasing a course')
 if allowed(u,cid):abort(409,description='You already have access to this course')
 if not p['enabled'] or not p['amount']:abort(400,description='This course is not available for paid checkout')
 secret=os.environ.get('PAYSTACK_SECRET_KEY','')
 if not secret.startswith(('sk_test_','sk_live_')):abort(503,description='Paystack checkout is not configured')
 rate('checkout:'+u['id'],limit=10,window=600);ref='ethan-'+secrets.token_hex(16);mode='live' if secret.startswith('sk_live_') else 'test';now=time.time()
 with legacy.connect() as c:c.execute('INSERT INTO payments VALUES(?,?,?,?,?,?,?,?,?,?)',(ref,u['id'],cid,p['amount'],'NGN',mode,'pending',u['email'],now,now))
 try:
  r=provider('https://api.paystack.co/transaction/initialize',secret,{'email':u['email'],'amount':str(p['amount']),'currency':'NGN','reference':ref,'callback_url':BASE_URL+'/payment-return','metadata':json.dumps({'course_id':cid,'user_id':u['id']})})
  url=r.get('data',{}).get('authorization_url','');parsed=urlparse(url)
  if not r.get('status') or parsed.scheme!='https' or parsed.hostname!='checkout.paystack.com':raise RuntimeError('Payment provider did not return a valid checkout URL')
 except Exception:
  with legacy.connect() as c:c.execute('UPDATE payments SET status=? WHERE reference=?',('initialisation_failed',ref))
  raise
 return jsonify(reference=ref,authorization_url=url,mode=mode)
@app.post('/api/payments/verify/<ref>')
def payment_verify(ref):
 u=who(True);rate('verify-payment:'+u['id'],limit=30,window=600)
 with legacy.connect() as c:p=c.execute('SELECT * FROM payments WHERE reference=? AND user_id=?',(ref,u['id'])).fetchone()
 if not p:abort(404,description='Purchase not found')
 secret=os.environ.get('PAYSTACK_SECRET_KEY','')
 if not secret:abort(503,description='Paystack is not configured')
 r=provider('https://api.paystack.co/transaction/verify/'+quote(ref,safe=''),secret)
 if not r.get('status'):abort(502,description='Payment provider could not confirm the transaction')
 d=r.get('data',{})
 if d.get('status')!='success':return jsonify(status=d.get('status','pending'),access=False)
 granted=settle(ref,d);return jsonify(status='success' if granted else 'revoked',access=granted,course_id=p['course_id'])
@app.post('/api/payments/webhook')
def webhook():
 secret=os.environ.get('PAYSTACK_SECRET_KEY','')
 if not secret:abort(503)
 raw=request.get_data();signature=hmac.new(secret.encode(),raw,hashlib.sha512).hexdigest()
 if not hmac.compare_digest(signature,request.headers.get('x-paystack-signature','')):abort(403,description='Invalid webhook signature')
 b=json.loads(raw);event=b.get('event');data=b.get('data',{})
 if event=='charge.success':settle(str(data.get('reference','')),data)
 # Refunds and disputes are reconciled by the administrator; no fake refund button.
 return jsonify(ok=True)
@app.post('/api/payments/revoke/<ref>')
def revoke(ref):
 u=who(True,True)
 with legacy.connect() as c:
  c.execute('BEGIN IMMEDIATE');r=c.execute('UPDATE payments SET status=?,updated=? WHERE reference=?',('revoked',time.time(),ref))
  if not r.rowcount:abort(404)
  c.execute('UPDATE entitlements SET status=? WHERE reference=?',('revoked',ref))
 log(u['id'],'payment-access-revoked',ref);return jsonify(ok=True)
@app.get('/payment-return')
def payment_return():return redirect('/#billing/'+quote(request.args.get('reference',''),safe=''))
@app.route('/api/<path:sub>',methods=['GET','POST','PUT','DELETE'])
def legacy_api(sub):
 # Authorised shared media must obey the same paid-access boundary as course notes.
 b=Bridge()
 if sub.startswith('files/shared/') and request.method=='GET':
  file_key=sub.split('/',2)[2];match=re.match(r'(.+)-\d+-(pdf|video)$',file_key)
  if not match or not allowed(who(),match[1]):abort(403,description='Course access required')
 if sub=='files' and request.method=='GET':
  u=who(True)
  with legacy.connect() as c:files=[dict(r) for r in c.execute('SELECT owner,key,name,mime,length(value) AS size FROM files WHERE owner IN (?,?)',(u['id'],'shared'))]
  files=[f for f in files if f['owner']!='shared' or (re.match(r'(.+)-\d+-(pdf|video)$',f['key']) and allowed(u,re.match(r'(.+)-\d+-(pdf|video)$',f['key'])[1]))];return jsonify(files=files)
 b.api(request.method,'/api/'+sub)
 if sub=='register' and b.status==200:
  result=json.loads(b.wfile.getvalue());uid=result['user']['id']
  with legacy.connect() as c:c.execute('INSERT OR IGNORE INTO user_flags VALUES(?,0)',(uid,))
 return b.response()
@app.get('/courses.js')
def courses_js():return Response('window.COURSES = '+json.dumps([metadata(c) for c in all_courses().values()])+';',mimetype='application/javascript')
@app.get('/')
def index():return send_file(ROOT/'index.html')
@app.get('/<path:filename>')
def static(filename):
 allowed_files={'index.html','styles.css','app.js','courses.js','foundations.js','manifest.json','sw.js','commerce.js','assets/ethan-lms-logo.png'}
 if filename not in allowed_files:abort(404)
 return send_file(ROOT/filename)
if __name__=='__main__':app.run(host='127.0.0.1',port=int(os.environ.get('PORT','8080')),debug=False)
