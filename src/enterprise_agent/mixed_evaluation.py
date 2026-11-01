"""Real, frozen mixed-question evaluation. No scripted model decisions."""
import argparse, hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path
from .evaluation import write_json, audit_record
from .graph import Agent
from .model import load_env, HTTPDecisionModel
from .retrieval import DocumentStore
ROOT=Path(__file__).resolve().parents[2]

def inspect_case(case, records):
    result=records[-1]['result'];expected=case['expected']
    gaps='\n'.join(result['missing_info'])+'\n'+result['question']
    return {'non_complete_status':result['status'] in expected['allowed_statuses'],
            'known_evidence_retained':set(expected['required_doc_ids']).issubset({c['doc_id'] for c in result['citations']}),
            'specific_unknowns_identified':all(any(w.lower() in gaps.lower() for w in g) for g in expected['gap_keyword_groups']),
            'real_response_every_turn':all(r['model_response_count']>0 for r in records),
            'trace_audit':all(not audit_record(r) for r in records)}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--env-file',type=Path,default=ROOT/'.env')
    p.add_argument('--credentials-file',type=Path)
    p.add_argument('--dataset',type=Path,default=ROOT/'data/mixed-evaluation-v1.json')
    p.add_argument('--data',type=Path,default=ROOT/'data/documents.json')
    p.add_argument('--output-dir',type=Path,default=ROOT/'examples/mixed20-runs')
    args=p.parse_args();load_env(args.env_file)
    if args.credentials_file:load_env(args.credentials_file)
    if not os.getenv('LLM_API_KEY') and os.getenv('ARK_API_KEY'):os.environ['LLM_API_KEY']=os.environ['ARK_API_KEY']
    if not os.getenv('LLM_BASE_URL'):os.environ['LLM_BASE_URL']=os.getenv('ARK_BASE_URL','https://ark.cn-beijing.volces.com/api/v3')
    HTTPDecisionModel.from_env()
    data=json.loads(args.dataset.read_text());store=DocumentStore.from_path(args.data)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');folder=args.output_dir/stamp
    folder.mkdir(parents=True,exist_ok=False);write_json(folder/'frozen-testset.json',data)
    report={'dataset_sha256':hashlib.sha256(args.dataset.read_bytes()).hexdigest(),'state':'running','planned_cases':len(data['cases']),'completed_cases':0,'rule_checks_passed':0,'cases':[],'models':[],'reported_tokens':0}
    log=ROOT/'examples/retest-report.md'
    def append(text):
        with log.open('a') as f:f.write(text)
    append(f'\n## 新20组混合测试 · {stamp}（UTC）\n\n先冻结预期再测试。16组单轮+4组双轮，共24条用户输入。双轮助手历史由本轮真实生成。数据集SHA256：{report["dataset_sha256"]}。规则初筛并非完整语义正确性证明，失败不重跑覆盖。\n')
    for case in data['cases']:
        records=[];history=[]
        for turn,q in enumerate(case['turns'],1):
            r=Agent(HTTPDecisionModel.from_env(),store).run(q,history)
            r.update(evaluation_case_id=case['id'],evaluation_turn=turn)
            write_json(folder/f"{case['id']}-turn-{turn}.json",r);records.append(r)
            history.extend([{'role':'user','content':q},{'role':'assistant','content':r['result']['answer']}])
            for t in r['trace']:
                m=t.get('model_metadata',{})
                if m.get('model') and m['model'] not in report['models']:report['models'].append(m['model'])
                report['reported_tokens']+=m.get('usage',{}).get('total_tokens',0)
        checks=inspect_case(case,records)
        row={'id':case['id'],'name':case['name'],'checks':checks,'rule_passed':all(checks.values()),'status':records[-1]['result']['status'],'expected':case['expected'],'turn_count':len(records),'steps':sum(len(r['trace']) for r in records)}
        report['cases'].append(row);report['completed_cases']+=1;report['rule_checks_passed']+=row['rule_passed']
        write_json(folder/'summary.json',report)
        append(f"\n### {case['id']} {case['name']}\n\n输入："+' / '.join(case['turns'])+'\n\n预期：'+case['expected']['review_note']+'\n\n规则检查：'+json.dumps(checks,ensure_ascii=False)+'\n\n')
        for n,r in enumerate(records,1):
            target=os.path.relpath(folder/f"{case['id']}-turn-{n}.json",log.parent)
            append(f'[第{n}轮Trace]({target})\n\n```text\n'+r['result']['answer']+'\n```\n\n')
        print(json.dumps({k:row[k] for k in ['id','rule_passed','status','checks']},ensure_ascii=False),flush=True)
    report['state']='complete';write_json(folder/'summary.json',report)
    append(f"\n完成{report['completed_cases']}/{report['planned_cases']}；规则初筛通过{report['rule_checks_passed']}/{report['planned_cases']}；模型{report['models']}；API报告token合计{report['reported_tokens']}，不等于已核实扣费。[本轮汇总]({os.path.relpath(folder/'summary.json',log.parent)})。\n")
    print(str(folder),flush=True)
    return int(report['rule_checks_passed']!=report['planned_cases'])
if __name__=='__main__':raise SystemExit(main())
