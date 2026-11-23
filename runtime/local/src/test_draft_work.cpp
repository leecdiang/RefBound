#include "draft_work.hpp"
#include "transaction.hpp"
#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

static void need(bool ok, const char * message) {
    if (!ok) throw std::runtime_error(message);
}

// A stateful producer whose complete row depends on every retained input. This
// checks lifetime/rollback/continuation semantics; it is not a GPU math oracle.
struct Producer {
    std::vector<int> tokens;
    std::vector<std::array<uint64_t,4>> kv;
    int forwards=0, heads=0;
    std::array<uint64_t,4> append(int token, int position, bool output) {
        need(position==int(tokens.size()),"append requires dense state");
        uint64_t h=kv.empty()?0xcbf29ce484222325ULL:kv.back()[0];
        h=(h^uint64_t(token+1))*0x100000001b3ULL;
        const std::array<uint64_t,4> row={h,h^uint64_t(position),h*17+uint64_t(token),h*31+7};
        tokens.push_back(token);kv.push_back(row);++forwards;
        if(output){++heads;return row;}
        return {};
    }
    void trim(int keep) {
        need(keep>=0 && keep<=int(tokens.size()),"cannot synthesize missing retained KV");
        tokens.resize(keep);kv.resize(keep);
    }
};

static void words(int length,std::vector<int>& v,std::vector<std::vector<int>>& out) {
    if(int(v.size())==length){out.push_back(v);return;}
    for(int t:{1,2,9}){v.push_back(t);words(length,v,out);v.pop_back();}
}

int main() {
    try {
        auto eog=[](int t){return t==9;};
        uint64_t cases=0,skip=0,catchup=0;std::map<std::string,uint64_t> kinds;
        for(bool catchup_outputs:{false,true})for(int generated=1;generated<128;++generated){
            const int limit=real_sd::proposal_limit(generated,128),base=7+generated-1;
            for(int k=0;k<=limit;++k){
                std::vector<std::vector<int>> proposals_all,decisions_all;std::vector<int> temp;
                words(k,temp,proposals_all);words(k+1,temp,decisions_all);
                for(const auto& proposals:proposals_all){
                    if(k==0 && limit!=0)continue;
                    if(k>0 && std::find(proposals.begin(),proposals.end()-1,9)!=proposals.end()-1)continue;
                    if(k<limit && (k==0 || !eog(proposals.back())))continue;
                    for(const auto& decisions:decisions_all){
                        Producer eager,lazy;
                        for(int i=0;i<base;++i){const int token=(i*13)%7;eager.append(token,i,false);lazy.append(token,i,false);}
                        auto old_frontier=eager.append(3,base,true);
                        auto new_frontier=lazy.append(3,base,limit>0);
                        real_sd::DeferredDraftToken deferred;
                        for(int j=0;j<k;++j){
                            need(old_frontier==new_frontier,"Every consumed complete draft row is identical");
                            old_frontier=eager.append(proposals[j],base+1+j,true);
                            if(real_sd::draft_needs_next_logits(j,limit,eog(proposals[j])))
                                new_frontier=lazy.append(proposals[j],base+1+j,true);
                            else deferred.defer(proposals[j],base+1+j);
                        }
                        auto commit=real_sd::select(proposals,decisions,base,generated,128,eog);
                        if(deferred.exists()){
                            if(deferred.needs_kv(commit.keep)){
                                need(commit.kind=="bonus","Only bonus retains final proposal");
                                lazy.append(deferred.token,deferred.position,catchup_outputs);++catchup;
                            }else ++skip;
                        }
                        eager.trim(commit.keep);lazy.trim(commit.keep);
                        need(eager.tokens==lazy.tokens && eager.kv==lazy.kv,"Complete retained draft state agrees");
                        need(eager.forwards-lazy.forwards==(deferred.exists()&&!deferred.needs_kv(commit.keep)?1:0),"Exact avoided row count");
                        need(eager.heads-lazy.heads==1-int(catchup_outputs&&deferred.exists()&&deferred.needs_kv(commit.keep)),"Exactly the configured unused final/seed output is suppressed");
                        // An actual next consumer sees the same complete row after
                        // rollback, including when final proposal KV was caught up.
                        need(eager.append(commit.pending,commit.keep,true)==lazy.append(commit.pending,commit.keep,true),"Continuation row after canonical pending agrees");
                        ++cases;++kinds[commit.kind];
                    }
                }
            }
        }
        need(kinds["tail"] && kinds["bonus"] && kinds["correction"] && kinds["accepted"],"All terminal and rollback classes covered");
        real_sd::DeferredDraftToken d;d.defer(4,17);bool rejected=false;
        try{d.needs_kv(19);}catch(const std::runtime_error&){rejected=true;}
        need(rejected,"Cannot keep beyond deferred prefix");
        std::cout<<"CPU_DRAFT_STATE_PASS cases="<<cases<<" skipped="<<skip<<" catchup="<<catchup;
        for(const auto& x:kinds)std::cout<<" "<<x.first<<"="<<x.second;
        std::cout<<"; both explicit output policies, all generated budgets, rejection positions, EOG/accepted terminals, q1 tails, full retained mock KV and next consumer row; GPU math not tested\n";
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
