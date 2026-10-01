"""Production app integration tests. All provider calls are mocked; no money or email is sent."""
from pathlib import Path
import os,tempfile,sys,json,re,hmac,hashlib,time
TMP=tempfile.TemporaryDirectory(prefix='ethan-v3-test-');ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ['ETHAN_DATA_DIR']=TMP.name;os.environ['ETHAN_ENV']='development';os.environ['ETHAN_SECURE_COOKIE']='0';os.environ['ETHAN_REQUIRE_VERIFIED_EMAIL']='1';os.environ['ETHAN_BASE_URL']='http://localhost:8080';os.environ['ETHAN_ADMIN_EMAIL']='admin@example.test';os.environ['ETHAN_ADMIN_PASSWORD']='AdminPass12345';os.environ.pop('PAYSTACK_SECRET_KEY',None);os.environ.pop('RESEND_API_KEY',None)
import app as a
a.app.config['TESTING']=True;admin=a.app.test_client();alice=a.app.test_client();bob=a.app.test_client();anonymous=a.app.test_client()
def post(c,url,data):return c.post(url,json=data)
def verify_email(c):
 assert post(c,'/api/auth/resend',{}).status_code==200
 token=re.search(r'/#verify/([\w-]+)',mail[-1]['text']).group(1)
 assert post(c,'/api/auth/verify',{'token':token}).status_code==200
 assert post(c,'/api/auth/verify',{'token':token}).status_code==400
 return token
assert post(admin,'/api/login',{'email':'admin@example.test','password':'AdminPass12345'}).status_code==200
for c,name in [(alice,'Alice'),(bob,'Bob')]:assert post(c,'/api/register',{'email':name.lower()+'@example.test','name':name,'password':'StudentPass12345'}).status_code==200
assert not alice.get('/api/me').json['user']['verified']
assert post(alice,'/api/auth/resend',{}).status_code==503
assert anonymous.get('/catalogue.json').status_code==404
assert anonymous.get('/teaching/pdfs/c011.pdf').status_code==404
assert anonymous.get('/server.py').status_code==404
assert anonymous.get('/api/teaching/c011/pdf').status_code==403
assert anonymous.get('/api/teaching/c011/video',headers={'Range':'bytes=0-99'}).status_code==206
assert anonymous.get('/app.py').status_code==404
assert anonymous.get('/api/admin/curriculum').status_code==403
metadata=anonymous.get('/courses.js').text;assert '"concept"' not in metadata and '"quiz"' not in metadata
preview=anonymous.get('/api/learning/c011').json['course'];assert not preview['access']['allowed'] and preview['lessons'][1]['locked'];assert 'concept' not in preview['lessons'][1]
assert alice.put('/api/prices/c011',json={'amount':500000,'enabled':True}).status_code==403
assert admin.put('/api/prices/c011',json={'amount':500000,'enabled':True}).status_code==200
assert post(alice,'/api/payments/checkout',{'course_id':'c011'}).status_code==403
mail=[];transactions={};wrong=False
os.environ['RESEND_API_KEY']='re_mock_test_only';os.environ['ETHAN_EMAIL_FROM']='Ethan <no-reply@example.test>'
def mock(url,key,payload=None):
 if url.endswith('/emails'):mail.append(payload);return {'id':'mock-mail-id'}
 if url.endswith('/initialize'):
  transactions[payload['reference']]={'reference':payload['reference'],'amount':int(payload['amount']),'currency':payload['currency'],'status':'success','domain':'test','customer':{'email':payload['email']}}
  return {'status':True,'data':{'authorization_url':'https://checkout.paystack.com/mock-checkout'}}
 if '/verify/' in url:
  ref=url.rsplit('/',1)[1];data=dict(transactions[ref]);data['amount']=1 if wrong else data['amount'];return {'status':True,'data':data}
 raise AssertionError(url)
a.provider=mock
verify_email(alice);assert alice.get('/api/me').json['user']['verified']
assert post(alice,'/api/payments/checkout',{'course_id':'c011'}).status_code==503
os.environ['PAYSTACK_SECRET_KEY']='sk_test_mock_test_only'
checkout=post(alice,'/api/payments/checkout',{'course_id':'c011','amount':1});assert checkout.status_code==200;ref=checkout.json['reference'];assert transactions[ref]['amount']==500000
assert not alice.get('/api/learning/c011').json['course']['access']['allowed']
wrong=True;assert post(alice,'/api/payments/verify/'+ref,{}).status_code==400;assert not alice.get('/api/learning/c011').json['course']['access']['allowed']
wrong=False;assert post(bob,'/api/payments/verify/'+ref,{}).status_code==404
verified=post(alice,'/api/payments/verify/'+ref,{});assert verified.status_code==200 and verified.json['access']
assert alice.get('/api/learning/c011').json['course']['access']['allowed'];assert 'concept' in alice.get('/api/learning/c011').json['course']['lessons'][1]
assert not bob.get('/api/learning/c011').json['course']['access']['allowed']
assert post(alice,'/api/payments/checkout',{'course_id':'c011'}).status_code==409
raw=json.dumps({'event':'charge.success','data':transactions[ref]}).encode();sig=hmac.new(os.environ['PAYSTACK_SECRET_KEY'].encode(),raw,hashlib.sha512).hexdigest()
assert anonymous.post('/api/payments/webhook',data=raw,headers={'Content-Type':'application/json','x-paystack-signature':'bad'}).status_code==403
for i in range(2):assert anonymous.post('/api/payments/webhook',data=raw,headers={'Content-Type':'application/json','x-paystack-signature':sig}).status_code==200
with a.legacy.connect() as c:assert c.execute('SELECT count(*) FROM entitlements').fetchone()[0]==1
assert post(bob,'/api/payments/revoke/'+ref,{}).status_code==403
assert post(admin,'/api/payments/revoke/'+ref,{}).status_code==200
assert not alice.get('/api/learning/c011').json['course']['access']['allowed']
assert anonymous.post('/api/payments/webhook',data=raw,headers={'Content-Type':'application/json','x-paystack-signature':sig}).status_code==200
assert not alice.get('/api/learning/c011').json['course']['access']['allowed']
assert admin.put('/api/prices/c013',json={'amount':0,'enabled':True}).status_code==200
assert alice.get('/api/learning/c013').json['course']['access']['allowed']
assert alice.get('/api/teaching/c013/pdf').status_code==200
assert alice.get('/api/teaching/c013/pdf').data.startswith(b'%PDF-')
assert not bob.get('/api/learning/c013').json['course']['access']['allowed']
assert post(alice,'/api/auth/forgot',{'email':'alice@example.test'}).status_code==200
token=re.search(r'/#reset/([\w-]+)',mail[-1]['text']).group(1)
assert post(anonymous,'/api/auth/reset',{'token':token,'password':'short'}).status_code==400
assert post(anonymous,'/api/auth/reset',{'token':token,'password':'ChangedPass12345'}).status_code==200
assert alice.get('/api/me').json['user'] is None
assert post(anonymous,'/api/auth/reset',{'token':token,'password':'ChangedAgain12345'}).status_code==400
assert post(alice,'/api/login',{'email':'alice@example.test','password':'ChangedPass12345'}).status_code==200
# Expired links are not accepted.
assert post(bob,'/api/auth/resend',{}).status_code==200
token=re.search(r'/#verify/([\w-]+)',mail[-1]['text']).group(1)
with a.legacy.connect() as c:c.execute('UPDATE auth_tokens SET expires=? WHERE hash=?',(time.time()-1,hashlib.sha256(token.encode()).hexdigest()))
assert post(anonymous,'/api/auth/verify',{'token':token}).status_code==400
# Browser-origin protections apply to payment and account writes.
assert admin.put('/api/prices/c011',json={'amount':1,'enabled':True},headers={'Origin':'https://other.example'}).status_code==403
print('PASS: draft/default access, protected curriculum/media paths, admin prices, verification/replay/expiry, password reset/session invalidation, provider-unconfigured errors, server-owned checkout amount, ownership, mismatched amount rejection, confirmed access, signed/idempotent webhook, revocation and free verified access. Provider calls mocked; no live transactions or emails.')
TMP.cleanup()
