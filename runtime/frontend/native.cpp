// Four-arm resident application frontend. Numerical archives are not rebuilt.
#include "llama.h"
#include "llama-model.h"
#include "ggml.h"
#include "ggml-backend.h"
#include <nlohmann/json.hpp>
#include <algorithm>
#include <array>
#include <cmath>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <numeric>
#include <stdexcept>
#include <string>
#include <unistd.h>
#include <vector>
#include "transaction.hpp"
#include "draft_work.hpp"
using json=nlohmann::json;
namespace fs=std::filesystem;
using Clock=std::chrono::steady_clock;
static void need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
static int64_t ns(){timespec t{};need(clock_gettime(CLOCK_MONOTONIC,&t)==0,"Monotonic clock");return int64_t(t.tv_sec)*1000000000+t.tv_nsec;}
static double elapsed(int64_t a){return (ns()-a)*1e-9;}
static double since(Clock::time_point t){return std::chrono::duration<double>(Clock::now()-t).count();}
static json load(const fs::path& p){std::ifstream f(p);json j;f>>j;need(bool(f),"JSON input");return j;}
static void write_json(const fs::path& p,const json& j){fs::create_directories(p.parent_path());need(!fs::exists(p),"Preserve existing JSON");std::ofstream f(p);f<<j.dump(2)<<'\n';need(bool(f),"JSON output");}
static void write_bytes(const fs::path& p,const void* b,size_t n){fs::create_directories(p.parent_path());need(!fs::exists(p),"Preserve existing payload");std::ofstream f(p,std::ios::binary);f.write(static_cast<const char*>(b),n);need(bool(f),"Payload output");}
#include "state.hpp"
#ifndef REAL_SD_ORACLE
#include "hs_scope.h"
#include "hsc_counter.h"
#include "inherited/work_counts.h"
extern "C" void hs_strong_select_arm_at_boundary(int);
extern "C" uint32_t hs_a5000_native4_capability_v1() __attribute__((weak));
extern "C" uint64_t hs_work_native4_dispatches();
extern "C" uint64_t hs_work_native4_columns();
extern "C" uint32_t hs_prefill_pack4_capability_v1();
extern "C" void hs_prefill_pack4_audit(uint64_t *);

extern "C" void hs_strong_decode_begin();
extern "C" void hs_strong_decode_end();
inline bool phase_observe=false;
#include "inherited/resident_context.hpp"
#endif

static const char* target_C_profile(){
#ifndef REAL_SD_ORACLE
    if(hs_a5000_native4_capability_v1){need(hs_a5000_native4_capability_v1()==0x48534E34,"Native4 capability identity");return "a5000_C_native4_small_width_v1";}
    return "a5000_C_q1_grouped_v1";
#else
    return "pristine_q1_reference";
#endif
}
static bool prefill_p4_enabled(){
#ifndef REAL_SD_ORACLE
    static const bool enabled=[](){
        const char* value=std::getenv("HS_PREFILL_PACK4");
        need(value && (std::string(value)=="0" || std::string(value)=="1"),"Explicit immutable P4 process environment");
        need(hs_prefill_pack4_capability_v1()==0x48535034,"Linked P4 capability");
        return std::string(value)=="1";
    }();
    return enabled;
#else
    return false;
#endif
}
static int greedy(const std::vector<float>& v){need(!v.empty(),"Owned vocabulary row");int best=0;for(size_t i=0;i<v.size();++i){need(std::isfinite(v[i]),"Finite complete logits");if(v[i]>v[best])best=int(i);}return best;}
struct Timer {
    std::array<int64_t,9> part{};
    template<class F>auto run(int p,F f){auto t=ns();auto v=f();part[p]+=ns()-t;return v;}
    template<class F>void action(int p,F f){auto t=ns();f();part[p]+=ns()-t;}
};
enum Phase{CONTEXT,PREFILL,DECODE,VERIFY,D_PREFILL,D_SYNC,D_PROPOSE,DECISION,SYNC};
static const std::array<const char*,9> phase_names={"context_s","target_prefill_s","target_decode_s","target_verify_s","draft_prefill_s","draft_sync_s","draft_propose_s","decision_commit_s","terminal_sync_s"};
struct Context {
    llama_context* c=nullptr;llama_model* model;
    const bool target;const int arm;
    bool capture=false;
    struct {std::string phase;int base=0,caller=0;bool bad=false;} obs;
    fs::path out;int calls=0,logical_calls=0;int64_t rows=0,attempted_rows=0;
    std::map<std::string,double> phases;
    json vectors=json::array(),native_calls=json::array();
#ifndef REAL_SD_ORACLE
    PhaseContext plan;
#endif
    Context(llama_model* m,bool istarget,int selected):model(m),target(istarget),arm(selected){
#ifndef REAL_SD_ORACLE
        hs_strong_select_arm_at_boundary(arm);hs_scope::requested_layout=0;hs_scope::active=false;
#endif
        auto p=llama_context_default_params();p.n_ctx=1024;p.n_batch=1024;p.n_seq_max=1;
#ifdef REAL_SD_ORACLE
        p.n_ubatch=1;p.n_outputs_max=1;p.n_outputs_max_per_seq=1;
#else
        p.n_ubatch=target?32:4;p.n_outputs_max=target?32:1;p.n_outputs_max_per_seq=target?32:1;
#endif
        p.n_threads=2;p.n_threads_batch=2;p.type_k=GGML_TYPE_F16;p.type_v=GGML_TYPE_F16;
        p.flash_attn_type=LLAMA_FLASH_ATTN_TYPE_DISABLED;
        c=llama_init_from_model(m,p);need(c,"Resident context initialization");llama_synchronize(c);
        need(llama_n_ctx(c)==1024 && llama_n_ubatch(c)==p.n_ubatch,"Observed context/physical microbatch");
    }
    ~Context(){if(c)llama_free(c);}
    void reset(bool cap,const fs::path& dir){
        capture=cap;out=dir;calls=logical_calls=0;rows=attempted_rows=0;phases.clear();vectors=json::array();native_calls=json::array();
#ifndef REAL_SD_ORACLE
        hs_strong_select_arm_at_boundary(arm);hs_scope::active=target;plan.clear();
#endif
        llama_memory_clear(llama_get_memory(c),false);llama_synchronize(c);
        need(llama_memory_seq_pos_min(llama_get_memory(c),0)==-1 && llama_memory_seq_pos_max(llama_get_memory(c),0)==-1,"Complete request reset");
    }
    std::vector<std::vector<float>> decode(const std::vector<int>& ids,int position,bool all,const char* phase,bool want_logits=true,bool own_logits=true){
        need(!target || (want_logits && own_logits),"Target output contract is unchanged");
        need(!ids.empty() && position>=0 && position+int(ids.size())<=1024,"Native append capacity");
        attempted_rows+=ids.size();const int logical=logical_calls++;
        std::vector<std::vector<float>> outputs;
#ifndef REAL_SD_ORACLE
        hs_strong_select_arm_at_boundary(arm);hs_scope::requested_layout=0;hs_scope::active=target;
        hs_strong_decode_begin();
        try{
            if(target){plan.decode(*this,ids,position,all,phase);outputs=std::move(plan.outputs);}
            else outputs=direct(ids,position,all,phase,want_logits,own_logits);
        }catch(...){hs_strong_decode_end();throw;}
        hs_strong_decode_end();
#else
        outputs=direct(ids,position,all,phase,want_logits,own_logits);
#endif
        rows+=ids.size();
        if(capture)for(size_t j=0;j<outputs.size();++j)if(!outputs[j].empty()){
            const auto name="vectors/"+std::string(target?"target":"draft")+"-call"+std::to_string(logical)+"-row"+std::to_string(j)+".f32";
            write_bytes(out/name,outputs[j].data(),outputs[j].size()*4);
            vectors.push_back({{"call",logical},{"row",j},{"position",position+int(j)},{"phase",phase},{"path",name},{"bytes",outputs[j].size()*4},{"sha256",digest_bytes(outputs[j].data(),outputs[j].size()*4)}});
        }
        native_calls.push_back({{"logical_call",logical},{"phase",phase},{"position",position},{"rows",ids.size()},{"outputs_all",all},{"outputs_requested",want_logits},{"outputs_owned",want_logits&&own_logits}});
        return outputs;
    }
    std::vector<std::vector<float>> direct(const std::vector<int>& ids,int pos,bool all,const char* phase,bool want_logits=true,bool own_logits=true){
        auto b=llama_batch_init(int(ids.size()),0,1);b.n_tokens=int(ids.size());
        for(int i=0;i<b.n_tokens;++i){b.token[i]=ids[i];b.pos[i]=pos+i;b.n_seq_id[i]=1;b.seq_id[i][0]=0;b.logits[i]=want_logits && (all || i+1==b.n_tokens);}
#ifndef REAL_SD_ORACLE
        hsc::decode_begin(c,target?"target":"draft",std::string(phase)=="PREFILL",b.n_tokens);
#endif
        const int rc=llama_decode(c,b);llama_batch_free(b);need(rc==0,"Direct model decode");llama_synchronize(c);++calls;
#ifndef REAL_SD_ORACLE
        hsc::decode_end();
#endif
        std::vector<std::vector<float>> v(ids.size());const int nv=llama_vocab_n_tokens(llama_model_get_vocab(model));
        if(want_logits && own_logits && all){for(size_t i=0;i<ids.size();++i){auto* p=llama_get_logits_ith(c,int(i));need(p,"Requested direct row");v[i].assign(p,p+nv);}}
        else if(want_logits && own_logits) {auto* p=llama_get_logits_ith(c,-1);need(p,"Requested direct last row");v.back().assign(p,p+nv);}
        return v;
    }
    void trim(int keep){need(llama_memory_seq_rm(llama_get_memory(c),0,keep,-1),"Canonical suffix trim");need(llama_memory_seq_pos_min(llama_get_memory(c),0)==0 && llama_memory_seq_pos_max(llama_get_memory(c),0)==keep-1,"Dense retained prefix after trim");}
    json execution() const {
#ifndef REAL_SD_ORACLE
        if(target)return plan.executions;
#endif
        return native_calls;
    }
};

// Independent R selection derives keep from its own complete decision sequence,
// without reading candidate accepted/keep/row fields or calling select().
static real_sd::Commit reference_commit(const std::vector<int>& proposals,const std::vector<int>& decisions,
                                       int prompt,int generated,int cap,const llama_vocab* vocab){
    real_sd::Commit c;
    for(size_t row=0;row<decisions.size();++row){
        const int token=decisions[row];const bool matching=row<proposals.size() && token==proposals[row];
        c.emitted.push_back(token);if(matching)++c.accepted;
        c.row=int(row);c.pending=token;c.done=llama_vocab_is_eog(vocab,token) || generated+int(c.emitted.size())==cap;
        if(!matching || c.done){
            c.rejected=row<proposals.size() && !matching;
            c.kind=proposals.empty()?"tail":matching?"accepted":c.rejected?"correction":"bonus";
            break;
        }
    }
    c.keep=prompt+generated+int(c.emitted.size())-1;return c;
}
struct Cycle {
    int base,seed,k_eff,target_call;std::vector<int> proposals,decisions;
    real_sd::Commit commit;
    json as_json()const{return {{"base",base},{"seed",seed},{"k_eff",k_eff},{"proposals",proposals},{"decisions",decisions},
        {"accepted",commit.accepted},{"rejected",commit.rejected},{"kind",commit.kind},{"keep",commit.keep},
        {"pending",commit.pending},{"done",commit.done},{"frontier_row",commit.row},{"emitted",commit.emitted},{"target_call",target_call}};}
};

static json request(const json& command,Context& first,Context* second,Context* draft_pool,llama_model* tm,llama_model* dm,
                    const json& config,const fs::path& dir){
    const auto scheduled=command.at("request");const auto arm=scheduled.at("arm").get<std::string>();
    const bool reference_trace=arm=="R_TRACE",sd=arm.rfind("SD_",0)==0 || reference_trace;
    const auto draft_policy=config.value("draft_work_policy",std::string("deferred_last_catchup_logits_v1"));
    need(draft_policy=="deferred_last_kv_only_v1" || draft_policy=="deferred_last_catchup_logits_v1","Explicit known draft work policy");
    const bool catchup_logits=draft_policy=="deferred_last_catchup_logits_v1";
    const bool capture=scheduled.at("stage")=="qualification" && (scheduled.at("role")=="full_trace" || scheduled.at("role")=="reference_greedy" || reference_trace);
    const auto prompt=command.at("prompt_ids").get<std::vector<int>>();const int P=int(prompt.size()),cap=128;
    need(P==scheduled.at("prompt_tokens") && P>0 && P+128+3+1<=1024,"Frozen prompt/capacity contract");
    const auto* vocab=llama_model_get_vocab(tm);const int nv=llama_vocab_n_tokens(vocab);
    for(int token:prompt)need(token>=0 && token<nv,"Prompt token bounds");
    need(!sd || draft_pool || reference_trace,"Live draft context required");
    json input_trace;if(reference_trace)input_trace=load(command.at("trace_receipt").get<std::string>());
    json checkpoints=json::array(),expected_prefixes=json::object();
    if(command.contains("reference_receipt")){
        const auto ref=load(command.at("reference_receipt").get<std::string>());
        for(const auto& p:ref.at("checkpoints"))expected_prefixes[std::to_string(p.at("active_tokens").get<int>())]=p.at("target").at("endpoint_sha256");
    }
    std::vector<Cycle> cycles;std::vector<int> ids;std::vector<float> frontier;
    int base=P,proposed=0,accepted=0,rejections=0,bonuses=0,tails=0;bool draft_initialized=false;
    int draft_deferred=0,draft_catchup=0,draft_skipped=0;
    std::array<int,4> widths{};std::array<int64_t,6> phase_rows{},phase_calls{};
    std::array<uint64_t,6> phase_native4_dispatches{},phase_native4_columns{};
    std::array<std::array<uint64_t,8>,6> phase_prefill_p4{};
    Timer timer;int64_t first_ready=0;
    auto eog=[&](int token){return llama_vocab_is_eog(vocab,token);};
    const auto start=ns();auto acquire=ns();
    Context& target=(arm=="TO_C" || arm=="SD_C")?*second:first;
    Context* draft=nullptr;timer.part[CONTEXT]+=ns()-acquire;
    auto checkpoint=[&](const char* kind,int cycle){
        if(!capture)return;
        auto ts=canonical_state(target.c,tm,ids.back(),base,config.at("target_sha256"),"target");
        json cp={{"kind",kind},{"cycle",cycle},{"active_tokens",base},{"target",ts.proof},{"frontier_sha256",digest_bytes(frontier.data(),frontier.size()*4)}};
        if(draft_initialized){auto ds=canonical_state(draft->c,dm,ids.back(),base,config.at("draft_sha256"),"draft");cp["draft"]=ds.proof;}
        else cp["draft"]=inactive_draft();
        const auto key=std::to_string(base);
        if(expected_prefixes.contains(key) && expected_prefixes.at(key)!=ts.proof.at("endpoint_sha256")){
            write_bytes(dir/"first-failure-target.bin",ts.native.data(),ts.native.size());
            write_json(dir/"FIRST_FAILURE.json",{{"checkpoint",cp},{"expected_endpoint_sha256",expected_prefixes.at(key)}});
            throw std::runtime_error("Canonical checkpoint differs from independent R-TO");
        }
        checkpoints.push_back(cp);
    };
    auto forward=[&](Context& ctx,const std::vector<int>& tokens,int pos,bool all,const char* name,int time_phase,int work_phase,bool want_logits=true,bool own_logits=true){
        const int before=ctx.calls;
#ifndef REAL_SD_ORACLE
        const auto before_n4=hs_work_native4_dispatches(),before_n4_columns=hs_work_native4_columns();
        std::array<uint64_t,8> before_p4{},after_p4{};hs_prefill_pack4_audit(before_p4.data());
#endif
        auto rows=timer.run(time_phase,[&](){return ctx.decode(tokens,pos,all,name,want_logits,own_logits);});
#ifndef REAL_SD_ORACLE
        phase_native4_dispatches[work_phase]+=hs_work_native4_dispatches()-before_n4;
        phase_native4_columns[work_phase]+=hs_work_native4_columns()-before_n4_columns;
        hs_prefill_pack4_audit(after_p4.data());
        for(size_t i=0;i<8;++i){need(after_p4[i]>=before_p4[i],"Monotone P4 counters");phase_prefill_p4[work_phase][i]+=after_p4[i]-before_p4[i];}
#endif
        phase_rows[work_phase]+=tokens.size();phase_calls[work_phase]+=ctx.calls-before;return rows;
    };
#ifndef REAL_SD_ORACLE
    hsc::begin("counts",P);hs_work_reset();
#endif
    timer.action(CONTEXT,[&](){target.reset(capture,dir);});
    auto initial=forward(target,prompt,0,false,"PREFILL",PREFILL,0);frontier=std::move(initial.back());
    timer.action(DECISION,[&](){ids.push_back(greedy(frontier));if(!eog(ids.back()))first_ready=ns();});
    bool done=eog(ids.back()) || int(ids.size())==cap;checkpoint("initial",-1);
    if(sd && !reference_trace && !done){
        timer.action(CONTEXT,[&](){draft=draft_pool;draft->reset(capture,dir);draft_initialized=true;});
        forward(*draft,prompt,0,false,"PREFILL",D_PREFILL,3,false); // KV only; seed produces the first proposal logits.
    }
    while(!done){
        if(!sd){
            auto rows=forward(target,{ids.back()},base,false,"ORDINARY",DECODE,1);frontier=std::move(rows.back());
            timer.action(DECISION,[&](){++base;ids.push_back(greedy(frontier));done=eog(ids.back()) || int(ids.size())==cap;});
            checkpoint("ordinary",int(ids.size())-1);continue;
        }
        const int seed=ids.back(),k_eff=real_sd::proposal_limit(int(ids.size()),cap),call=target.logical_calls;
        std::vector<int> proposals;real_sd::DeferredDraftToken deferred;
        if(reference_trace){
            need(cycles.size()<input_trace.at("sd_trace").size(),"R-trace candidate inputs exhausted");
            const auto& row=input_trace.at("sd_trace").at(cycles.size());
            need(row.at("base")==base && row.at("seed")==seed && row.at("k_eff")==k_eff,"R-trace own seed/base/remaining");
            proposals=row.at("proposals").get<std::vector<int>>();need(proposals.size()<=size_t(k_eff),"R-trace proposal limit");
        }else{
            timer.action(DECISION,[&](){draft->trim(base);});
            auto rows=forward(*draft,{seed},base,false,"DRAFT_SYNC",D_SYNC,4,k_eff>0);
            auto draft_frontier=std::move(rows.back());
            for(int j=0;j<k_eff;++j){
                int proposal=timer.run(DECISION,[&](){return greedy(draft_frontier);});proposals.push_back(proposal);
                if(real_sd::draft_needs_next_logits(j,k_eff,eog(proposal))){
                    auto next=forward(*draft,{proposal},base+1+j,false,"PROPOSE",D_PROPOSE,5);draft_frontier=std::move(next.back());
                }else{
                    deferred.defer(proposal,base+1+j);++draft_deferred;
                    break;
                }
            }
        }
        need(proposals.size()<=size_t(k_eff) && (proposals.size()==size_t(k_eff) || (!proposals.empty() && eog(proposals.back()))),"Deterministic shortened EOG proposal list");
        std::vector<int> verify={seed};verify.insert(verify.end(),proposals.begin(),proposals.end());
        std::vector<std::vector<float>> rows;
        if(reference_trace){
            for(size_t j=0;j<verify.size();++j){auto one=forward(target,{verify[j]},base+int(j),false,"VERIFY",VERIFY,2);rows.push_back(std::move(one.back()));}
        }else rows=forward(target,verify,base,true,"VERIFY",VERIFY,2);
        std::vector<int> decisions;real_sd::Commit commit;
        timer.action(DECISION,[&](){
            for(const auto& row:rows)decisions.push_back(greedy(row));
            commit=reference_trace?reference_commit(proposals,decisions,P,int(ids.size()),cap,vocab):real_sd::select(proposals,decisions,base,int(ids.size()),cap,eog);
        });
        // Catch up exactly the retained deferred token, after the target decides.
        // Default catchup keeps the q1 output graph but skips the owned output copy.
        // The explicit KV-only option removes the output graph. Both are
        // included in draft_sync_s/rows/calls before the canonical checkpoint.
        if(draft_initialized && deferred.exists()){
            if(deferred.needs_kv(commit.keep)){
                need(commit.kind=="bonus","Only all-accepted bonus retains draft tail");
                forward(*draft,{deferred.token},deferred.position,false,"DRAFT_CATCHUP",D_SYNC,4,catchup_logits,false);++draft_catchup;
            }else ++draft_skipped;
        }
        timer.action(DECISION,[&](){
            ids.insert(ids.end(),commit.emitted.begin(),commit.emitted.end());
            target.trim(commit.keep);if(draft_initialized)draft->trim(commit.keep);
            need(commit.keep==P+int(ids.size())-1 && commit.pending==ids.back(),"Canonical pending after commit");
            frontier=std::move(rows.at(commit.row));
            cycles.push_back({base,seed,k_eff,call,proposals,decisions,commit});
            base=commit.keep;done=commit.done;proposed+=proposals.size();accepted+=commit.accepted;
            rejections+=commit.rejected;bonuses+=commit.kind=="bonus";tails+=commit.kind=="tail";++widths.at(verify.size()-1);
        });
        checkpoint("commit",int(cycles.size())-1);
    }
    timer.action(SYNC,[&](){llama_synchronize(target.c);if(draft_initialized)llama_synchronize(draft->c);});
    const int64_t end=ns();
#ifndef REAL_SD_ORACLE
    auto counters=hs_work_finish();hsc::w.active=false;
#endif
    // All hashing, state export, logits payloads and JSON serialization below
    // are outside a clean service interval; heavy qualification is labelled.
    json r=scheduled;r["scheduled_request_id"]=scheduled.at("request_id");r["request_id"]=command.at("actual_request_id");
    r["source_freeze_sha256"]=command.at("source_freeze_sha256");r["attempt"]=command.value("attempt",0);r["included"]=true;r["exclusion_reason"]=nullptr;
    r["service_s"]=(end-start)*1e-9;r["ttft_s"]=first_ready?json((first_ready-start)*1e-9):json(nullptr);
    int64_t covered=0;for(size_t i=0;i<phase_names.size();++i){r[phase_names[i]]=timer.part[i]*1e-9;covered+=timer.part[i];}
    need(end-start>=covered,"Disjoint phase clock closure");r["other_host_s"]=(end-start-covered)*1e-9;
    r["clock"]={{"kind","CLOCK_MONOTONIC"},{"start_ns",start},{"first_non_EOG_ready_ns",first_ready?json(first_ready):json(nullptr)},{"final_sync_end_ns",end},{"end_ns",end},{"heavy_observer_inside_service",capture}};
    r["decision_ids"]=ids;auto display=ids;if(eog(ids.back()))display.pop_back();r["display_ids"]=display;
    r["stop_reason"]=eog(ids.back())?"EOG":"CAP";r["eog_id"]=eog(ids.back())?json(ids.back()):json(nullptr);
    r["pending_id"]=ids.back();r["pending_position"]=base;r["active_target_tokens"]=base;
    r["cycles"]=cycles.size();r["proposed"]=proposed;r["accepted"]=accepted;r["rejections"]=rejections;r["bonus_events"]=bonuses;r["tail_steps"]=tails;
    r["verify_width_hist"]={{"1",widths[0]},{"2",widths[1]},{"3",widths[2]},{"4",widths[3]}};
    r["target_rows"]=target.rows;r["draft_rows"]=draft_initialized?draft->rows:0;
    int verifier_rows=0;for(int q=1;q<=4;++q)verifier_rows+=q*widths[q-1];
    need(target.rows==P+(sd?verifier_rows:int(ids.size())-1),"Target actual row closure");
    need(draft_deferred==draft_catchup+draft_skipped,"Deferred draft disposition closure");
    need(!draft_initialized || draft->rows==P+int(cycles.size())+proposed-draft_skipped,"Draft actual row closure");
    r["draft_work_policy"]=draft_policy;
    r["draft_deferred_tokens"]=draft_deferred;r["draft_catchup_rows"]=draft_catchup;r["draft_skipped_rows"]=draft_skipped;
    r["draft_kv_only_calls"]=draft_initialized?1+(catchup_logits?0:draft_catchup)+tails:0;
    r["draft_discarded_catchup_logits"]=catchup_logits?draft_catchup:0;
    need(target.rows<=scheduled.at("reserved_target_rows") && r["draft_rows"].get<int64_t>()<=scheduled.at("reserved_draft_rows"),"Per-request row reservation");
    auto target_state=canonical_state(target.c,tm,ids.back(),base,config.at("target_sha256"),"target");
    write_bytes(dir/"target-terminal.bin",target_state.native.data(),target_state.native.size());
    write_bytes(dir/"target-frontier.f32",frontier.data(),frontier.size()*4);
    r["target_endpoint"]=target_state.proof;r["target_endpoint_sha256"]=target_state.proof.at("endpoint_sha256");
    r["target_frontier_sha256"]=digest_bytes(frontier.data(),frontier.size()*4);
    if(draft_initialized){auto state=canonical_state(draft->c,dm,ids.back(),base,config.at("draft_sha256"),"draft");write_bytes(dir/"draft-terminal.bin",state.native.data(),state.native.size());r["draft_endpoint"]=state.proof;}
    else r["draft_endpoint"]=inactive_draft();
    r["draft_endpoint_sha256"]=r["draft_endpoint"].at("endpoint_sha256");r["draft_initialized"]=draft_initialized;
    r["sd_trace"]=json::array();for(const auto& c:cycles)r["sd_trace"].push_back(c.as_json());
    r["sd_trace_sha256"]=sd?json(digest_text(r["sd_trace"].dump())):json(nullptr);
    r["checkpoints"]=checkpoints;r["target_vectors"]=target.vectors;r["draft_vectors"]=draft_initialized?draft->vectors:json::array();
    r["target_native_calls"]=target.calls;r["draft_native_calls"]=draft_initialized?draft->calls:0;
    r["target_executions"]=target.execution();r["draft_executions"]=draft_initialized?draft->execution():json::array();
    r["phase_rows"]={{"target_prefill",phase_rows[0]},{"target_decode",phase_rows[1]},{"target_verify",phase_rows[2]},
        {"draft_prefill",phase_rows[3]},{"draft_sync",phase_rows[4]},{"draft_propose",phase_rows[5]}};
    r["phase_native_calls"]={{"target_prefill",phase_calls[0]},{"target_decode",phase_calls[1]},{"target_verify",phase_calls[2]},
        {"draft_prefill",phase_calls[3]},{"draft_sync",phase_calls[4]},{"draft_propose",phase_calls[5]}};
    r["phase_native4_dispatches"]=json::object();r["phase_native4_columns"]=json::object();
    const std::array<const char*,6> work_phase_names={"target_prefill","target_decode","target_verify","draft_prefill","draft_sync","draft_propose"};
    for(size_t i=0;i<work_phase_names.size();++i){r["phase_native4_dispatches"][work_phase_names[i]]=phase_native4_dispatches[i];r["phase_native4_columns"][work_phase_names[i]]=phase_native4_columns[i];}
    r["prefill_pack4_enabled"]=prefill_p4_enabled();
    r["prefill_pack4_profile"]="prefill_native4_channel_groups_v1";
    r["prefill_pack4_fields"]=json::array({"calls","columns","channel_groups","launches","q8","q16","q32","other_widths"});
    r["phase_prefill_pack4"]=json::object();std::array<uint64_t,8> total_p4{};
    for(size_t p=0;p<6;++p){r["phase_prefill_pack4"][work_phase_names[p]]=phase_prefill_p4[p];for(size_t i=0;i<8;++i)total_p4[i]+=phase_prefill_p4[p][i];}
    r["prefill_pack4_total"]=total_p4;
    r["target_context_identity"]=std::string("fixed-arm-")+std::to_string(target.arm);
    r["target_C_dispatch_profile"]=target_C_profile();
    r["draft_context_identity"]=draft_initialized?json("fixed-draft-B-D4"):json(nullptr);
    r["endpoint_export_after_service"]=true;r["online_state_exports"]=capture?json(nullptr):json(0);
#ifndef REAL_SD_ORACLE
    r["application_work"]={{"quant_calls",counters.quant_calls},{"quant_rows",counters.quant_rows},{"backend_loop_entries",counters.backend_loop_entries},{"scalar_dot_dispatches",counters.scalar_dot_dispatches},{"kernel_launch_calls",counters.kernel_calls},{"sync_calls",counters.sync_calls},{"native4_dispatches",hs_work_native4_dispatches()},{"native4_columns",hs_work_native4_columns()}};
    r["target_physical_width_hist"]=json::object();r["draft_physical_width_hist"]=json::object();
    for(size_t width=0;width<hsc::w.target_physical.size();++width){
        if(hsc::w.target_physical[width])r["target_physical_width_hist"][std::to_string(width)]=hsc::w.target_physical[width];
        if(hsc::w.draft_physical[width])r["draft_physical_width_hist"][std::to_string(width)]=hsc::w.draft_physical[width];
    }
    r["graphs_built"]=hsc::w.graphs_built;r["graphs_reused"]=hsc::w.graphs_reused;
#endif
    write_json(dir/"RECEIPT.json",r);return r;
}

static json structure(llama_model* m){return {{"layers",m->hparams.n_layer()},{"K_elements",m->hparams.n_embd_k_gqa()},{"V_elements",m->hparams.n_embd_v_gqa()},{"vocabulary",llama_vocab_n_tokens(llama_model_get_vocab(m))}};}
static json placement(llama_model* m){json counts=json::object();for(const auto& item:m->tensors_by_name){auto* b=item.second->buffer;need(b,"Actual tensor buffer");const std::string name=ggml_backend_buft_name(ggml_backend_buffer_get_type(b));if(!counts.contains(name))counts[name]={{"tensors",0},{"bytes",0}};counts[name]["tensors"]=counts[name]["tensors"].get<int>()+1;counts[name]["bytes"]=counts[name]["bytes"].get<uint64_t>()+ggml_nbytes(item.second);}return counts;}
static void event(const json& e){std::cout<<"HS_REAL_SD "<<e.dump()<<'\n'<<std::flush;}
static void cpu_fixtures(){
    need(digest_text("abc")=="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad","Existing libcrypto SHA256 known answer");
    for(bool transposed:{false,true}){
        std::vector<uint8_t> raw,expected;
        auto append=[&](auto value){const auto* b=reinterpret_cast<const uint8_t*>(&value);raw.insert(raw.end(),b,b+sizeof(value));};
        append(uint32_t(0xaf143cd8));append(int32_t(0));append(uint32_t(1));append(uint32_t(3));
        for(int t=0;t<3;++t){append(int32_t(t));append(uint32_t(1));append(int32_t(0));}
        append(uint32_t(transposed));append(uint32_t(2));
        for(int l=0;l<2;++l){append(int32_t(1));append(uint64_t(4));for(int t=0;t<3;++t)for(int j=0;j<2;++j)append(uint16_t(10+100*l+10*t+j));}
        for(int l=0;l<2;++l){append(int32_t(1));if(transposed){append(uint32_t(2));append(uint32_t(3));}else append(uint64_t(6));
            for(int x=0;x<(transposed?3:3);++x)for(int y=0;y<3;++y){int t=transposed?y:x,j=transposed?x:y;append(uint16_t(1000+100*l+10*t+j));}}
        auto emit=[&](uint16_t value){expected.push_back(value&255);expected.push_back(value>>8);};
        for(int t=0;t<3;++t)for(int l=0;l<2;++l){for(int j=0;j<2;++j)emit(10+100*l+10*t+j);for(int j=0;j<3;++j)emit(1000+100*l+10*t+j);}
        const auto proof=canonical_kv(raw,3,2,4,6);need(proof.at("active_KV_bytes")==60 && proof.at("active_KV_sha256")==digest_bytes(expected.data(),expected.size()),"All canonical bytes and transposed V mapping");
        raw.push_back(0);bool rejected=false;try{canonical_kv(raw,3,2,4,6);}catch(const std::exception&){rejected=true;}need(rejected,"Unclassified state suffix rejection");
        raw.resize(20);rejected=false;try{canonical_kv(raw,3,2,4,6);}catch(const std::exception&){rejected=true;}need(rejected,"Truncated state rejection");
    }
    std::cout<<"CPU_ONLY_PASS SHA256 known answer; every K/V byte; transposed/nontransposed logical order; truncation/suffix rejection; no GPU initialization\n";
}
int main(int argc,char** argv){
    if(argc==2 && std::string(argv[1])=="--cpu-fixtures"){
        try{cpu_fixtures();return 0;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}
    }
    fs::path out;std::string active;std::unique_ptr<Context> b,c,d;
    llama_model* target=nullptr;llama_model* draft=nullptr;bool initialized=false;auto started=ns();
    try{
        need(argc==3,"native CONFIG OUT, then one admitted request per stdin line");const auto config=load(argv[1]);out=argv[2];
#ifndef REAL_SD_ORACLE
        need(config.value("target_C_dispatch_profile",std::string("a5000_C_q1_grouped_v1"))==target_C_profile(),"Explicit C dispatch profile must match linked backend capability");
#endif
need(config.at("prefill_pack4_enabled").get<bool>()==prefill_p4_enabled(),"Configured P4 process profile");
need(!fs::exists(out),"Fresh native window");fs::create_directories(out);
        need(std::getenv("CUDA_VISIBLE_DEVICES") && config.at("gpu_uuid")==std::getenv("CUDA_VISIBLE_DEVICES"),"Original A0 binding");
        need(std::getenv("GGML_CUDA_DISABLE_GRAPHS") && std::string(std::getenv("GGML_CUDA_DISABLE_GRAPHS"))=="1","Frozen graphs-off policy");
        ggml_time_init();llama_backend_init();initialized=true;ggml_backend_dev_t gpu=nullptr;
        for(size_t i=0;i<ggml_backend_dev_count();++i){auto x=ggml_backend_dev_get(i);if(ggml_backend_dev_type(x)==GGML_BACKEND_DEVICE_TYPE_GPU){need(!gpu,"Only one visible GPU");gpu=x;}}
        need(gpu,"Native GPU required");ggml_backend_dev_t devices[]={gpu,nullptr};auto mp=llama_model_default_params();mp.devices=devices;mp.n_gpu_layers=999;mp.split_mode=LLAMA_SPLIT_MODE_NONE;
        auto stage=ns();target=llama_model_load_from_file(config.at("target_model").get<std::string>().c_str(),mp);need(target,"Target weights");
#ifndef REAL_SD_ORACLE
        draft=llama_model_load_from_file(config.at("draft_model").get<std::string>().c_str(),mp);need(draft,"Draft weights");
        const auto* tv=llama_model_get_vocab(target);const auto* dv=llama_model_get_vocab(draft);need(llama_vocab_n_tokens(tv)==llama_vocab_n_tokens(dv),"Vocabulary extent");
        for(int i=0;i<llama_vocab_n_tokens(tv);++i)need(std::strcmp(llama_vocab_get_text(tv,i),llama_vocab_get_text(dv,i))==0 && llama_vocab_is_eog(tv,i)==llama_vocab_is_eog(dv,i),"Exact target/draft tokenizer/EOG identity");
        phase_lowering="SIMPLE";phase_target_reserve=32;phase_draft_width=4;
#endif
        const double model_load_s=elapsed(stage);stage=ns();
#ifdef REAL_SD_ORACLE
        b=std::make_unique<Context>(target,true,0);
#else
        b=std::make_unique<Context>(target,true,2);c=std::make_unique<Context>(target,true,3);d=std::make_unique<Context>(draft,false,2);
#endif
        json window={{"pid",getpid()},{"model_load_and_tokenizer_check_s",model_load_s},{"context_setup_s",elapsed(stage)},
            {"device",ggml_backend_dev_description(gpu)},{"target_structure",structure(target)},{"target_placement",placement(target)},
            {"draft_structure",draft?structure(draft):json(nullptr)},{"draft_placement",draft?placement(draft):json(nullptr)},
            {"both_weights_resident",draft!=nullptr},{"arm_graph_identity","Separate immutable-arm target contexts; fixed-B draft context"},
            {"request_threads",2},{"target_ubatch",draft?32:1},{"target_output_reserve",draft?32:1},{"draft_ubatch",draft?4:0},{"graphs",false},{"flash",false}};
        window["eog_ids"]=json::array();const auto* vocab=llama_model_get_vocab(target);
        for(int token=0;token<llama_vocab_n_tokens(vocab);++token)if(llama_vocab_is_eog(vocab,token))window["eog_ids"].push_back(token);
        window["prefill_pack4_enabled"]=prefill_p4_enabled();window["prefill_pack4_profile"]="prefill_native4_channel_groups_v1";
        window["target_C_dispatch_profile"]=target_C_profile();window["draft_work_policy"]=config.value("draft_work_policy",std::string("deferred_last_catchup_logits_v1"));write_json(out/"WINDOW_READY.json",window);event({{"event","ready"},{"pid",getpid()}});
        std::string line;
        while(std::getline(std::cin,line)){
            auto command=json::parse(line);if(command.value("command",std::string())=="finish")break;
            const auto& req=command.at("request");active=command.at("actual_request_id");
            need(!active.empty() && active.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")==std::string::npos,"Request identity");
            need(command.at("budget_reserved")==true && command.at("source_freeze_sha256")==config.at("source_freeze_sha256"),"Fresh reserved request/freeze");
            const std::string arm=req.at("arm");
#ifndef REAL_SD_ORACLE
            need(arm=="TO_U" || arm=="TO_C" || arm=="SD_U" || arm=="SD_C","Four candidate arms");
#else
            need(arm=="R_TO" || arm=="R_TRACE","Pristine oracle arm");
#endif
            const auto dir=out/active;fs::create_directories(dir);write_json(dir/"COMMAND.json",command);
            auto r=request(command,*b,c.get(),d.get(),target,draft,config,dir);
            event({{"event","result"},{"request_id",active},{"receipt",(dir/"RECEIPT.json").string()},{"target_rows",r.at("target_rows")},{"draft_rows",r.at("draft_rows")}});active.clear();
        }
        stage=ns();d.reset();c.reset();b.reset();if(draft)llama_model_free(draft);draft=nullptr;llama_model_free(target);target=nullptr;llama_backend_free();initialized=false;
        write_json(out/"WINDOW_COMPLETE.json",{{"normal_teardown_s",elapsed(stage)},{"window_wall_s",elapsed(started)}});event({{"event","complete"}});return 0;
    }catch(const std::exception& e){
        if(!out.empty() && fs::exists(out))write_json(out/"FAILURE.json",{{"error",e.what()},{"active_request",active},{"wall_s",elapsed(started)},
            {"target_rows_completed",b?b->rows:0},{"C_target_rows_completed",c?c->rows:0},{"draft_rows_completed",d?d->rows:0}});
        event({{"event","failure"},{"request_id",active},{"error",e.what()}});std::cerr<<e.what()<<'\n';
        d.reset();c.reset();b.reset();if(draft)llama_model_free(draft);if(target)llama_model_free(target);if(initialized)llama_backend_free();return 2;
    }
}

