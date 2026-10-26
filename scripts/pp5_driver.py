"""Version-bound PP5 automation. Writes numeric settings; reads native results."""
import ctypes as c
from ctypes import wintypes as w
import hashlib,json,pathlib,struct,sys,time,re,math
u=c.WinDLL('user32',use_last_error=True);k=c.WinDLL('kernel32',use_last_error=True)
CB=c.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
APP=pathlib.Path(r'C:\.Primer Premier 5')
LARGE_SEARCH_ALLOWED=False;SEARCH_WARNINGS=[]
SHA='024eea91d0e65f068784f93760fa27eb7d4ab69f642404c26049ad0d3112e4c8'
if hashlib.sha256((APP/'Primer Premier 5.exe').read_bytes()).hexdigest()!=SHA:raise ValueError('Unsupported PP5 binary')
if not (APP/'codex-isolated-test.marker').is_file():raise ValueError('Only an explicitly marked isolated automation bottle is allowed')
def describe(hwnd):
 t=c.create_unicode_buffer(2048);cl=c.create_unicode_buffer(256);pid=w.DWORD()
 u.GetWindowTextW(hwnd,t,2048);u.GetClassNameW(hwnd,cl,256);u.GetWindowThreadProcessId(hwnd,c.byref(pid))
 return dict(hwnd=hwnd,title=t.value,cls=cl.value,pid=pid.value,visible=bool(u.IsWindowVisible(hwnd)),enabled=bool(u.IsWindowEnabled(hwnd)),id=u.GetDlgCtrlID(hwnd))
def windows(parent=None):
 out=[]
 @CB
 def cb(hwnd,lp):out.append(describe(hwnd));return True
 if parent is None:u.EnumWindows(cb,0)
 else:u.EnumChildWindows(parent,cb,0)
 return out
if len(sys.argv)>1 and sys.argv[1]=='inventory':
 mains=[x for x in windows() if x['cls'].startswith('xPrimer Premier4580task')]
 pathlib.Path(sys.argv[3]).write_text(json.dumps({'mains':mains}))
 sys.exit(0)
deadline=time.monotonic()+25
while True:
 mains=[x for x in windows() if x['cls'].startswith('xPrimer Premier4580task')]
 if mains or time.monotonic()>deadline:break
 time.sleep(.2)
if len(mains)!=1:raise ValueError('Expected one PP5 process')
main=mains[0];PID=main['pid'];h=k.OpenProcess(0x438,False,PID)
if not h:raise c.WinError(c.get_last_error())
def rd(a,n):
 if n<0 or n>1048576:raise ValueError('Read budget')
 b=c.create_string_buffer(n);got=w.DWORD()
 if not k.ReadProcessMemory(h,a,b,n,c.byref(got)) or got.value!=n:raise c.WinError(c.get_last_error())
 return b.raw
def integer(a):return struct.unpack('<I',rd(a,4))[0]
def number(a):return struct.unpack('<f',rd(a,4))[0]
def wr(a,data):
 b=c.create_string_buffer(data);got=w.DWORD()
 if not k.WriteProcessMemory(h,a,b,len(data),c.byref(got)) or got.value!=len(data):raise c.WinError(c.get_last_error())
def sm(hwnd,msg,wp=0,lp=0):
 val=w.DWORD()
 if not u.SendMessageTimeoutW(hwnd,msg,wp,lp,2,1500,c.byref(val)):raise c.WinError(c.get_last_error())
 return c.c_int32(val.value).value
def post(hwnd,msg,wp=0,lp=0):
 if not u.PostMessageW(hwnd,msg,wp,lp):raise c.WinError(c.get_last_error())
def wait(fn,timeout=35):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  value=fn()
  if value:return value
  time.sleep(.1)
 raise TimeoutError('PP5 state transition timed out; visible='+json.dumps(allvisible()))
def allvisible():
 out=[]
 for d in windows():
  if d['pid']==PID and d['visible']:
   out.append(d);out.extend(x for x in windows(d['hwnd']) if x['visible'])
 return out
def find(title):
 return next((x for x in allvisible() if x['title']==title),None)
def fail_modals():
 ds=[d for d in windows() if d['pid']==PID and d['visible'] and d['cls']=='#32770']
 if ds:
  for d in ds:d['controls']=[x['title'] for x in windows(d['hwnd']) if x['title']]
  known='More than 30000 possible primers. Optimal primer search will be exceedingly time consuming.'
  if not LARGE_SEARCH_ALLOWED or not all(any(t.startswith(known) for t in d['controls']) for d in ds):
   raise RuntimeError('Unexpected modal dialog: '+json.dumps(ds))
  for d in ds:
   if not d['enabled']:continue
   buttons=[x for x in windows(d['hwnd']) if x['cls']=='Button' and x['title']=='&Search' and x['enabled']]
   if len(buttons)!=1:raise RuntimeError('Known large-search warning lacks one enabled Search button')
   SEARCH_WARNINGS.extend(t for t in d['controls'] if t.startswith(known));post(buttons[0]['hwnd'],0xf5)
  time.sleep(.1)
def command(hwnd,cmd):fail_modals();post(hwnd,0x111,cmd)
def enter(hwnd):post(hwnd,0x100,13,1);post(hwnd,0x102,13,1);post(hwnd,0x101,13,0xC0000001)
def obj(hwnd,vtable=None):
 p=integer(u.GetWindowLongW(hwnd,-21)+0x14)
 if vtable and integer(p)!=vtable:raise ValueError('Unexpected PWR object')
 return p
def settings(dialog,parameter_offset=0xf0):
 p=obj(dialog['hwnd']);params=integer(p+parameter_offset);doc=integer(p+0x8c)
 if integer(params)!=0x53fde8 or integer(doc)!=0x548bb8:raise ValueError('Parameter/doc layout mismatch')
 out={'mode':integer(params+0xc),'nominal_length':integer(params+0x18),'length_tolerance':integer(params+0x1c),'tm_min':number(params+0x30),'tm_max':number(params+0x34),'gc_min':number(params+0x38),'gc_max':number(params+0x3c),'product_min':integer(doc+0x68),'product_max':integer(doc+0x6c)}
 return out,doc

def prepare(request):
 wait(lambda:u.IsWindowVisible(main['hwnd']) and u.IsWindowEnabled(main['hwnd']) and u.GetMenu(main['hwnd']))
 # The XVT task window is created before its initial event loop finishes.
 time.sleep(2)
 seq=request['expected_sequence']
 if not re.fullmatch('[ACGT]+',seq):raise ValueError('Unambiguous DNA is required')
 alias='codex_'+hashlib.sha256(seq.encode()).hexdigest()[:12]+'.txt'
 if not any(x['title'].startswith('GeneTank -') for x in allvisible()):
  (APP/alias).write_text('>CODEx_PP5_'+hashlib.sha256(seq.encode()).hexdigest()[:12]+'\n'+seq+'\n')
  d=find('Select Multiple DNA Files')
  if not d:
   command(main['hwnd'],120);d=wait(lambda:find('Select Multiple DNA Files'))
  value=c.create_unicode_buffer(alias)
  def ready_lists():
   controls=windows(d['hwnd']);matches=[]
   if len([x for x in controls if x['cls']=='ListBox'])!=2:return None
   for x in controls:
    if x['cls']=='ListBox':
     ix=sm(x['hwnd'],0x1a2,-1,c.cast(value,c.c_void_p).value)
     if ix>=0:matches.append((x,ix))
   return (controls,matches) if len(matches)==1 else None
  children,matches=wait(ready_lists)
  lb,ix=matches[0];sm(lb['hwnd'],0x185,1,ix)
  if sm(lb['hwnd'],0x187,ix)!=1:raise ValueError('File not selected')
  post(d['hwnd'],0x111,(1<<16)|lb['id'],lb['hwnd'])
  buttons={x['title']:x['hwnd'] for x in children if x['cls']=='Button'}
  post(buttons['Add >>'],0xf5)
  wait(lambda:any(sm(x['hwnd'],0x1a2,-1,c.cast(value,c.c_void_p).value)>=0 for x in children if x['cls']=='ListBox' and x['hwnd']!=lb['hwnd']))
  post(buttons['OK'],0xf5)
  wait(lambda:any(x['title'].startswith('GeneTank -') for x in allvisible()))
 primer=find('Primer Premier')
 # Select the document, not the main application frame, which has the same title.
 primer=next((x for x in allvisible() if x['title']=='Primer Premier' and 'doc' in x['cls']),None)
 if not primer:
  command(main['hwnd'],546)
  primer=wait(lambda:next((x for x in allvisible() if x['title']=='Primer Premier' and 'doc' in x['cls']),None))
 window=obj(primer['hwnd']);doc=integer(window+0x8c)
 if integer(doc)!=0x548bb8:raise ValueError('DNA document mismatch')
 if rd(integer(doc+0x48),integer(doc+0x4c)).decode('ascii')!=seq:raise ValueError('Loaded template differs from request')
 if find('Search Progress'):raise ValueError('Finish the previous search before configuring another')
 previous=find('Search Criteria')
 if previous:
  post(previous['hwnd'],0x10);wait(lambda:not find('Search Criteria'))
 table=APP/'data'/'srchcrit.tbl';original=table.read_bytes()
 if len(original)!=130 or original[:6]!=bytes.fromhex('888800008250'):raise ValueError('Unknown configuration table')
 mapping={'mode':(0xe,'i'),'nominal_length':(0x16,'i'),'length_tolerance':(0x1a,'i'),'tm_min':(0x42,'f'),'tm_max':(0x46,'f'),'gc_min':(0x4a,'f'),'gc_max':(0x4e,'f')}
 data=bytearray(original)
 for key,(off,fmt) in mapping.items():struct.pack_into('<'+fmt,data,off,request[key])
 oldproduct=rd(doc+0x68,8)
 table.write_bytes(data);wr(doc+0x68,struct.pack('<ii',request['product_min'],request['product_max']))
 try:
  command(primer['hwnd'],541);d=wait(lambda:find('Search Criteria'))
  def ready_settings():
   try:
    value=settings(d)
    expected={key:request[key] for key in value[0]}
    return value if value[0]==expected else None
   except (OSError,ValueError):return None
  actual,loaded_doc=wait(ready_settings)
  expected={key:request[key] for key in actual}
  if actual!=expected:raise ValueError('Native readback differs: '+json.dumps(actual))
 except BaseException:
  table.write_bytes(original);wr(doc+0x68,oldproduct);raise
 return dict(phase='prepared',actual=actual,dialog=d['hwnd'],doc=hex(doc),template_sha256=hashlib.sha256(seq.encode()).hexdigest())

def status_text(progress):
 p=obj(progress['hwnd'],0x549258);text=integer(p+0x10c)
 if integer(text)!=0x53d500:raise ValueError('Unexpected native status label')
 # unmpr458 PWR_CText::SetText -> PWR_CView::SetTitle assigns
 # PWR_CStringRW at +0x28. Read that string only, never adjacent objects.
 sp=integer(text+0x28);n=integer(sp-4)
 if n>512:raise ValueError('Status string length exceeds budget')
 value=rd(sp,n).decode('ascii')
 phrases=('Search Complete.','No primers found.','Unable to locate sufficient primers.','Search aborted.')
 return [p for p in phrases if value.startswith(p)]

def extract(seq):
 d=find('Search Results')
 if not d:raise ValueError('Search Results not visible')
 window=obj(d['hwnd'],0x54a388);grid=integer(window+0x100)
 if integer(grid)!=0x54a5f8:raise ValueError('Result grid mismatch')
 doc=integer(grid+0xec);collection=integer(doc+0x70);count=integer(collection+4);arr=integer(collection+12)
 if count>10000:raise ValueError('Result count exceeds budget')
 if rd(integer(doc+0x48),integer(doc+0x4c)).decode('ascii')!=seq:raise ValueError('Result template mismatch')
 def structures(p,offset):
  collection=integer(p+offset)
  count=integer(collection+4) if collection else 0
  if count>100000:raise ValueError('Structure result count invalid')
  return count
 def sites(p,offset):
  collection=integer(p+offset)
  if not collection:return None
  count=structures(p,offset);arr=integer(collection+12)
  if count>1000:raise ValueError('Structure detail count exceeds budget')
  result=[]
  for j in range(count):
   node=integer(arr+4*j);dg=number(node+4)
   if not math.isfinite(dg):raise ValueError('Invalid native structure energy')
   strings={}
   for off in (0x10,0x14,0x18,0x1c):
    try:
     ptr=integer(node+off);n=integer(ptr-4)
     if 0<=n<=4096:strings[hex(off)]=rd(ptr,n).decode('ascii')
    except (OSError,ValueError,UnicodeDecodeError):pass
   result.append(dict(delta_g_kcal_mol=dg,native_3prime_flag=struct.unpack('<h',rd(node+0x28,2))[0],native_strings=strings,native_raw=rd(node,48).hex()))
  return result
 def primer(p):
  sp=integer(p+12);n=integer(sp-4)
  if not 1<=n<=70:raise ValueError('Primer length invalid')
  return dict(position=integer(p+8),sequence=rd(sp,n).decode('ascii'),length=n,tm=number(p+0x2c),gc=number(p+0x24),hairpin_count=structures(p,0x18),self_dimer_count=structures(p,0x1c),false_priming_count=structures(p,0x20) if integer(p+0x20) else None,raw=rd(p,100).hex(),hairpin_sites=sites(p,0x18),self_dimer_sites=sites(p,0x1c))
 pairs=[]
 for j in range(count):
  p=integer(arr+4*j)
  pairs.append(dict(rating=integer(p+0x10),cross_dimer_count=structures(p,0x14),cross_dimer_sites=sites(p,0x14),forward=primer(integer(p+4)),reverse=primer(integer(p+8)),native_pair_raw=rd(p,40).hex()))
 return dict(software_sha256=SHA,template_sha256=hashlib.sha256(seq.encode()).hexdigest(),count=count,pairs=pairs)

action=sys.argv[1];request=json.loads(pathlib.Path(sys.argv[2]).read_text())
if action=='prepare':out=prepare(request)
elif action=='close':
 post(main['hwnd'],0x10)
 deadline=time.monotonic()+5
 while u.IsWindow(main['hwnd']) and time.monotonic()<deadline:
  for dialog in windows():
   if dialog['pid']==PID and dialog['visible'] and dialog['cls']=='#32770':
    for button in windows(dialog['hwnd']):
     if button['cls']=='Button' and button['title'] in ('No','&No'):
      post(button['hwnd'],0xf5)
  time.sleep(.1)
 graceful=not u.IsWindow(main['hwnd'])
 termination=k.OpenProcess(1,False,PID)
 if not graceful and (not termination or not k.TerminateProcess(termination,0)):raise c.WinError(c.get_last_error())
 if termination:k.CloseHandle(termination)
 out={'closed_isolated_pid':PID,'graceful':graceful}
elif action=='diagnose':
 progress=wait(lambda:find('Search Progress'),60)
 p=obj(progress['hwnd']);status=integer(p+0x10c);vt=integer(status)
 out={'progress':hex(p),'status':hex(status),'vtable':hex(vt),'setter':hex(integer(vt+0x1d4)),'object':rd(status,256).hex()}
 for off in range(4,256,4):
  ptr=integer(status+off)
  if 0x10000<ptr<0x7fffffff:
   try:out['pointer_'+hex(off)]={'address':hex(ptr),'data':rd(ptr,96).hex()}
   except OSError:pass
elif action=='collect':out=extract(request['expected_sequence'])
elif action=='run':
 d=find('Search Criteria');progress=find('Search Progress')
 if d:
  actual,doc=settings(d)
  if actual!={key:request[key] for key in actual}:raise ValueError('Unexpected parameters at search start')
  LARGE_SEARCH_ALLOWED=True
  enter(d['hwnd'])
  def progress_ready():
   fail_modals();return find('Search Progress')
  progress=wait(progress_ready)
 elif progress:
  LARGE_SEARCH_ALLOWED=True
  actual,doc=settings(progress,0xf8)
  if actual!={key:request[key] for key in actual}:raise ValueError('Previous search had different parameters')
 else:raise ValueError('No prepared or resumable search')
 def completed():
  fail_modals()
  try:
   p=obj(progress['hwnd'],0x549258)
   # SearchProgress::DoCommand(299) stores the native search return value
   # at +0xf4. Accept/transfer is allowed only when this WORD is nonzero.
   complete=struct.unpack('<H',rd(p+0xf4,2))[0]
   collection=integer(p+0x108)
   if complete==1 and collection and integer(collection+4)>0:return ['Search Complete.']
   texts=status_text(progress)
   if texts in (['No primers found.'],['Unable to locate sufficient primers.']):return texts
  except (OSError,ValueError):pass
  return None
 completion=wait(completed,60)
 time.sleep(.2)
 if completion not in (['Search Complete.'],['No primers found.'],['Unable to locate sufficient primers.']):raise ValueError('Search did not complete successfully: '+str(completion))
 enter(progress['hwnd']);wait(lambda:not find('Search Progress'),8)
 if completion==['Search Complete.']:
  command(main['hwnd'],542);wait(lambda:find('Search Results'))
  def ready_extract():
   try:return extract(request['expected_sequence'])
   except (OSError,ValueError):return None
  out=wait(ready_extract)
 else:
  out={'software_sha256':SHA,'template_sha256':hashlib.sha256(request['expected_sequence'].encode()).hexdigest(),'count':0,'pairs':[]}
 out['settings']=actual;out['completion']=completion;out['native_search_warnings']=SEARCH_WARNINGS
else:raise ValueError('Expected prepare or run')
pathlib.Path(sys.argv[3]).write_text(json.dumps(out,indent=2));print(json.dumps({key:value for key,value in out.items() if key!='pairs'}));k.CloseHandle(h)
