#!/usr/bin/env python3
"""Build the real P4 core and compile its frontend; run only model-free CPU tests."""
import argparse,hashlib,json,pathlib,shutil,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--cmake',default='cmake');p.add_argument('--ninja',default='ninja');p.add_argument('--cxx',default='g++');p.add_argument('--jobs',type=int,default=2);a=p.parse_args()
 if not 1<=a.jobs<=4:raise ValueError('Use 1–4 CPU build jobs')
 out=a.out.resolve()
 if out.exists() or out==ROOT or ROOT in out.parents:raise ValueError('Choose a fresh output directory outside this source package')
 provenance=json.loads((ROOT/'PROVENANCE.json').read_text())
 for row in provenance['files']:
  if hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Changed source: '+row['path'])
 out.mkdir(parents=True);calls=[]
 def run(name,args):
  with (out/(name+'.log')).open('w') as f:r=subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT)
  calls.append({'name':name,'argv':list(map(str,args)),'returncode':r.returncode});(out/'COMMANDS.json').write_text(json.dumps(calls,indent=2));r.check_returncode()
 backend=ROOT/'backend';build=out/'core'
 options=['-DBUILD_SHARED_LIBS=OFF','-DGGML_CPU=ON','-DGGML_CUDA=OFF','-DGGML_NATIVE=OFF','-DGGML_CCACHE=OFF','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_EXPORT_COMPILE_COMMANDS=ON']
 options+=['-D'+key+'=OFF' for key in ['LLAMA_BUILD_COMMON','LLAMA_BUILD_TESTS','LLAMA_BUILD_EXAMPLES','LLAMA_BUILD_TOOLS','LLAMA_BUILD_SERVER','LLAMA_BUILD_APP','LLAMA_BUILD_MTMD','LLAMA_OPENSSL','LLAMA_BUILD_UI','LLAMA_USE_PREBUILT_UI']]
 run('configure',[a.cmake,'-S',backend,'-B',build,'-G','Ninja','-DCMAKE_MAKE_PROGRAM='+str(pathlib.Path(shutil.which(a.ninja) or a.ninja).resolve()),'-DLLAMA_BUILD_NUMBER=10839','-DLLAMA_BUILD_COMMIT=0cae43063',*options])
 run('core-build',[a.cmake,'--build',build,'--target','llama','ggml-cpu','--parallel',a.jobs])
 inc=[backend/d for d in ['include','src','ggml/include','ggml/src','common','vendor']]+[ROOT/'frontend']
 run('frontend-object',[a.cxx,'-std=c++17','-O0',*['-I'+str(x) for x in inc],'-c',ROOT/'frontend/native.cpp','-o',out/'native.o'])
 for test in ['transaction','draft_work']:
  run(test+'-build',[a.cxx,'-std=c++17','-O2','-I'+str(ROOT/'frontend'),ROOT/('frontend/test_'+test+'.cpp'),'-o',out/('test-'+test)])
  run(test+'-run',[out/('test-'+test)])
 (out/'RESULT.json').write_text(json.dumps({'core_CPU_build':'PASS','real_P4_frontend_object':'PASS','CPU_tests':'PASS','GPU_requests':0,'model_loads':0,'CUDA_build':'NOT_RUN','full_worker_link':'NOT_RUN','numerical_qualification':'NOT_RUN'},indent=2))
 print('PASS: real CPU core, P4 frontend compilation, model-free tests. CUDA worker not built.')
if __name__=='__main__':main()
