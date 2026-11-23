#pragma once
#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#include "llama.h"
#include <nlohmann/json.hpp>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <functional>
#include <numeric>
#include <stdexcept>
#include <vector>
using json=nlohmann::json;
namespace fs=std::filesystem;
using Clock=std::chrono::steady_clock;
inline void need(bool ok,const std::string & why){if(!ok)throw std::runtime_error(why);}
// Literal diagnostics allocate only on failure; keep dynamic std::string callers.
inline void need(bool ok,const char * why){if(!ok)throw std::runtime_error(why);}
inline double elapsed(Clock::time_point a,Clock::time_point b=Clock::now()){return std::chrono::duration<double>(b-a).count();}
inline json read_json(const fs::path & path){std::ifstream f(path);json j;f>>j;need(bool(f),"read "+path.string());return j;}
inline void write_json(const fs::path & path,const json & j){std::ofstream f(path);f<<j.dump(2)<<'\n';need(bool(f),"write "+path.string());}
struct Sha {
    BCRYPT_ALG_HANDLE a=nullptr;BCRYPT_HASH_HANDLE h=nullptr;
    Sha(){need(BCryptOpenAlgorithmProvider(&a,BCRYPT_SHA256_ALGORITHM,nullptr,0)==0,"SHA provider");need(BCryptCreateHash(a,&h,nullptr,0,nullptr,0,0)==0,"SHA create");}
    ~Sha(){if(h)BCryptDestroyHash(h);if(a)BCryptCloseAlgorithmProvider(a,0);}
    void update(const void * p,size_t n){auto b=(const uint8_t*)p;while(n){auto k=ULONG(std::min<size_t>(n,1024*1024));need(BCryptHashData(h,(PUCHAR)b,k,0)==0,"SHA update");b+=k;n-=k;}}
    std::string finish(){uint8_t out[32];need(BCryptFinishHash(h,out,32,0)==0,"SHA finish");std::string s;for(auto b:out){s+="0123456789abcdef"[b>>4];s+="0123456789abcdef"[b&15];}return s;}
};
inline std::string digest(const void * b,size_t n){Sha s;s.update(b,n);return s.finish();}
inline std::string digest(const std::string & s){return digest(s.data(),s.size());}
inline fs::path store(const fs::path & objects,const void * data,size_t size,const std::string & suffix){
    auto p=objects/(digest(data,size)+suffix);
    if(!fs::exists(p)){std::ofstream f(p,std::ios::binary);f.write((const char*)data,size);need(bool(f),"payload write");}
    return p;
}
inline int greedy(const std::vector<float> & x){need(!x.empty(),"empty owned row");int best=0;for(size_t i=0;i<x.size();++i){need(std::isfinite(x[i]),"nonfinite logits");if(x[i]>x[best])best=int(i);}return best;}

// A selection contains decisions only; the caller owns all verifier vectors.
struct Selection {std::vector<int> emitted;int accepted=0,frontier=0,keep=0;bool rejected=false,done=false;std::string branch;};
inline Selection select_cycle(const std::vector<int> & proposals,const std::vector<int> & decisions,int base,int remaining,const std::function<bool(int)> & eog){
    need(remaining>0 && decisions.size()==proposals.size()+1,"selection shape");Selection s;
    auto emit=[&](int token,int row){s.emitted.push_back(token);s.frontier=row;s.done=eog(token)||int(s.emitted.size())==remaining;};
    for(size_t i=0;i<proposals.size();++i){
        if(decisions[i]==proposals[i]){++s.accepted;emit(proposals[i],int(i));s.branch="accepted";if(s.done){s.keep=base+s.accepted;return s;}}
        else{s.rejected=true;emit(decisions[i],int(i));s.branch="correction";s.keep=base+1+s.accepted;return s;}
    }
    emit(decisions.back(),int(proposals.size()));s.branch=proposals.empty()?"tail":"bonus";s.keep=base+1+int(proposals.size());return s;
}

struct Reader {
    const std::vector<uint8_t> & b;size_t off=0;
    template<class T>T get(){need(off+sizeof(T)<=b.size(),"state header truncated");T x;memcpy(&x,b.data()+off,sizeof(x));off+=sizeof(x);return x;}
    const uint8_t * take(size_t n){need(off+n<=b.size(),"state data truncated");auto p=b.data()+off;off+=n;return p;}
};
inline void append(std::vector<uint8_t> & out,const void * p,size_t n){auto b=(const uint8_t*)p;out.insert(out.end(),b,b+n);}
template<class T>inline void append(std::vector<uint8_t> & out,T x){append(out,&x,sizeof(x));}

// Logical positions and only active K/V bytes, without capacity/free-slot metadata.
inline std::vector<uint8_t> canonical_bytes(const std::vector<uint8_t> & raw,int pending,int pending_position){
    Reader r{raw};
    need(r.get<uint32_t>()==0xaf143cd8 && r.get<int32_t>()==0,"modern sequence header");
    need(r.get<uint32_t>()==1,"single KV stream");uint32_t n=r.get<uint32_t>();
    need(n==uint32_t(pending_position),"active prefix count");
    std::vector<int32_t> positions(n);std::vector<uint32_t> order(n);std::iota(order.begin(),order.end(),0);
    for(auto & p:positions){p=r.get<int32_t>();need(r.get<uint32_t>()==1 && r.get<int32_t>()==0,"canonical sequence metadata");}
    std::sort(order.begin(),order.end(),[&](auto a,auto b){return positions[a]<positions[b];});
    bool contiguous=true;for(uint32_t i=0;i<n;++i){need(positions[order[i]]==int(i),"canonical dense logical prefix");contiguous&=order[i]==i;}
    std::vector<uint8_t> out;out.reserve(raw.size()+64);append(out,"HSSDKV1\0",8);append(out,n);append(out,int32_t(pending));append(out,int32_t(pending_position));
    for(uint32_t i=0;i<n;++i)append(out,int32_t(i));
    if(n==0){need(r.off==raw.size(),"empty state trailing data");return out;}
    uint32_t trans=r.get<uint32_t>(),layers=r.get<uint32_t>(),rk=r.get<uint32_t>(),rv=r.get<uint32_t>();
    need(trans<=1 && layers>0 && rk==0 && rv==0,"fixed Llama F16 state profile");
    for(auto x:{trans,layers,rk,rv})append(out,x);
    for(uint32_t l=0;l<layers;++l){int32_t type=r.get<int32_t>();uint64_t row=r.get<uint64_t>();need(type==1 && row>0,"F16 K profile");append(out,type);append(out,row);auto p=r.take(size_t(n)*row);
        if(contiguous)append(out,p,size_t(n)*row);else for(auto i:order)append(out,p+i*row,row);
    }
    for(uint32_t l=0;l<layers;++l){int32_t type=r.get<int32_t>();need(type==1,"F16 V profile");append(out,type);
        if(!trans){uint64_t row=r.get<uint64_t>();append(out,row);auto p=r.take(size_t(n)*row);if(contiguous)append(out,p,size_t(n)*row);else for(auto i:order)append(out,p+i*row,row);}
        else{uint32_t element=r.get<uint32_t>(),width=r.get<uint32_t>();need(element==2 && width>0,"F16 transposed V profile");append(out,element);append(out,width);auto p=r.take(size_t(n)*element*width);
            for(uint32_t d=0;d<width;++d){auto col=p+size_t(d)*n*element;if(contiguous)append(out,col,size_t(n)*element);else for(auto i:order)append(out,col+i*element,element);}}
    }
    need(r.off==raw.size(),"state trailing data");return out;
}
inline std::vector<uint8_t> canonical(llama_context * c,int pending,int pending_position){
    size_t size=llama_state_seq_get_size(c,0);std::vector<uint8_t> raw(size);
    need(llama_state_seq_get_data(c,raw.data(),size,0)==size,"state export");return canonical_bytes(raw,pending,pending_position);
}
