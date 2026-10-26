"""NCBI ORFfinder and supplied-primer specificity requests; retain raw evidence."""
import html.parser, urllib.request, urllib.parse, pathlib, json, re, hashlib

class FormDefaults(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(); self.fields={}; self.select=None
    def handle_starttag(self,tag,attrs):
        a=dict(attrs);name=a.get('name')
        if tag=='input' and name:
            typ=a.get('type','text')
            if typ in ('file','button','submit','reset'):return
            if typ in ('checkbox','radio'):
                if 'checked' in a:self.fields[name]=a.get('value','on')
            else:self.fields[name]=a.get('value') or a.get('defval','')
        elif tag=='select' and name:
            self.select=name
            if 'defval' in a:self.fields[name]=a['defval']
        elif tag=='option' and self.select:
            if self.select not in self.fields or 'selected' in a:self.fields[self.select]=a.get('value','')
        elif tag=='textarea' and name:self.fields[name]=''
    def handle_endtag(self,tag):
        if tag=='select':self.select=None

def orffinder(sequence, directory, genetic_code=1):
    directory=pathlib.Path(directory);directory.mkdir(parents=True,exist_ok=True)
    parameters=dict(acc=sequence,minlen=25,gcode=genetic_code,startcdn=1,nested=1)
    (directory/'orffinder-request.json').write_text(json.dumps(parameters,indent=2))
    url='https://www.ncbi.nlm.nih.gov/projects/orffinder/ORFfinderBE.cgi'
    raw=urllib.request.urlopen(url,data=urllib.parse.urlencode(parameters).encode(),timeout=90).read()
    (directory/'orffinder-native.json').write_bytes(raw)
    result=json.loads(raw)
    if result.get('status')!='success' or 'error' in result.get('retval',{}):raise ValueError(result)
    rows=[]
    for item in result['retval']['orflist']:
        if 'b' not in item:continue
        start,end=int(item['b']),int(item['e'])
        if not 1<=start<=end<=len(sequence):raise ValueError('Invalid ORFfinder coordinates')
        rows.append(dict(id=item['n'],start=start,end=end,strand=item['s'],frame=int(item['f']),length=end-start+1,protein=item['aa'],boundary_start=item.get('pb',''),boundary_end=item.get('pe','')))
    return sorted(rows,key=lambda x:-x['length'])

def submit_specificity(forward,reverse,directory,organism,template):
    """Supplied PP5 primers remain unchanged. NCBI only checks this pair."""
    directory=pathlib.Path(directory);directory.mkdir(parents=True,exist_ok=True)
    page=urllib.request.urlopen('https://www.ncbi.nlm.nih.gov/tools/primer-blast/index.cgi',timeout=40).read().decode('utf-8-sig')
    parser=FormDefaults();parser.feed(page);p=parser.fields
    p.update(INPUT_SEQUENCE=template,PRIMER_LEFT_INPUT=forward,PRIMER_RIGHT_INPUT=reverse,PRIMER_PRODUCT_MIN='200',PRIMER_PRODUCT_MAX='750',PRIMER_NUM_RETURN='1',PRIMER_MIN_TM='56',PRIMER_OPT_TM='60',PRIMER_MAX_TM='65',PRIMER_MAX_DIFF_TM='2',PRIMER_MIN_SIZE='18',PRIMER_OPT_SIZE='20',PRIMER_MAX_SIZE='25',PRIMER_MIN_GC='40',PRIMER_MAX_GC='60',SEARCH_SPECIFIC_PRIMER='on',PRIMER_SPECIFICITY_DATABASE='refseq_mrna',ORGANISM=organism,ORGANISM_INCLUDES=organism,ORGANISM_EXCLUDES='',SEARCHMODE='0',CMD='request')
    (directory/'request.json').write_text(json.dumps(p,indent=2))
    response=urllib.request.urlopen('https://www.ncbi.nlm.nih.gov/tools/primer-blast/primertool.cgi',data=urllib.parse.urlencode(p).encode(),timeout=90)
    body=response.read().decode('utf-8-sig');(directory/'submitted.html').write_text(body)
    return dict(url=response.url,html=body)

def job_url(body):
    match=re.search(r'URL=([^"\s>]+)',body,re.I)
    if not match:raise ValueError('No complete Primer-BLAST status URL returned; inspect submitted.html')
    url=html.unescape(match.group(1))
    parsed=urllib.parse.urlparse(url)
    fields=urllib.parse.parse_qs(parsed.query)
    if parsed.hostname!='www.ncbi.nlm.nih.gov' or not fields.get('job_key') or not fields.get('ctg_time'):
        raise ValueError('Incomplete/unexpected status URL')
    return url

def check_specificity(directory,expected_forward,expected_reverse,expected_product):
    directory=pathlib.Path(directory);job=json.loads((directory/'job.json').read_text())
    if (job['submitted_forward'],job['submitted_reverse'])!=(expected_forward,expected_reverse):
        raise ValueError('Cached job belongs to different primers')
    raw=urllib.request.urlopen(job['url'],timeout=60).read()
    (directory/'result.html').write_bytes(raw)
    body=raw.decode('utf-8-sig');parser=FormDefaults();parser.feed(body)
    info=parser.fields.get('PRIMER_RESULTS_INFO','')
    if not info:
        return dict(status='pending' if re.search('HTTP-EQUIV=Refresh',body,re.I) else 'needs_review',url=job['url'])
    def table_row(name):
        match=re.search(r'<tr><th>'+name+r' primer</th>(.*?)</tr>',body,re.S)
        if not match:raise ValueError('No actual supplied-primer result row')
        return [html.unescape(re.sub('<[^>]+>','',x)).strip() for x in re.findall(r'<td[^>]*>(.*?)</td>',match.group(1),re.S)]
    forward,reverse=table_row('Forward'),table_row('Reverse')
    if forward[0]!=expected_forward or reverse[0]!=expected_reverse:raise ValueError('NCBI returned different primers')
    products=[int(x) for x in re.findall(r'product length = (\d+)',body)]
    if expected_product not in products:raise ValueError('Expected local product not confirmed by NCBI')
    status='pass' if info.startswith('Primer pairs are specific to input template as no other targets were found') else 'not_passed'
    return dict(status=status,conclusion=info,url=job['url'],template=parser.fields.get('TEMPLATE_ID'),database='refseq_mrna',forward_tm_ncbi=float(forward[5]),reverse_tm_ncbi=float(reverse[5]),delta_tm_ncbi=abs(float(forward[5])-float(reverse[5])),products=products,report_sha256=hashlib.sha256(raw).hexdigest())
