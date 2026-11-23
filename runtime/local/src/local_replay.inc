#include <cstdlib>
#ifndef REAL_SD_ORACLE
#include <cuda_profiler_api.h>
extern "C" hs_work_counts hs_work_peek();
extern "C" void hs_work_native4(uint64_t columns);
#endif

static const std::string& local_lowering() {
    static const std::string value=[](){
        const char* text=std::getenv("HS_LOCAL_LOWERING");
        need(text && (std::string(text)=="SIMPLE" || std::string(text)=="LOCAL"),"Explicit immutable LOCAL lowering");
        return std::string(text);
    }();
    return value;
}

static json local_work() {
#ifndef REAL_SD_ORACLE
    const auto w=hs_work_peek();
    std::array<uint64_t,8> p4{};hs_prefill_pack4_audit(p4.data());
    return {{"quant_calls",w.quant_calls},{"quant_rows",w.quant_rows},{"dot_calls",w.scalar_dot_dispatches},
        {"dot_columns",w.scalar_dot_columns},{"kernel_calls",w.kernel_calls},
        {"native4_dispatches",hs_work_native4_dispatches()},{"native4_columns",hs_work_native4_columns()},
        {"graphs_built",hsc::w.graphs_built},{"graphs_reused",hsc::w.graphs_reused},{"P4",p4}};
#else
    return json::object();
#endif
}

static json local_request(const json& command,Context& target,llama_model* model,
                          const json& config,const fs::path& directory) {
    const auto& task=command.at("request");const auto& input=task.at("case_input");
    const auto history=input.at("history_ids").get<std::vector<int>>();
    const int prompt=task.at("prompt_tokens");const int base=int(history.size());
    const bool qualification=task.at("stage")=="qualification";
    const bool diagnostic=task.value("diagnostic",false);
    need(task.at("lowering")==local_lowering() && config.at("local_lowering")==local_lowering(),"Frozen per-process lowering identity");
    need(config.at("local_diagnostic")==diagnostic,"Frozen diagnostic scope");
    need(!prefill_p4_enabled(),"LOCAL comparison keeps P4 disabled");
    need((base==137 || base==253) && prompt==137,"Frozen two histories");
    need(digest_text(input.at("history_ids").dump())==input.at("history_sha256"),"Frozen history IDs");
    need(history.size()==size_t(input.at("transaction").at("base").get<int>()),"Incoming physical/logical base");
    for(int token:history)need(token>=0 && token<151936,"Frozen history vocabulary bounds");
#ifndef REAL_SD_ORACLE
    need(phase_lowering==local_lowering(),"No live lowering change");
#endif
    const auto request_begin=ns();target.reset(false,directory);
#ifndef REAL_SD_ORACLE
    hs_work_reset();hsc::w={};hsc::w.active=true;
#endif
    json states=json::array(),vectors=json::array(),calls=json::array();
    auto forward=[&](const std::vector<int>& tokens,int position,bool all,const char* phase) {
#ifdef REAL_SD_ORACLE
        std::vector<std::vector<float>> result;
        for(size_t i=0;i<tokens.size();++i){auto row=target.decode({tokens[i]},position+int(i),false,phase);result.push_back(std::move(row.at(0)));}
        return result;
#else
        return target.decode(tokens,position,all,phase);
#endif
    };
    auto state=[&](const std::string& label,int active,int pending,const char* semantics) {
        auto snapshot=canonical_state(target.c,model,pending,active,config.at("target_sha256"),"target");
        const std::string file="states/"+label+".bin";write_bytes(directory/file,snapshot.native.data(),snapshot.native.size());
        states.push_back({{"stage",label},{"path",file},{"proof",snapshot.proof},{"pending_semantics",semantics}});
    };
    const auto prefix_begin=ns();auto prefill=forward(history,0,false,"PREFILL");const auto prefix_end=ns();
    need(!prefill.back().empty() && prefill.back().size()==151936,"Complete prefix frontier");
    write_bytes(directory/"prefix-frontier.f32",prefill.back().data(),prefill.back().size()*4);
    int pending=greedy(prefill.back());
    state("prefix",base,pending,"canonical pending before the frozen transaction");
    need(pending==input.at("transaction").at("seed"),"Reference-compatible incoming greedy frontier");
    target.capture=qualification;
    int position=base,generated=base-prompt+1;
    std::vector<std::vector<std::vector<float>>> owned;
    for(int step=0;step<2;++step) {
        const auto frozen=input.at(step==0?"transaction":"continuation");
        const auto proposals=frozen.at("proposals").get<std::vector<int>>();
        need(proposals.size()==3 && real_sd::proposal_limit(generated,128)==3,"Fixed legal k3 transaction");
        for(int token:proposals)need(token>=0 && token<151936,"Frozen proposal vocabulary bounds");
        if(position!=frozen.at("base") || pending!=frozen.at("seed")) {
            write_json(directory/"FIRST_FAILURE_STAGE.json",{{"stage",step},{"actual_position",position},{"actual_pending",pending},{"expected",frozen},{"completed_calls",calls}});
            need(false,"Own commit cannot continue the frozen legal transaction");
        }
        std::vector<int> tokens{pending};tokens.insert(tokens.end(),proposals.begin(),proposals.end());
        const auto before=local_work();
#ifndef REAL_SD_ORACLE
        if(diagnostic && step==0)need(cudaProfilerStart()==cudaSuccess,"CUDA diagnostic capture start");
#endif
        const char* phase=step==0?"LOCAL_PRIMARY":"LOCAL_CONTINUATION";
        std::cerr<<phase<<"_BEGIN position="<<position<<" lowering="<<local_lowering()<<'\n';
        const auto transaction_begin=ns();const auto decode_begin=ns();
        auto output=forward(tokens,position,true,phase);llama_synchronize(target.c);
        const auto decode_end=ns();
        need(output.size()==4 && std::all_of(output.begin(),output.end(),[](const auto& row){return row.size()==151936;}),"Four complete owned vocabulary rows");
        std::vector<int> decisions;for(const auto& row:output)decisions.push_back(greedy(row));
        if(qualification)state(std::string(step==0?"primary":"continuation")+"_uncommitted",position+4,decisions.back(),"counterfactual full proposal branch; not committed pending");
        real_sd::Commit commit;
#ifdef REAL_SD_ORACLE
        commit=reference_commit(proposals,decisions,prompt,generated,128,llama_model_get_vocab(model));
#else
        commit=real_sd::select(proposals,decisions,position,generated,128,[&](int token){return llama_vocab_is_eog(llama_model_get_vocab(model),token);});
#endif
        const auto commit_begin=ns();target.trim(commit.keep);llama_synchronize(target.c);const auto transaction_end=ns();
#ifndef REAL_SD_ORACLE
        if(diagnostic && step==0)need(cudaProfilerStop()==cudaSuccess,"CUDA diagnostic capture stop");
#endif
        std::cerr<<phase<<"_END position="<<position<<" lowering="<<local_lowering()<<'\n';
        const auto after=local_work();json work=json::object();
        for(const auto& item:after.items()) {
            if(item.key()=="P4"){
                need(std::all_of(item.value().begin(),item.value().end(),[](const auto& value){return value==0;}),"No P4 dispatch in LOCAL experiment");work["P4"]=item.value();
            }else{need(item.value().get<uint64_t>()>=before.at(item.key()).get<uint64_t>(),"Monotone call counters");work[item.key()]=item.value().get<uint64_t>()-before.at(item.key()).get<uint64_t>();}
        }
        Cycle cycle{position,tokens[0],3,0,proposals,decisions,commit};
        calls.push_back({{"phase",phase},{"trace",cycle.as_json()},{"decode_s",(decode_end-decode_begin)*1e-9},
            {"verify_to_commit_s",(transaction_end-transaction_begin)*1e-9},{"trim_sync_s",(transaction_end-commit_begin)*1e-9},
            {"clock",{{"start_ns",transaction_begin},{"decode_start_ns",decode_begin},{"decode_end_ns",decode_end},{"end_ns",transaction_end}}},
            {"heavy_observer_inside_call",qualification},{"diagnostic",diagnostic && step==0},{"work",work},
            {"owned_frontier_row",commit.row},{"owned_frontier_sha256",digest_bytes(output.at(commit.row).data(),151936*4)}});
        pending=commit.pending;position=commit.keep;generated+=int(commit.emitted.size());
        if(qualification || step==1)state(std::string(step==0?"primary":"continuation")+"_commit",position,pending,"canonical committed pending");
        owned.push_back(std::move(output));
    }
    llama_synchronize(target.c);const auto request_end=ns();
    // These complete payload writes are outside both clean call intervals.
    for(size_t step=0;step<owned.size();++step)for(size_t row=0;row<owned[step].size();++row){
        const auto file="owned/step"+std::to_string(step)+"-row"+std::to_string(row)+".f32";
        write_bytes(directory/file,owned[step][row].data(),151936*4);
        vectors.push_back({{"step",step},{"row",row},{"path",file},{"bytes",151936*4},{"sha256",digest_bytes(owned[step][row].data(),151936*4)}});
    }
    json result=task;result["request_id"]=command.at("actual_request_id");result["scheduled_request_id"]=task.at("request_id");
    result["attempt"]=command.at("attempt");result["source_freeze_sha256"]=config.at("source_freeze_sha256");
    result["measurement_kind"]="frozen-proposal target transaction replay, not complete SD service";
    result["target_rows"]=target.rows;result["draft_rows"]=0;result["pending_id"]=pending;result["pending_position"]=position;
    result["prefix_s"]=(prefix_end-prefix_begin)*1e-9;result["calls"]=calls;result["checkpoints"]=states;
    result["owned_vectors"]=vectors;result["target_vectors"]=target.vectors;result["target_executions"]=target.execution();
    result["target_native_calls"]=target.native_calls;result["local_lowering"]=local_lowering();result["prefill_pack4_enabled"]=prefill_p4_enabled();
    result["clock"]={{"kind","CLOCK_MONOTONIC"},{"start_ns",request_begin},{"end_ns",request_end},{"final_sync_end_ns",request_end},{"heavy_observer_inside_service",true}};
    result["service_s"]=(request_end-request_begin)*1e-9;result["service_s_is_application_estimate"]=false;
    result["request_clock_excludes_final_payload_writes"]=true;
    write_json(directory/"RECEIPT.json",result);return result;
}
