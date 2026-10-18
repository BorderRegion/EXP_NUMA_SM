#!/usr/bin/env python3
"""Small reading/review package; no models, binaries or frame-level raw outputs."""
from pathlib import Path
import json,csv,hashlib,zipfile,shutil,re,ast
ROOT=Path(__file__).resolve().parents[1];NAME='T10_GPT_轻量包_20261015';STAGE=ROOT/'exports'/NAME
DESKTOP=Path('/home/ubuntu/桌面/GPU双卡拓扑实验_交付_20261014')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 archive=DESKTOP/(NAME+'.zip');textfile=DESKTOP/'T10_GPT_合并阅读材料_20261015.txt'
 if STAGE.exists()or archive.exists()or textfile.exists():raise SystemExit('Refuse to overwrite existing lightweight delivery')
 STAGE.mkdir(parents=True);sources={}
 files=['DECISIONS.jsonl','SOURCE_LOCKS.json','run_index.jsonl','preregistration/LOCAL_PROTOCOL.md','preregistration/renderer.patch','environment/device_query.json','environment/green_api_probe.json']
 files += [str(p.relative_to(ROOT))for p in (ROOT/'reports').iterdir()if p.suffix in ['.md','.json']]
 files += [str(p.relative_to(ROOT))for p in (ROOT/'reports/figures').glob('0[1-9]_*.png')]
 files += [str(p.relative_to(ROOT))for p in (ROOT/'derived/t10').iterdir()if p.suffix in ['.json','.csv']]
 files += [str(p.relative_to(ROOT))for p in (ROOT/'src').iterdir()if p.is_file()]
 files += ['tools/'+p for p in ['campaign_renderer.py','campaign_sparse.py','campaign_mechanism.py','formal_renderer.py','prepare_renderer.py','analyze_results.py','runlib.py']]
 files += [str(p.relative_to(ROOT))for p in (ROOT/'preregistration').glob('W*/*/plan_card.json')]
 files += ['GPU_COMPUTE_TOPOLOGY_DUAL_20261014/tools/reference.py','GPU_COMPUTE_TOPOLOGY_DUAL_20261014/docs/03_METHOD_AND_BASELINES.md','GPU_COMPUTE_TOPOLOGY_DUAL_20261014/docs/05_EXPERIMENTS_AND_STATS.md']
 for rel in sorted(set(files)):
  p=ROOT/rel;q=STAGE/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q);sources[rel]=sha(p)
 # Keep numerical text unchanged; replace the single deliberately omitted large image.
 report=STAGE/'reports/DUAL_TOPOLOGY_PAPER_REPORT_t10.md';s=report.read_text()
 s=s.replace('![真实渲染输出](figures/render_examples.png)','（轻量包省略大型渲染示例图片；完整包保留该图片及选取的二进制输出。）').replace('图中是每场景首个成功正式块的首帧','完整包的渲染示例是每场景首个成功正式块的首帧')
 report.write_text(s)
 prompt='''T10 实验轻量审阅包｜2026-10-15

用途：供网页版 GPT 阅读实验结果、审查方法与讨论后续验证。本次仅打包，没有新增 GPU 实验。

建议先读根目录“01_合并阅读材料.txt”，它整合了结果摘要、用户质疑、完整报告正文、全部48个正式进程块的N/R/M均值，以及关键访存/分组/计划代码。需要核查时再读 reports、derived/t10 和 src。九张结果图保留在 reports/figures。

可以把下面的请求交给 GPT：
请独立审阅本包。先区分“实测事实”“作者解释”“待验证假设”，检查当前负结果是否足以排除SM—地址亲和性，分析渲染负载、组级吞吐标定、静态分类和公开控制能力的适配问题。请同时检查时间漂移、Native顺序、样本量、同信息R基线及可复现性限制。不要预设NUMA存在，也不要因本次不提速而断言不存在。指出证据缺口，并给出优先级明确、可证伪、固定样本量的后续验证方案；不要建议事后挑选有利场景。

事实边界：实测只有一张T10；5070Ti未在本机运行。W1是完整动态3DGS，W2是真实输入独立CSR算子。每条件6个进程块；73,728帧/请求不是独立样本数。E3为新进程配对批次；有限E4没有计时尾Native锚。当前没有SM×地址亲和性图。

本包包含：报告与质疑、原始决策记录、组级容量/会话均值/逐块主比较/统计区间/成本/健康快照、关键源码、计划参数、九张图。
本包省略：逐帧原始CSV、全部run目录、完整任务表/开发权重、模型/CSR大文件、渲染示例图片、像素二进制输出、编译产物及第三方依赖。因此它是审阅包，不是完整GPU复现实验包；正文保留的部分完整包路径在这里不会存在。

tools/recompute_paired_light.py 可从已保存的逐块均值复算四个主对比的20000次bootstrap并核对区间，不会执行GPU工作。它不从逐帧CSV重建均值。原 tools/analyze_results.py 仅作为分析源码供审阅，在本轻量包内不能直接运行完整main。

完整证据包名：T10_实验结果与质疑_20261015.zip；原冻结实测包名：GPU_TOPOLOGY_T10_20261014.zip。两者仍保留在桌面交付目录。LIGHT_MANIFEST.json列出本小包文件校验值。
'''
 (STAGE/'00_给GPT的阅读说明.txt').write_text(prompt)
 (STAGE/'REPRODUCE.md').write_text('''# 轻量包复算范围\n\n运行 `python3 tools/recompute_paired_light.py`，可用逐块均值重算W1/W2的M/N和M/R主比较。无需GPU或第三方Python包。\n\n本包没有逐帧原始CSV、完整run目录或模型，不能运行完整分析main、完整输出审计或重跑GPU。完整复现请使用桌面保留的大包。本文件为轻量版说明，不是原完整包REPRODUCE.md。\n''')
 source=(ROOT/'tools/analyze_results.py').read_text();tree=ast.parse(source);fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name=='bootstrap');function=ast.get_source_segment(source,fn)
 wrapper='''import pathlib,json,collections,math,random\nROOT=pathlib.Path(__file__).resolve().parents[1]\n'''+function+'''\nexpected=json.loads((ROOT/'derived/t10/application_statistics.json').read_text())\nresults={}\nfor ref in ['N','R']:\n records=json.loads((ROOT/('derived/t10/paired_M_'+ref+'.json')).read_text())\n for workload in ['W1','W2']:\n  key=workload+'_M/'+ref\n  results[key]=bootstrap([r for r in records if r['condition'].startswith(workload+'/')])\n  assert results[key]==expected[key],key\nprint('PASS: four primary comparisons exactly match; based on saved block means, not raw frame reprocessing')\nprint(json.dumps(results,indent=2))\n'''
 (STAGE/'tools/recompute_paired_light.py').write_text(wrapper)
 rows=list(csv.DictReader(open(ROOT/'derived/t10/session_summaries.csv')));blocks={}
 for r in rows:blocks.setdefault((r['workload'],r['input'],int(r['sequence']),int(r['block_id'])),{})[r['policy']]=r['mean_ms']
 blocktable='workload,input,sequence,block,N_mean_ms,R_mean_ms,M_mean_ms\n'+'\n'.join(','.join(map(str,[*k,v['N'],v['R'],v['M']]))for k,v in sorted(blocks.items()))
 merged=[prompt,'\n\n===== 1. 结果与证据边界摘要 =====\n', (ROOT/'reports/结果与证据边界摘要_20261015.md').read_text(),'\n\n===== 2. 用户质疑与未执行的验证方案 =====\n',(ROOT/'reports/实验质疑与后续验证_20261015.md').read_text(),'\n\n===== 3. 原实验完整报告正文（图片见压缩包） =====\n',re.sub(r'!\[[^\]]*\]\([^)]+\)','[图像见压缩包对应文件]',s),'\n\n===== 4. 全部48个正式进程块均值 =====\n',blocktable]
 for rel in ['src/micro_kernels.cu','src/driver_backend.hpp','tools/campaign_renderer.py']:
  merged += ['\n\n===== 5. 关键代码：'+rel+' =====\n',(ROOT/rel).read_text()]
 (STAGE/'01_合并阅读材料.txt').write_text(''.join(merged));shutil.copy2(STAGE/'01_合并阅读材料.txt',textfile)
 entries=[dict(path=str(p.relative_to(STAGE)),bytes=p.stat().st_size,sha256=sha(p),source_sha256=sources.get(str(p.relative_to(STAGE))))for p in sorted(STAGE.rglob('*'))if p.is_file()]
 info=dict(purpose='Lightweight research review; not full raw-data/GPU reproduction',date='2026-10-15',new_GPU_experiments=False,full_package_sha256=json.loads((ROOT/'environment/results_questions_package_validation.json').read_text())['sha256'],files=entries)
 (STAGE/'LIGHT_MANIFEST.json').write_text(json.dumps(info,indent=2,ensure_ascii=False))
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9)as z:
  for p in sorted(STAGE.rglob('*')):
   if p.is_file():z.write(p,NAME+'/'+str(p.relative_to(STAGE)))
 with zipfile.ZipFile(archive)as z:
  assert z.testzip()is None
  for x in entries:assert hashlib.sha256(z.read(NAME+'/'+x['path'])).hexdigest()==x['sha256']
 result=dict(status='PASS',zip=str(archive),zip_bytes=archive.stat().st_size,merged_text=str(textfile),text_bytes=textfile.stat().st_size,files=len(entries)+1,sha256=sha(archive),CRC_and_file_hashes_verified=True)
 archive.with_suffix('.sha256').write_text(result['sha256']+'  '+archive.name+'\n');(ROOT/'environment/gpt_light_package_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
