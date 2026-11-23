#include "support.hpp"
#include "draft_policy.hpp"
#include "ggml-backend.h"
#include <iostream>
#include <map>
#include <memory>

using SetArm=void (*)(int);
using Audit=int (*)(uint64_t*,int64_t*,int,int*);
static SetArm set_arm=nullptr;
static Audit audit=nullptr;
static uint64_t last_graph_counts[4]={};
using Pack4Audit=void (*)(uint64_t*);
static Pack4Audit pack4_audit=nullptr;
static DriverOptions options;
static void arm(int a){if(set_arm)set_arm(a);}
static const std::vector<std::string> phase_names={"context_s","target_prefill_s","target_decode_s","target_verify_s","draft_prefill_s","draft_sync_s","draft_propose_s","decision_commit_s","terminal_sync_s","other_host_s"};
struct Costs {
    std::map<std::string,double> value;
    Costs(){for(const auto & p:phase_names)value[p]=0;}
    template<class F>void measure(const std::string & name,F f){auto t=Clock::now();f();value[name]+=elapsed(t);}
};
struct Context {
    llama_context * c=nullptr;llama_model * model=nullptr;int mode=1,vocab=0,rows=0,calls=0;bool is_draft=false;uint64_t graph_identity_counts[4]={};
    json phase_work=json::object();std::vector<int64_t> physical_extents;
    Context(llama_model * m,bool reference,bool draft):model(m),is_draft(draft){
        mode=draft?options.draft_mode():1;arm(mode);
        auto cp=llama_context_default_params();cp.n_ctx=1024;cp.n_batch=32;cp.n_ubatch=reference?1:(draft?options.draft_ubatch():32);
        cp.n_outputs_max=cp.n_outputs_max_per_seq=reference?1:(draft?options.draft_ubatch():32);cp.n_seq_max=1;
        cp.n_threads=cp.n_threads_batch=2;cp.type_k=cp.type_v=GGML_TYPE_F16;cp.flash_attn_type=LLAMA_FLASH_ATTN_TYPE_DISABLED;cp.attention_type=LLAMA_ATTENTION_TYPE_CAUSAL;
        c=llama_init_from_model(model,cp);need(c,"context initialization");vocab=llama_vocab_n_tokens(llama_model_get_vocab(model));
    }
    ~Context(){if(c)llama_free(c);}
    void reset(int a){mode=a;arm(mode);llama_memory_clear(llama_get_memory(c),true);need(llama_memory_seq_pos_max(llama_get_memory(c),0)<0,"reset not empty");rows=calls=0;std::fill(graph_identity_counts,graph_identity_counts+4,0);phase_work=json::object();}
    void call(const std::vector<int> & ids,int position,bool all,const std::string & phase,bool request_logits=true){
        need(!ids.empty() && ids.size()<=32,"native width");arm(mode);auto b=llama_batch_init(int(ids.size()),0,1);b.n_tokens=int(ids.size());
        for(int i=0;i<b.n_tokens;++i){b.token[i]=ids[i];b.pos[i]=position+i;b.n_seq_id[i]=1;b.seq_id[i][0]=0;b.logits[i]=request_logits&&(all||i==b.n_tokens-1);}
        int rc=llama_decode(c,b);llama_batch_free(b);need(rc==0,"decode failure "+phase+" rc="+std::to_string(rc));llama_synchronize(c);
        rows+=int(ids.size());++calls;
        if(!phase_work.contains(phase))phase_work[phase]={{"rows",0},{"calls",0}};
        phase_work[phase]["rows"]=phase_work[phase]["rows"].get<int>()+int(ids.size());phase_work[phase]["calls"]=phase_work[phase]["calls"].get<int>()+1;
        physical_extents.clear();if(audit){uint64_t counts[4];int64_t ext[32];int a=0;int n=audit(counts,ext,32,&a);need(a==mode,"graph arm identity");for(int i=0;i<4;++i){need(counts[i]>=last_graph_counts[i],"graph audit monotone");graph_identity_counts[i]+=counts[i]-last_graph_counts[i];last_graph_counts[i]=counts[i];}physical_extents.assign(ext,ext+n);}
    }
    std::vector<std::vector<float>> own(int n,bool all){
        std::vector<std::vector<float>> result;int count=all?n:1;
        for(int i=0;i<count;++i){const float * p=llama_get_logits_ith(c,all?i:-1);need(p,"owned output row missing");result.emplace_back(p,p+vocab);}
        return result;
    }
    void trim(int keep){arm(mode);need(llama_memory_seq_rm(llama_get_memory(c),0,keep,-1),"suffix trim");need(llama_memory_seq_pos_min(llama_get_memory(c),0)==0 && llama_memory_seq_pos_max(llama_get_memory(c),0)==keep-1,"trim prefix bounds");}
};
struct Capture {
    bool enabled;fs::path dir,objects;std::ofstream vectors,index;uint64_t offset=0;json checkpoints=json::object(),expected,expected_sd;
    Capture(bool e,const fs::path & d,const fs::path & o,const json & spec):enabled(e),dir(d),objects(o){
        if(enabled){vectors.open(dir/"vectors.f32",std::ios::binary);index.open(dir/"vectors.jsonl");need(bool(vectors)&&bool(index),"capture open");}
        if(spec.contains("expected_target"))expected=read_json(spec["expected_target"].get<std::string>());
        if(spec.contains("expected_sd"))expected_sd=read_json(spec["expected_sd"].get<std::string>());
    }
    void logits(const std::string & name,const std::vector<std::vector<float>> & owned,int first_position,const std::vector<int64_t> & extents,int row_offset=0){
        if(!enabled)return;
        for(size_t i=0;i<owned.size();++i){auto & row=owned[i];for(float x:row)need(std::isfinite(x),"captured nonfinite logits");
            index<<json({{"name",name+"/"+std::to_string(i+row_offset)},{"offset",offset},{"bytes",row.size()*4},{"position",first_position+int(i)},{"physical_extents",extents}}).dump()<<'\n';
            vectors.write((const char*)row.data(),row.size()*4);offset+=row.size()*4;
        }
        need(bool(vectors)&&bool(index),"capture write");
    }
    json state(Context & ctx,int pending,int keep,bool persist){
        auto bytes=canonical(ctx.c,pending,keep);Sha hash;for(size_t off=0;off<bytes.size();off+=1024*1024)hash.update(bytes.data()+off,std::min<size_t>(1024*1024,bytes.size()-off));
        auto h=hash.finish();json result={{"sha256",h},{"bytes",bytes.size()},{"active_tokens",keep},{"pending_id",pending},{"pending_position",keep}};
        if(persist)result["payload"]=(store(objects,bytes.data(),bytes.size(),".kv")).string();
        return result;
    }
    void checkpoint(Context & target,Context * draft,int G,int pending,int keep){
        if(!enabled)return;auto key=std::to_string(G);json check={{"target",state(target,pending,keep,false)}};
        if(draft)check["draft"]=state(*draft,pending,keep,false);else check["draft"]={{"sha256",digest("HSSDINACTIVE1")},{"initialized",false}};
        checkpoints[key]=check;
        auto verify=[&](const json & ref,const std::string & model,Context & ctx){
            if(ref.is_null() || !ref.contains("checkpoints") || !ref["checkpoints"].contains(key))return;
            auto expected=ref["checkpoints"][key][model]["sha256"];
            if(check[model]["sha256"]!=expected){auto payload=state(ctx,pending,keep,true);write_json(dir/"FIRST_MISMATCH.json",{{"G",G},{"model",model},{"actual",payload},{"expected_sha256",expected},{"reference",ref.value("request_id","")}});throw std::runtime_error("canonical checkpoint mismatch "+model+" G="+key);}
        };
        verify(expected,"target",target);if(draft)verify(expected_sd,"draft",*draft);
    }
};

static json request(Context & target,Context * pool_draft,const json & spec,const fs::path & objects,const fs::path & dir){
    const auto prompt=spec.at("prompt_ids").get<std::vector<int>>();int P=int(prompt.size());need(P>0 && P+128+3+1<=1024,"prompt capacity");
    need(digest(json(prompt).dump())==spec["prompt_ids_sha256"],"prompt identity");
    std::string name=spec["arm"];bool replay=name=="R_TRACE",sd=name.rfind("SD_",0)==0 || replay;
    bool capture=spec.value("capture",false);int mode=(name=="TO_C"||name=="SD_C")?2:1;
    int qual_only=spec.value("qual_only_k_max",0);
    int k_limit=request_k_max(sd,capture,spec.value("stage",std::string())=="qualification",spec.value("k_max",3),qual_only);
    Capture cap(capture,dir,objects,spec);Costs costs;std::vector<int> decisions;std::vector<float> frontier;
    std::vector<std::vector<float>> owned,last_draft;json transactions=json::array(),geometry=json::array();
    json replay_rows;if(replay)replay_rows=read_json(spec.at("replay_request").get<std::string>()).at("transactions");
    int draft_saved_rows=0,draft_deferred_commits=0;
    std::map<int,int> widths={{1,0},{2,0},{3,0},{4,0}};int accepted=0,proposed=0,rejections=0,bonus=0,tail=0,cycle=0;bool draft_active=false,done=false,eog=false;double ttft=0;bool has_ttft=false;
    auto vocab=llama_model_get_vocab(target.model);auto is_eog=[&](int t){return llama_vocab_is_eog(vocab,t);};
    uint64_t pack4_before[6]={},pack4_prefill[6]={},pack4_after[6]={};if(pack4_audit)pack4_audit(pack4_before);
    if(audit){int64_t ext[32];int a=0;audit(last_graph_counts,ext,32,&a);}
    int target_reused_before=llama_perf_context(target.c).n_reused,draft_reused_before=pool_draft?llama_perf_context(pool_draft->c).n_reused:0;
    auto start=Clock::now();costs.measure("context_s",[&]{target.reset(mode);});
    auto call=[&](Context & ctx,const std::vector<int> & ids,int pos,bool all,const std::string & phase,const std::string & label,int row_offset=0,bool request_logits=true,bool own_logits=true){
        need(!own_logits||request_logits,"owned logits require an output");
        costs.measure(phase,[&]{ctx.call(ids,pos,all,phase,request_logits);});std::vector<std::vector<float>> result;
        if(own_logits)costs.measure("decision_commit_s",[&]{result=ctx.own(int(ids.size()),all);});
        cap.logits(label,result,all?pos:pos+int(ids.size())-1,ctx.physical_extents,row_offset);return result;
    };
    auto prefill=[&](Context & ctx,const std::string & phase,const std::string & label){std::vector<std::vector<float>> last;
        for(int i=0;i<P;i+=32){int n=std::min(32,P-i);auto out=prefill_output_policy(ctx.is_draft,options.deferred(),capture,i+n==P,options.keep_unused_logits());
            last=call(ctx,std::vector<int>(prompt.begin()+i,prompt.begin()+i+n),i,false,phase,label+"/"+std::to_string(i),0,out.request_logits,out.own_logits);}return last;};
    auto keep_frontier=[&](std::vector<float> & row){if(options.deferred())frontier=std::move(row);else frontier=row;};
    owned=prefill(target,"target_prefill_s","target-prefill");
    if(pack4_audit)pack4_audit(pack4_prefill); // Six host counters; included in continuous service/other_host.
    costs.measure("decision_commit_s",[&]{keep_frontier(owned.back());decisions.push_back(greedy(frontier));eog=is_eog(decisions.back());done=eog;if(!eog){ttft=elapsed(start);has_ttft=true;}});
    int base=P,pending=decisions.back();cap.checkpoint(target,nullptr,int(decisions.size()),pending,base);
    if(sd && !replay && !done){need(pool_draft,"SD resident draft missing");costs.measure("context_s",[&]{pool_draft->reset(options.draft_mode());});draft_active=true;last_draft=prefill(*pool_draft,"draft_prefill_s","draft-prefill");}
    while(!done){
        int remaining=128-int(decisions.size());need(remaining>0,"remaining decisions");
        if(!sd){owned=call(target,{pending},base,false,"target_decode_s","ordinary/"+std::to_string(decisions.size()));
            costs.measure("decision_commit_s",[&]{keep_frontier(owned[0]);pending=greedy(frontier);decisions.push_back(pending);++base;eog=is_eog(pending);done=eog||decisions.size()==128;});
            cap.checkpoint(target,nullptr,int(decisions.size()),pending,base);continue;
        }
        int k_eff=std::min(k_limit,remaining-1),seed=pending,draft_end=base;std::vector<int> proposals;bool draft_eog=false;
        if(replay){need(cycle<int(replay_rows.size()),"oracle replay too short");auto expected=replay_rows[cycle];need(expected["base"]==base && expected["seed"]==seed && expected["k_eff"]==k_eff,"independent oracle seed/position");proposals=expected["proposals"].get<std::vector<int>>();draft_eog=expected["draft_eog"];need(int(proposals.size())<=k_eff,"oracle proposal bound");}
        else{
            if(!options.deferred())costs.measure("decision_commit_s",[&]{pool_draft->trim(base);});
            bool seed_owned=!options.deferred()||capture||k_eff>0,seed_logits=seed_owned||options.keep_unused_logits();
            last_draft=call(*pool_draft,{seed},base,false,"draft_sync_s","draft-sync/"+std::to_string(cycle),0,seed_logits,seed_owned);draft_end=base+1;
            for(int j=0;j<k_eff;++j){int t=0;costs.measure("decision_commit_s",[&]{t=greedy(last_draft[0]);});proposals.push_back(t);
                draft_eog=llama_vocab_is_eog(llama_model_get_vocab(pool_draft->model),t);
                if(materialize_proposal_now(options.deferred(),j,k_eff,draft_eog)){
                    last_draft=call(*pool_draft,{t},base+1+j,false,"draft_propose_s","draft-proposal/"+std::to_string(cycle)+"/"+std::to_string(j));++draft_end;
                }
                if(draft_eog)break;
            }
        }
        std::vector<int> inputs={seed};inputs.insert(inputs.end(),proposals.begin(),proposals.end());int q=int(inputs.size());
        if(replay){owned.clear();for(int row=0;row<q;++row){auto one=call(target,{inputs[row]},base+row,false,"target_verify_s","verify/"+std::to_string(cycle),row);owned.push_back(std::move(one[0]));}}
        else owned=call(target,inputs,base,true,"target_verify_s","verify/"+std::to_string(cycle));
        std::vector<int> predictions;Selection selected;
        costs.measure("decision_commit_s",[&]{for(auto & row:owned)predictions.push_back(greedy(row));selected=select_cycle(proposals,predictions,base,remaining,is_eog);
            decisions.insert(decisions.end(),selected.emitted.begin(),selected.emitted.end());keep_frontier(owned[selected.frontier]);pending=decisions.back();base=selected.keep;eog=is_eog(pending);done=eog||decisions.size()==128;
            need(base==P+int(decisions.size())-1,"canonical pending selection");target.trim(base);
        });
        if(draft_active){
            auto plan=draft_commit_plan(options.deferred(),int(proposals.size()),draft_end,base);
            if(plan.missing_rows){
                // Only an accepted last proposal whose KV is retained is materialized.
                // Its output distribution is not consumed; capture may request it.
                call(*pool_draft,{proposals.back()},draft_end,false,"draft_propose_s","draft-proposal/"+std::to_string(cycle)+"/"+std::to_string(proposals.size()-1),0,capture||options.keep_unused_logits(),capture);
                ++draft_deferred_commits;
            }
            draft_saved_rows+=plan.skipped_rows;
            costs.measure("decision_commit_s",[&]{pool_draft->trim(base);});
        }
        json entry={{"cycle",cycle},{"base",base-int(selected.emitted.size())},{"seed",seed},{"k_eff",k_eff},{"proposals",proposals},{"decisions",predictions},{"accepted",selected.accepted},{"rejected",selected.rejected},{"branch",selected.branch},{"emitted",selected.emitted},{"keep",base},{"pending",pending},{"G",decisions.size()},{"width",q},{"frontier_row",selected.frontier},{"draft_eog",draft_eog}};
        // The previous base is P+old_G-1, including accepted-terminal trim.
        entry["base"]=P+int(decisions.size())-int(selected.emitted.size())-1;
        if(replay)need(entry==replay_rows[cycle],"R recomputed transaction differs from candidate");
        transactions.push_back(entry);if(!replay)geometry.push_back({{"cycle",cycle},{"positions_begin",entry["base"]},{"width",q},{"extent_vector",target.physical_extents}});
        ++widths[q];accepted+=selected.accepted;proposed+=int(proposals.size());rejections+=selected.rejected;bonus+=selected.branch=="bonus";tail+=selected.branch=="tail";++cycle;
        cap.checkpoint(target,draft_active?pool_draft:nullptr,int(decisions.size()),pending,base);
    }
    costs.measure("decision_commit_s",[&]{need(base==P+int(decisions.size())-1,"final pending position");target.trim(base);if(draft_active)pool_draft->trim(base);});
    need(!replay || cycle==int(replay_rows.size()),"independent R consumed every proposal cycle");
    costs.measure("terminal_sync_s",[&]{arm(mode);llama_synchronize(target.c);if(draft_active){arm(pool_draft->mode);llama_synchronize(pool_draft->c);}});
    auto end=Clock::now();double service=elapsed(start,end),accounted=0;for(const auto & x:costs.value)accounted+=x.second;
    need(service>=accounted-1e-6,"phase closure");costs.value["other_host_s"]=std::max(0.0,service-accounted);
    if(pack4_audit)pack4_audit(pack4_after);
    // Endpoint export and persistence are after the continuous native service interval.
    json target_state=cap.state(target,pending,base,true),draft_state=draft_active?cap.state(*pool_draft,pending,base,true):json{{"sha256",digest("HSSDINACTIVE1")},{"initialized",false}};
    auto frontier_path=store(objects,frontier.data(),frontier.size()*4,".f32");
    std::vector<int> display=decisions;if(eog)display.pop_back();json hist;for(auto x:widths)hist[std::to_string(x.first)]=x.second;
    json result={{"event","request"},{"request_id",spec["request_id"]},{"arm",name},{"capture",capture},{"service_s",service},{"ttft_s",has_ttft?json(ttft):json(nullptr)},
        {"decision_ids",decisions},{"display_ids",display},{"stop_reason",eog?"EOG":"CAP"},{"eog_id",eog?json(pending):json(nullptr)},{"pending_id",pending},{"pending_position",base},{"active_target_tokens",base},
        {"target_endpoint_sha256",target_state["sha256"]},{"target_frontier_sha256",frontier_path.stem().string()},{"draft_endpoint_sha256",draft_state["sha256"]},{"sd_trace_sha256",sd?json(digest(transactions.dump())):json(nullptr)},
        {"draft_profile",options.draft_profile},{"frontend_profile",options.frontend_profile},{"host_fix","need-literal-v1"},{"target_pack4_requested",options.target_pack4},{"unused_draft_logits",options.unused_draft_logits},{"k_max_effective",k_limit},{"qual_only_k_max",qual_only},
        {"draft_mode",draft_active?json(pool_draft->mode):json(nullptr)},{"draft_ubatch",draft_active?json(llama_n_ubatch(pool_draft->c)):json(nullptr)},
        {"draft_saved_rows",draft_saved_rows},{"draft_deferred_commits",draft_deferred_commits},
        {"target_rows",target.rows},{"draft_rows",draft_active?pool_draft->rows:0},{"target_calls",target.calls},{"draft_calls",draft_active?pool_draft->calls:0},
        {"target_phase_work",target.phase_work},{"draft_phase_work",draft_active?pool_draft->phase_work:json::object()},
        {"cycles",cycle},{"proposed",proposed},{"accepted",accepted},{"rejections",rejections},{"bonus_events",bonus},{"tail_steps",tail},{"verify_width_hist",hist},{"draft_initialized",draft_active},
        {"transactions",transactions},{"verification_geometry",geometry},{"checkpoints",cap.checkpoints},{"target_endpoint",target_state},{"draft_endpoint",draft_state},{"frontier_payload",frontier_path.string()},
        {"native_start_tick",start.time_since_epoch().count()},{"native_end_tick",end.time_since_epoch().count()},{"native_tick_period_num",Clock::period::num},{"native_tick_period_den",Clock::period::den},{"capture_timing_is_not_performance",capture}};
    result["target_graph_reused_delta"]=llama_perf_context(target.c).n_reused-target_reused_before;
    result["draft_graph_reused_delta"]=draft_active?llama_perf_context(pool_draft->c).n_reused-draft_reused_before:0;
    result["graph_identity_fields"]={"builds","arm_incompatibilities","extent_incompatibilities","compatible_identity_checks"};
    result["target_graph_identity_delta"]={target.graph_identity_counts[0],target.graph_identity_counts[1],target.graph_identity_counts[2],target.graph_identity_counts[3]};
    result["draft_graph_identity_delta"]=draft_active?json({pool_draft->graph_identity_counts[0],pool_draft->graph_identity_counts[1],pool_draft->graph_identity_counts[2],pool_draft->graph_identity_counts[3]}):json({0,0,0,0});
    if(pack4_audit){json delta=json::array(),prefill_delta=json::array(),continuation_delta=json::array();for(int i=0;i<6;++i){
            need(pack4_after[i]>=pack4_prefill[i]&&pack4_prefill[i]>=pack4_before[i],"pack4 monotone audit");
            delta.push_back(pack4_after[i]-pack4_before[i]);prefill_delta.push_back(pack4_prefill[i]-pack4_before[i]);continuation_delta.push_back(pack4_after[i]-pack4_prefill[i]);
            if(mode==1)need(pack4_after[i]==pack4_before[i],"B dispatch unexpectedly entered C4");}
        if(options.target_pack4 && mode==2 && sd && widths[2]+widths[3]+widths[4]>0)
            need(pack4_after[1]>pack4_prefill[1],"C4 verify candidate had no admitted dispatch");
        result["pack4_dispatch_delta"]=delta;result["pack4_prefill_dispatch_delta"]=prefill_delta;
        result[sd?"pack4_verify_dispatch_delta":"pack4_decode_dispatch_delta"]=continuation_delta;
        result["pack4_dispatch_fields"]={"marked_C_calls","admitted_calls","columns","full4_tiles","tail_tiles","fallbacks"};}
    for(auto x:costs.value)result[x.first]=x.second;
    if(audit){uint64_t counts[4];int64_t ext[32];int a=0;audit(counts,ext,32,&a);result["graph_audit_cumulative"]={counts[0],counts[1],counts[2],counts[3]};}
    return result;
}

static void fixtures(){
    auto eog=[](int t){return t==99;};int checked=0;
    for(int reject=0;reject<3;++reject){std::vector<int> p={10,11,12},d=p;d.push_back(13);d[reject]=20;auto s=select_cycle(p,d,765,10,eog);need(s.rejected && s.accepted==reject && s.frontier==reject && s.keep==766+reject,"reject fixture");++checked;}
    auto s=select_cycle({10,11,12},{10,11,12,13},765,10,eog);need(s.branch=="bonus"&&s.keep==769&&s.frontier==3,"bonus fixture");++checked;
    s=select_cycle({}, {14}, 880, 1,eog);need(s.branch=="tail"&&s.done&&s.keep==881&&s.frontier==0,"q1 cap tail");++checked;
    for(int a=1;a<=3;++a){std::vector<int> p={10,11,12},d={10,11,12,13};p[a-1]=d[a-1]=99;s=select_cycle(p,d,765,10,eog);need(s.done&&s.accepted==a&&s.keep==765+a&&s.frontier==a-1,"accepted EOG frontier");++checked;
        s=select_cycle({10,11,12},{10,11,12,13},765,a,eog);need(s.done&&s.keep==765+a&&s.frontier==a-1,"accepted cap frontier");++checked;}
    s=select_cycle({10,11,12},{10,99,12,13},765,10,eog);need(s.done&&s.keep==767&&s.frontier==1&&s.branch=="correction","correction EOG");++checked;
    s=select_cycle({10,11,12},{10,11,12,99},765,10,eog);need(s.done&&s.keep==769&&s.frontier==3,"bonus EOG");++checked;
    auto ext=[](int p){std::vector<int> v;for(int i=0;i<4;++i)v.push_back(std::min(1024,((p+i+1+255)/256)*256));return v;};
    need(ext(765)==std::vector<int>({768,768,768,1024})&&ext(766)==std::vector<int>({768,768,1024,1024})&&ext(765)!=ext(766),"fixed view identity fixture");++checked;
    need(greedy({1,2,2})==1,"lowest ID tie");++checked;
    need(eog(99) && std::min(3,1-1)==0,"initial EOG and tail policy");++checked;
    s=select_cycle({10,11,12},{10,20,12,13},765,2,eog);need(s.done&&s.branch=="correction"&&s.keep==767&&s.frontier==1,"correction cap");++checked;
    s=select_cycle({10,11,12},{10,11,12,13},765,4,eog);need(s.done&&s.branch=="bonus"&&s.keep==769,"bonus cap");++checked;
    s=select_cycle({}, {99}, 880, 1,eog);need(s.done&&s.branch=="tail"&&s.frontier==0,"q1 EOG tail");++checked;
    s=select_cycle({99},{20,21},765,10,eog);need(s.rejected&&!s.done&&s.emitted==std::vector<int>({20}),"draft EOG remains a rejectable proposal");++checked;
    std::cout<<json({{"event","CPU_FIXTURES_PASS"},{"cases",checked}})<<std::endl;
}

int main(int argc,char ** argv){
    std::unique_ptr<Context> target,draft;llama_model * tm=nullptr,*dm=nullptr;std::ofstream log;
    try{
        if(argc==2 && std::string(argv[1])=="--fixtures"){fixtures();return 0;}
        if(argc==5 && std::string(argv[1])=="--state-fixture"){
            std::ifstream in(argv[2],std::ios::binary);need(bool(in),"CPU state fixture");std::vector<uint8_t> raw((std::istreambuf_iterator<char>(in)),{});
            auto b=canonical_bytes(raw,std::stoi(argv[3]),std::stoi(argv[4]));std::cout<<json({{"event","CPU_STATE_PASS"},{"raw_bytes",raw.size()},{"canonical_bytes",b.size()},{"sha256",digest(b.data(),b.size())}})<<std::endl;return 0;
        }
        options=driver_options(std::getenv("HS_SD_DRAFT_PROFILE"),std::getenv("HS_SD_FRONTEND"),std::getenv("HS_SD_TARGET_PACK4"),std::getenv("HS_SD_UNUSED_DRAFT_LOGITS"));
        need(argc==6,"TARGET DRAFT RESULTS OBJECTS R|BC; requests on stdin");bool reference=std::string(argv[5])=="R";
        fs::path objects=argv[4];fs::create_directories(objects);log.open(argv[3],std::ios::app);need(bool(log),"native results open");
        llama_log_set([](ggml_log_level level,const char * text,void*){if(level>=GGML_LOG_LEVEL_INFO)fputs(text,stderr);},nullptr);
        auto load_start=Clock::now();llama_backend_init();ggml_backend_dev_t gpu=nullptr;
        for(size_t i=0;i<ggml_backend_dev_count();++i){auto d=ggml_backend_dev_get(i);if(ggml_backend_dev_type(d)==GGML_BACKEND_DEVICE_TYPE_GPU){need(!gpu,"multiple GPU devices");gpu=d;}}
        need(gpu,"CUDA GPU unavailable");ggml_backend_dev_t devices[]={gpu,nullptr};auto mp=llama_model_default_params();mp.devices=devices;mp.n_gpu_layers=999;mp.split_mode=LLAMA_SPLIT_MODE_NONE;
        tm=llama_model_load_from_file(argv[1],mp);need(tm,"target load");
        if(!reference){auto h=GetModuleHandleA("ggml-cuda.dll");set_arm=(SetArm)GetProcAddress(h,"hs248_set_arm");audit=(Audit)GetProcAddress(GetModuleHandleA("llama.dll"),"hs_sd_graph_audit");need(set_arm && audit,"candidate APIs");
            pack4_audit=(Pack4Audit)GetProcAddress(h,"hs_sd_pack4_audit");need(!options.target_pack4||pack4_audit,"pack4 audit API missing");
            if(options.native_draft()){using Capability=int(*)();auto native=(Capability)GetProcAddress(GetModuleHandleA("llama.dll"),"hs_sd_native_draft_capability");need(native&&native()==1,"native-draft runtime patch missing");}
            arm(1);dm=llama_model_load_from_file(argv[2],mp);need(dm,"draft load");}
        auto load_end=Clock::now();target=std::make_unique<Context>(tm,reference,false);if(dm)draft=std::make_unique<Context>(dm,false,true);
        log<<json({{"event","loaded"},{"draft_profile",options.draft_profile},{"frontend_profile",options.frontend_profile},{"host_fix","need-literal-v1"},{"target_pack4_requested",options.target_pack4},{"unused_draft_logits",options.unused_draft_logits},{"pack4_audit_available",bool(pack4_audit)},{"reference",reference},{"gpu",ggml_backend_dev_description(gpu)},{"model_load_s",elapsed(load_start,load_end)},{"context_setup_s",elapsed(load_end)},
            {"target_ubatch",llama_n_ubatch(target->c)},{"target_outputs_reserve",reference?1:32},{"draft_ubatch",draft?json(llama_n_ubatch(draft->c)):json(nullptr)},{"vocab",target->vocab}}).dump()<<'\n';log.flush();
        std::string line;while(std::getline(std::cin,line)){
            if(line.empty())continue;auto spec=json::parse(line);if(spec.value("command","")=="stop")break;
            std::string id=spec.at("request_id");need(id.find_first_of("/\\:")==std::string::npos && id.find("..") == std::string::npos,"request ID path");
            std::string a=spec.at("arm");need(reference?(a=="R_TO"||a=="R_TRACE"):(a=="TO_U"||a=="TO_C"||a=="SD_U"||a=="SD_C"),"arm/API binding");
            fs::path dir=spec.at("request_dir").get<std::string>();need(fs::is_directory(dir),"request directory");
            log<<json({{"event","request_start"},{"request_id",id}}).dump()<<'\n';log.flush();
            auto result=request(*target,draft.get(),spec,objects,dir);write_json(dir/"native.json",result);log<<result.dump()<<'\n';log.flush();std::cout<<json({{"event","complete"},{"request_id",id}}).dump()<<std::endl;
        }
        auto teardown=Clock::now();draft.reset();target.reset();if(dm)llama_model_free(dm);dm=nullptr;if(tm)llama_model_free(tm);tm=nullptr;llama_backend_free();
        log<<json({{"event","done"},{"window_teardown_s",elapsed(teardown)}}).dump()<<'\n';log.flush();return 0;
    }catch(const std::exception & ex){if(log){log<<json({{"event","failure"},{"error",ex.what()}}).dump()<<'\n';log.flush();}std::cerr<<"real-SD failure: "<<ex.what()<<std::endl;draft.reset();target.reset();if(dm)llama_model_free(dm);if(tm)llama_model_free(tm);return 1;}
}
