"""Materialize a capture-only worker from the exact accepted source."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil


BASELINE = "3f8084142cb78c8f6cb2c9580d856046d9694391c70742e86ee1b78e38058420"
REPLACEMENTS = [
    ('#include "draft_policy.hpp"', '#include "draft_policy.hpp"\n#include "activity_capture.hpp"'),
    ('{auto t=Clock::now();f();value[name]+=elapsed(t);}',
     '{hs_capture::Scope span("service_phase",name);auto t=Clock::now();f();value[name]+=elapsed(t);}'),
    ('int rc=llama_decode(c,b);llama_batch_free(b);need(rc==0,"decode failure "+phase+" rc="+std::to_string(rc));llama_synchronize(c);',
     'int rc;{hs_capture::Scope submit("cuda_submit","llama_decode");rc=llama_decode(c,b);}'
     'llama_batch_free(b);need(rc==0,"decode failure "+phase+" rc="+std::to_string(rc));'
     '{hs_capture::Scope sync("cuda_sync","llama_synchronize");llama_synchronize(c);}'),
    ('json state(Context & ctx,int pending,int keep,bool persist){\n        auto bytes=canonical(ctx.c,pending,keep);',
     'json state(Context & ctx,int pending,int keep,bool persist,int generation=-1){\n'
     '        std::vector<uint8_t> bytes;\n'
     '        {hs_capture::Scope export_scope("kv_export",generation<0?"endpoint":"checkpoint",'
     '{{"role",ctx.is_draft?"draft":"target"},{"generation",generation},{"positions",keep}});'
     'bytes=canonical(ctx.c,pending,keep); }'),
    ('if(persist)result["payload"]=(store(objects,bytes.data(),bytes.size(),".kv")).string();',
     'if(persist){hs_capture::Scope save("kv_persist",generation<0?"endpoint":"checkpoint",'
     '{{"role",ctx.is_draft?"draft":"target"},{"generation",generation}});'
     'result["payload"]=(store(objects,bytes.data(),bytes.size(),".kv")).string();}'),
    ('state(target,pending,keep,false)', 'state(target,pending,keep,true,G)'),
    ('state(*draft,pending,keep,false)', 'state(*draft,pending,keep,true,G)'),
    ('auto payload=state(ctx,pending,keep,true);', 'auto payload=state(ctx,pending,keep,true,G);'),
    ('    const auto prompt=spec.at("prompt_ids")', '    hs_capture::Scope request_scope("request",spec.at("request_id"));\n'
     '    const auto prompt=spec.at("prompt_ids")'),
    ('        need(!own_logits||request_logits,',
     '        hs_capture::Scope forward("forward",phase,{{"label",label},{"position",pos},{"width",ids.size()},'
     '{"role",ctx.is_draft?"draft":"target"}});\n        need(!own_logits||request_logits,'),
    ('[&]{result=ctx.own(int(ids.size()),all);}', '[&]{hs_capture::Scope own("logits_export",label);'
     'result=ctx.own(int(ids.size()),all);}'),
    ('    while(!done){\n        int remaining=', '    while(!done){\n'
     '        hs_capture::Scope successor("cycle",cycle?"own_successor":"initial",{{"cycle",cycle}});\n'
     '        int remaining='),
    ('    std::unique_ptr<Context> target,draft;llama_model * tm=nullptr,*dm=nullptr;std::ofstream log;\n    try{',
     '    std::unique_ptr<hs_capture::Session> trace;\n'
     '    std::unique_ptr<Context> target,draft;llama_model * tm=nullptr,*dm=nullptr;std::ofstream log;\n    try{\n'
     '        if(argc==2 && std::string(argv[1])=="--cupti-probe"){uint32_t v=0;uint64_t t=0;'
     'hs_capture::cu(cuptiGetVersion(&v),"version probe");hs_capture::cu(cuptiGetTimestamp(&t),"clock probe");'
     'std::cout<<json({{"version",v},{"timestamp_nonzero",t>0}})<<std::endl;return t?0:2;}'),
    ('        auto load_start=Clock::now();llama_backend_init();',
     '        trace=std::make_unique<hs_capture::Session>(fs::path(argv[3]).parent_path());\n'
     '        auto setup=std::make_unique<hs_capture::Scope>("worker","setup");\n'
     '        auto load_start=Clock::now();llama_backend_init();'),
    ('if(dm)draft=std::make_unique<Context>(dm,false,true);\n        log',
     'if(dm)draft=std::make_unique<Context>(dm,false,true);\n        setup.reset();\n        log'),
    ('        auto teardown=Clock::now();draft.reset();target.reset();if(dm)llama_model_free(dm);dm=nullptr;'
     'if(tm)llama_model_free(tm);tm=nullptr;llama_backend_free();',
     '        auto teardown=Clock::now();{hs_capture::Scope cleanup("worker","teardown");'
     'draft.reset();target.reset();if(dm)llama_model_free(dm);dm=nullptr;if(tm)llama_model_free(tm);tm=nullptr;'
     'llama_backend_free();}\n        trace->finish(true);'),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-source", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    baseline = (a.base_source / "worker.cpp").read_bytes()
    if sha(baseline) != BASELINE:
        raise ValueError("accepted baseline worker source bytes differ")
    source = baseline.decode("utf-8").replace("\r\n", "\n")
    for before, after in REPLACEMENTS:
        if source.count(before) != 1:
            raise ValueError(f"capturing wrapper must match one accepted source boundary: {before[:80]}")
        source = source.replace(before, after, 1)
    a.out.mkdir(parents=True)
    incoming = Path(__file__).resolve().parent / "activity_capture.hpp"
    for filename in ("support.hpp", "draft_policy.hpp"):
        shutil.copyfile(a.base_source / filename, a.out / filename)
    shutil.copyfile(incoming, a.out / incoming.name)
    (a.out / "worker.cpp").write_bytes(source.encode())
    print(json.dumps({"base_worker_sha256": BASELINE, "capture_worker_source_sha256": sha(source.encode()),
                      "modified_boundaries": len(REPLACEMENTS), "backend_modified": False}))


if __name__ == "__main__":
    main()
