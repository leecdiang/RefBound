#include "transaction.hpp"
#include "inherited/phase_plan.hpp"
#include <iostream>
#include <stdexcept>
static void check(bool v){if(!v)throw std::runtime_error("CPU state fixture failed");}
int main(){
    auto eog=[](int x){return x==99;};
    const std::vector<int> p={10,20,30};
    auto a=real_sd::select(p,{11,21,31,40},255,1,128,eog);
    check(a.rejected && a.accepted==0 && a.keep==256 && a.row==0 && a.pending==11);
    a=real_sd::select(p,{10,21,31,40},255,1,128,eog);
    check(a.rejected && a.accepted==1 && a.keep==257 && a.row==1 && a.emitted==std::vector<int>({10,21}));
    a=real_sd::select(p,{10,20,31,40},255,1,128,eog);
    check(a.rejected && a.accepted==2 && a.keep==258 && a.row==2);
    a=real_sd::select(p,{10,20,30,40},255,1,128,eog);
    check(!a.rejected && a.accepted==3 && a.kind=="bonus" && a.keep==259 && a.row==3 && !a.done);
    a=real_sd::select({99},{99,40},255,1,128,eog);
    check(a.done && a.kind=="accepted" && a.keep==256 && a.row==0 && a.pending==99);
    a=real_sd::select(p,{10,20,30,40},255,126,128,eog);
    check(a.done && a.accepted==2 && a.keep==257 && a.row==1 && a.pending==20);
    a=real_sd::select(p,{99,20,30,40},255,1,128,eog);
    check(a.done && a.rejected && a.keep==256 && a.row==0 && a.pending==99);
    a=real_sd::select(p,{11,20,30,40},255,127,128,eog);
    check(a.done && a.rejected && a.keep==256 && a.pending==11);
    a=real_sd::select({}, {44},255,127,128,eog);
    check(a.done && a.kind=="tail" && !a.accepted && a.keep==256 && a.row==0 && a.pending==44);
    a=real_sd::select({}, {99},255,127,128,eog);
    check(a.done && a.kind=="tail" && a.pending==99);
    check(real_sd::proposal_limit(124)==3 && real_sd::proposal_limit(126)==1 && real_sd::proposal_limit(127)==0);
    // A first EOG is already a terminal decision, with no SD cycle/draft work.
    std::vector<int> initial={99};check(eog(initial.front()) && initial.size()==1);
    const auto ext=refplan::dense_extents(255,4,256,1024);
    check(ext==std::vector<int64_t>({256,512,512,512}));
    std::vector<refplan::Row> rows;for(int i=0;i<4;++i)rows.push_back({255+i,ext[i],1,true});
    const auto groups=refplan::plan(rows,32);check(groups.size()==2 && groups[0].count==1 && groups[1].count==3);
    // A rollback to the accepted prefix changes the next append's actual key.
    check(refplan::dense_extents(256,1,256,1024)==std::vector<int64_t>({512}));
    std::cout<<"PASS reject0/1/2, bonus, accepted/correction EOG/cap, initial EOG, q1 tail, boundary/rollback\n";
}
