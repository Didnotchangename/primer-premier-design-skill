"""ORFfinder -> local PP5 -> ORF coverage -> supplied-primer Primer-BLAST.

External sequence submission must be within the user's authorized scope.
First record only; species is explicit. JSON native evidence supports resume.
"""
import argparse,hashlib,json,pathlib,subprocess,sys,time
from pp5_design import records,validate_select
from ncbi_services import orffinder,submit_specificity,job_url,check_specificity

def map_candidate(row,orf,window_start,window_end):
    row=dict(row)
    if orf['strand']=='+':
        start=window_start+row['product_start']-1;end=window_start+row['product_end']-1
    else:
        start=window_end-row['product_end']+1;end=window_end-row['product_start']+1
    overlap=max(0,min(end,orf['end'])-max(start,orf['start'])+1)
    row.update(product_start=start,product_end=end,orf_id=orf['id'],orf_start=orf['start'],orf_end=orf['end'],orf_strand=orf['strand'],orf_length=orf['length'],orf_overlap=overlap,orf_coverage=overlap/orf['length'],orf_source='NCBI ORFfinder',orf_status='预测；按最长ORF初选，需结合注释',orf_boundary_start=orf['boundary_start'],orf_boundary_end=orf['boundary_end'])
    return row

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('fasta','organism','archive','workdir','output'):p.add_argument('--'+name,required=True)
    p.add_argument('--reference',help='Verified intended transcript accession; never guess')
    p.add_argument('--genetic-code',type=int,default=1)
    p.add_argument('--orf-id',help='Use an ORF selected from returned predictions instead of default longest')
    p.add_argument('--wait-seconds',type=int,default=600)
    args=p.parse_args();name,seq=records(args.fasta)[0]
    output=pathlib.Path(args.output).resolve();output.mkdir(parents=True,exist_ok=True)
    source_sha=hashlib.sha256(seq.encode()).hexdigest();state_file=output/'progress.json'
    if state_file.exists():
        previous=json.loads(state_file.read_text())
        if previous['input_sha256']!=source_sha or previous['organism']!=args.organism or previous.get('reference')!=args.reference:raise ValueError('Output belongs to another input/species/reference')
    state=dict(id=name,input_sha256=source_sha,organism=args.organism,reference=args.reference,status='orf_analysis',selected=[])
    def save():state_file.write_text(json.dumps(state,ensure_ascii=False,indent=2))
    save()
    cache=output/'orfs.json'
    if cache.exists():
        request=json.loads((output/'orffinder-request.json').read_text())
        cached_sequence=request['acc']
        if cached_sequence.startswith('>'):cached_sequence=''.join(cached_sequence.splitlines()[1:])
        if cached_sequence!=seq or int(request['gcode'])!=args.genetic_code:raise ValueError('ORF cache belongs to another sequence/genetic code')
        orfs=json.loads(cache.read_text())
    else:
        orfs=orffinder(seq,output,args.genetic_code);cache.write_text(json.dumps(orfs,ensure_ascii=False,indent=2))
    if not orfs:state.update(status='no_orf');save();return
    orf=next((o for o in orfs if o['id']==args.orf_id),None) if args.orf_id else orfs[0]
    if orf is None:raise ValueError('Requested ORF ID not found')
    state['orf']=orf
    # False Priming must cover the complete supplied template, including UTRs.
    lo=1;hi=len(seq)
    template=seq[lo-1:hi]
    if orf['strand']=='-':template=template.translate(str.maketrans('ACGT','TGCA'))[::-1]
    state.update(window_start=lo,window_end=hi,status='pp5_design');save()
    fasta=output/'design-window.fasta';fasta.write_text('>'+name+'\n'+template+'\n')
    native=output/'native';record=native/'record-001'
    if not (record/'validated.json').exists():
        subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name('pp5_design.py')),'--fasta',str(fasta),'--archive',args.archive,'--workdir',args.workdir,'--output',str(native)],check=True)
    runs=[json.loads(f.read_text()) for f in sorted(record.glob('native-*.json'))]
    if not runs:raise ValueError('No native evidence')
    # Always revalidate native sequence/coordinates, including on resume.
    validated=validate_select(runs,template,name)
    candidates=[map_candidate(r,orf,lo,hi) for r in validated['candidates']]
    candidates=[r for r in candidates if r['orf_overlap']>0]
    eligible=sorted((r for r in candidates if r['native_quality_clear']),key=lambda r:(-r['orf_overlap'],-r['rating'],r['delta_tm']))
    selected=[dict(r,rank=i+1,level='首选' if i==0 else '备选') for i,r in enumerate(eligible[:3])]
    state.update(status='specificity_check',native_count=validated['raw_count'],candidates=candidates,selected=selected)
    save()
    if not selected:state.update(status='no_qualifying_pair');save();return
    for i,row in enumerate(selected,1):
        directory=output/('specificity-%d'%i);directory.mkdir(exist_ok=True)
        if not (directory/'job.json').exists():
            reply=submit_specificity(row['forward'],row['reverse'],directory,args.organism,args.reference or seq)
            job=dict(url=job_url(reply['html']),submitted_forward=row['forward'],submitted_reverse=row['reverse'])
            (directory/'job.json').write_text(json.dumps(job,indent=2))
        request=json.loads((directory/'request.json').read_text())
        if request['ORGANISM']!=args.organism or request['INPUT_SEQUENCE']!=(args.reference or seq):raise ValueError('Cached specificity job uses another species/template')
        end=time.monotonic()+args.wait_seconds
        while True:
            result=check_specificity(directory,row['forward'],row['reverse'],row['product_length'])
            row['specificity_result']=result;row['specificity']=result['status'];save()
            print(json.dumps(dict(pair=i,status=result['status'],url=result['url'])),flush=True)
            if result['status']!='pending' or time.monotonic()>=end:break
            time.sleep(30)
    passed=all(r.get('specificity')=='pass' for r in selected)
    state['status']='computational_checks_complete' if passed else 'incomplete_or_failed_specificity'
    save()
    if not passed:sys.exit(2)

if __name__=='__main__':main()
