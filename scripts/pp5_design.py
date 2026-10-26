"""Local macOS PP5 runner. Uses only a marked, isolated CrossOver bottle.

FASTA records are processed sequentially, with a fresh PP5 process per record.
Native results are retained before independent validation and selection.
"""
import argparse, csv, hashlib, json, pathlib, re, subprocess, threading, tarfile, shutil, fcntl

ROOT = pathlib.Path(__file__).resolve().parent.parent
CROSSOVER = pathlib.Path('/Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin')
SHA = '024eea91d0e65f068784f93760fa27eb7d4ab69f642404c26049ad0d3112e4c8'

def winpath(path):
    return 'Z:' + str(pathlib.Path(path).resolve()).replace('/', '\\')

def records(path):
    result = []
    for chunk in pathlib.Path(path).read_text().split('>'):
        if not chunk.strip(): continue
        lines = chunk.splitlines()
        name = lines[0].strip()
        sequence = re.sub(r'\s+', '', ''.join(lines[1:])).upper()
        if not name or not re.fullmatch('[ACGT]+', sequence):
            raise ValueError('FASTA requires nonempty ID and unambiguous A/C/G/T DNA')
        result.append((name, sequence))
    if not result or len({x[0] for x in result}) != len(result):
        raise ValueError('FASTA must contain uniquely named records')
    return result

def validate_select(native, sequence, record_id, limit=3, length_min=18, length_max=25):
    """Validate every native row; reject inconsistent data, filter hard ranges.

    Native structures are warnings, not estimated free energies. Rank fewer
    native structure findings first, then native pair rating and delta Tm.
    ORF coverage is intentionally absent unless externally annotated.
    """
    digest = hashlib.sha256(sequence.encode()).hexdigest()
    candidates = {}
    raw_count = 0
    for run in native:
        if run['software_sha256'] != SHA or run['template_sha256'] != digest:
            raise ValueError('Software/template provenance mismatch')
        if run['count'] != len(run['pairs']): raise ValueError('Row count mismatch')
        settings = run['settings']
        for pair in run['pairs']:
            raw_count += 1
            f, r = pair['forward'], pair['reverse']
            for primer, reverse in ((f, False), (r, True)):
                s, pos, n = primer['sequence'], primer['position'], primer['length']
                if n != len(s) or not 0 <= pos <= len(sequence)-n:
                    raise ValueError('Invalid native position/length')
                target = sequence[pos:pos+n]
                if reverse: target = target.translate(str.maketrans('ACGT','TGCA'))[::-1]
                if s != target: raise ValueError('Primer orientation/sequence mismatch')
                gc = 100 * (s.count('G')+s.count('C'))/n
                if abs(gc-primer['gc']) > .0001: raise ValueError('Native GC mismatch')
                if not (settings['nominal_length']-settings['length_tolerance'] <= n <= settings['nominal_length']+settings['length_tolerance'] and settings['gc_min'] <= gc <= settings['gc_max'] and settings['tm_min'] <= primer['tm'] <= settings['tm_max']):
                    raise ValueError('PP5 returned a row outside verified search settings')
            start, end = f['position']+1, r['position']+r['length']
            product, delta = end-start+1, abs(f['tm']-r['tm'])
            if not settings['product_min'] <= product <= settings['product_max']:
                raise ValueError('Native product outside requested search range')
            if not (length_min <= f['length'] <= length_max and length_min <= r['length'] <= length_max and delta <= 2): continue
            structures = pair['cross_dimer_count'] + sum(p[k] for p in (f,r) for k in ('hairpin_count','self_dimer_count'))
            row = dict(id=record_id,template_type='cDNA',template_length=len(sequence),orf_status='未提供注释',forward=f['sequence'],reverse=r['sequence'],f_length=f['length'],r_length=r['length'],f_gc=f['gc'],r_gc=r['gc'],f_tm=f['tm'],r_tm=r['tm'],delta_tm=delta,product_start=start,product_end=end,product_length=product,template_coverage=product/len(sequence),rating=pair['rating'],f_hairpin=f['hairpin_count'],r_hairpin=r['hairpin_count'],f_self_dimer=f['self_dimer_count'],r_self_dimer=r['self_dimer_count'],cross_dimer=pair['cross_dimer_count'],structure_findings=structures,local_check='通过',specificity='未检查',false_priming='未验证，不能以集合为0宣称通过',structure_status='无原生结构提示' if structures==0 else '存在原生结构提示，需审查')
            fp_f=f.get('false_priming_count',f.get('false_priming_count_unverified'));fp_r=r.get('false_priming_count',r.get('false_priming_count_unverified'))
            fp_initialized=all(int.from_bytes(bytes.fromhex(primer.get('raw',''))[0x20:0x24],'little')!=0 for primer in (f,r))
            fp_known=fp_initialized and all(isinstance(x,int) and not isinstance(x,bool) and x>=0 for x in (fp_f,fp_r))
            row.update(f_false_priming_count=fp_f,r_false_priming_count=fp_r,false_priming_scope_length=len(sequence),native_quality_clear=structures==0 and fp_known and fp_f==0 and fp_r==0,false_priming='原生集合计数0；仅对本轮输入模板有效' if fp_known and fp_f==0 and fp_r==0 else '原生False Priming Found' if fp_known else '未知，禁止自动推荐')
            candidates[(row['forward'],row['reverse'])] = row
    ordered = sorted(candidates.values(), key=lambda x:(x['structure_findings'], -x['rating'], x['delta_tm'], abs((x['f_tm']+x['r_tm'])/2-60)))
    # Do not promote structurally flagged rows just to fill three slots.
    selected = [dict(row, rank=i+1,level='首选' if i==0 else '备选') for i,row in enumerate([r for r in ordered if r['native_quality_clear']][:limit])]
    return dict(id=record_id,template_sha256=digest,raw_count=raw_count,eligible_count=len(ordered),structure_clear_count=sum(x['structure_findings']==0 for x in ordered),native_quality_clear_count=sum(x['native_quality_clear'] for x in ordered),selected=selected,candidates=ordered,status='完成本地设计；特异性未检查' if selected else '未找到同时无结构及False Priming提示的候选，不自动放宽')

def helper(bottle, action, request, output):
    cmd = [str(CROSSOVER/'wine'),'--bottle',str(bottle),'--cx-app',winpath(ROOT/'runtime/python-win32/python.exe'),winpath(ROOT/'scripts/pp5_driver.py'),action,winpath(request),winpath(output)]
    # CrossOver shares Windows console pipe handles with the GUI process.
    # communicate()/capture_output can wait forever for GUI-held EOF.
    subprocess.run(cmd,check=True,timeout=95,stdin=subprocess.DEVNULL)
    return json.loads(output.read_text())

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fasta',required=True);p.add_argument('--archive',required=True)
    p.add_argument('--workdir',required=True);p.add_argument('--output',required=True)
    p.add_argument('--rounds',default='20:2,24:1,22:4',help='Native nominal:tolerance rounds')
    p.add_argument('--length-max',type=int,default=25,help='Final length preference limit; document departures from18–25')
    p.add_argument('--all',action='store_true',help='Process all records only after the sample/report format has been approved')
    args=p.parse_args()
    seqs=records(args.fasta)
    if not args.all: seqs=seqs[:1]
    work=pathlib.Path(args.workdir).resolve();work.mkdir(parents=True,exist_ok=True)
    output=pathlib.Path(args.output).resolve();output.mkdir(parents=True,exist_ok=True)
    lock=(work/'runner.lock').open('w')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    bottle=work/'pp5-bottle';app=bottle/'drive_c/.Primer Premier 5';marker=app/'codex-isolated-test.marker'
    if not bottle.exists():
        subprocess.run([str(CROSSOVER/'cxbottle'),'--bottle',str(bottle),'--restore',str(pathlib.Path(args.archive).resolve())],check=True,capture_output=True,timeout=180)
        if hashlib.sha256((app/'Primer Premier 5.exe').read_bytes()).hexdigest()!=SHA: raise ValueError('Unsupported PP5 archive')
        marker.write_text('Codex-owned isolated primer design bottle; original bottle is not used.\n')
    if not marker.is_file():raise ValueError('Refusing an unmarked existing bottle')
    pristine=work/'pref-pristine.tbl'
    if not pristine.exists():
        with tarfile.open(args.archive,'r:gz') as archive:
            member=next(m for m in archive if m.name.replace('\\','/').endswith('/data/pref.tbl'))
            pristine.write_bytes(archive.extractfile(member).read())
    reports=[]
    for index,(name,seq) in enumerate(seqs,1):
        directory=output/('record-%03d'%index);directory.mkdir(exist_ok=True)
        # PP5 persists a PID in pref.tbl. Wine can reuse that PID after a server
        # restart, falsely reporting a second instance. Restore original preferences
        # in this runner-owned bottle before starting each sequential record.
        inventory_request=directory/'inventory-request.json';inventory_request.write_text('{}')
        inventory=helper(bottle,'inventory',inventory_request,directory/'inventory.json')
        if inventory['mains']:raise RuntimeError('A PP5 instance is already running in this isolated bottle; close it before resuming')
        shutil.copyfile(pristine,app/'data/pref.tbl')
        log=(work/('app-%03d.log'%index)).open('wb')
        process=subprocess.Popen([str(CROSSOVER/'wine'),'--bottle',str(bottle),'--workdir',r'C:\.Primer Premier 5','--cx-app',r'C:\.Primer Premier 5\Primer Premier 5.exe'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        def drain(pipe, sink):
            try:
                for line in iter(pipe.readline,b''):sink.write(line);sink.flush()
            finally:sink.close()
        threading.Thread(target=drain,args=(process.stdout,log),daemon=True).start()
        request=directory/'request.json';runs=[]
        try:
            # Superset round includes short/long mixed pairs; final filter enforces18–25.
            for nominal,tolerance in [tuple(map(int,x.split(':'))) for x in args.rounds.split(',')]:
                request.write_text(json.dumps(dict(expected_sequence=seq,mode=1,nominal_length=nominal,length_tolerance=tolerance,tm_min=56,tm_max=65,gc_min=40,gc_max=60,product_min=200,product_max=min(750,len(seq)))))
                stem='%d-%d'%(nominal-tolerance,nominal+tolerance)
                helper(bottle,'prepare',request,directory/('readback-'+stem+'.json'))
                runs.append(helper(bottle,'run',request,directory/('native-'+stem+'.json')))
            report=validate_select(runs,seq,name,length_max=args.length_max);reports.append(report)
            (directory/'validated.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
            print(json.dumps({k:v for k,v in report.items() if k not in ('selected','candidates')},ensure_ascii=False),flush=True)
        except BaseException as error:
            (directory/'failure.json').write_text(json.dumps(dict(id=name,error_type=type(error).__name__,message=str(error),completed_native_rounds=len(runs)),ensure_ascii=False,indent=2))
            raise
        finally:
            # This is our isolated process. No user bottle is enumerated or closed.
            helper(bottle,'close',request,directory/'closed.json')
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.terminate()
        (output/'progress.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2))
    selected=[r for report in reports for r in report['selected']]
    if selected:
        with (output/'selected.csv').open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(selected[0]));writer.writeheader();writer.writerows(selected)

if __name__=='__main__':main()
