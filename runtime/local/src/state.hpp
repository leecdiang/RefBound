#pragma once
#include <dlfcn.h>
#include <cstring>
#include <memory>

// Same dense_seq_f16_v1 grammar and token/layer/K,V order as the inherited
// active_kv.py reader. Hashes every active byte; opaque capacity is excluded.
struct Crypto {
    void* library=dlopen("/usr/lib/x86_64-linux-gnu/libcrypto.so.3",RTLD_NOW|RTLD_LOCAL);
    template<class F>F symbol(const char* name){need(library,"Existing pinned libcrypto");auto f=reinterpret_cast<F>(dlsym(library,name));need(f,"Existing libcrypto EVP ABI");return f;}
    void*(*create)()=symbol<void*(*)()>("EVP_MD_CTX_new");
    void(*destroy)(void*)=symbol<void(*)(void*)>("EVP_MD_CTX_free");
    const void*(*sha256)()=symbol<const void*(*)()>("EVP_sha256");
    int(*init)(void*,const void*,void*)=symbol<int(*)(void*,const void*,void*)>("EVP_DigestInit_ex");
    int(*update)(void*,const void*,size_t)=symbol<int(*)(void*,const void*,size_t)>("EVP_DigestUpdate");
    int(*finish)(void*,unsigned char*,unsigned*)=symbol<int(*)(void*,unsigned char*,unsigned*)>("EVP_DigestFinal_ex");
};
static Crypto& crypto(){static Crypto api;return api;}
struct Digest {
    void* c=crypto().create();
    Digest(){need(c && crypto().init(c,crypto().sha256(),nullptr)==1,"SHA256 init");}
    ~Digest(){crypto().destroy(c);}
    void update(const void* p,size_t n){need(crypto().update(c,p,n)==1,"SHA256 update");}
    std::string finish(){unsigned char b[32];unsigned n=0;need(crypto().finish(c,b,&n)==1 && n==32,"SHA256 final");std::string s;for(auto x:b){s+="0123456789abcdef"[x>>4];s+="0123456789abcdef"[x&15];}return s;}
};
static std::string digest_bytes(const void* p,size_t n){Digest h;h.update(p,n);return h.finish();}
static std::string digest_text(const std::string& s){return digest_bytes(s.data(),s.size());}
struct StateReader {
    const std::vector<uint8_t>& bytes;size_t offset=0;
    template<class T>T read(){need(offset+sizeof(T)<=bytes.size(),"Truncated state header");T x;std::memcpy(&x,bytes.data()+offset,sizeof(T));offset+=sizeof(T);return x;}
    const uint8_t* take(size_t n){need(n<=bytes.size()-offset,"Truncated active state");auto* p=bytes.data()+offset;offset+=n;return p;}
};
static json canonical_kv(const std::vector<uint8_t>& raw,int position,unsigned expected_layers,size_t k_bytes,size_t v_bytes){
    StateReader r{raw};const size_t size=raw.size();
    const uint16_t endian=1;need(*reinterpret_cast<const uint8_t*>(&endian)==1,"Little endian required");
    need(r.read<uint32_t>()==0xaf143cd8 && r.read<int32_t>()==0 && r.read<uint32_t>()==1,"Pinned state format/sequence/stream");
    need(r.read<uint32_t>()==uint32_t(position),"Active cell count");
    for(int t=0;t<position;++t)need(r.read<int32_t>()==t && r.read<uint32_t>()==1 && r.read<int32_t>()==0,"Canonical logical position map");
    const auto transposed=r.read<uint32_t>(),layers=r.read<uint32_t>();
    need(transposed<=1 && layers==expected_layers,"State layer/layout profile");
    std::vector<const uint8_t*> ks,vs;
    for(unsigned l=0;l<layers;++l){need(r.read<int32_t>()==1 && r.read<uint64_t>()==k_bytes,"F16 K row profile");ks.push_back(r.take(position*k_bytes));}
    for(unsigned l=0;l<layers;++l){
        need(r.read<int32_t>()==1,"F16 V profile");
        if(transposed)need(r.read<uint32_t>()==2 && r.read<uint32_t>()==v_bytes/2,"Transposed V profile");
        else need(r.read<uint64_t>()==v_bytes,"V row profile");
        vs.push_back(r.take(position*v_bytes));
    }
    need(r.offset==size,"No unclassified state suffix");
    Digest h;std::vector<uint8_t> vrow(v_bytes);
    for(int t=0;t<position;++t)for(unsigned l=0;l<layers;++l){
        h.update(ks[l]+t*k_bytes,k_bytes);
        if(!transposed)h.update(vs[l]+t*v_bytes,v_bytes);
        else {
            for(size_t j=0;j<v_bytes/2;++j)std::memcpy(vrow.data()+2*j,vs[l]+2*(j*position+t),2);
            h.update(vrow.data(),vrow.size());
        }
    }
    const size_t active_bytes=size_t(position)*layers*(k_bytes+v_bytes);
    return {{"active_KV_bytes",active_bytes},{"active_KV_sha256",h.finish()},{"raw_v_transposed",bool(transposed)}};
}
struct StateEvidence {json proof;std::vector<uint8_t> native;};
static StateEvidence canonical_state(llama_context* c,llama_model* m,int pending,int position,
                                     const std::string& model_hash,const std::string& role) {
    need(position>0 && position<=1024,"Canonical state extent");
    auto mem=llama_get_memory(c);
    need(llama_memory_seq_pos_min(mem,0)==0 && llama_memory_seq_pos_max(mem,0)==position-1,"Canonical dense bounds");
    StateEvidence e;const size_t size=llama_state_seq_get_size(c,0);e.native.resize(size);
    need(size && llama_state_seq_get_data(c,e.native.data(),size,0)==size,"Complete state export");
    const size_t k_bytes=2*m->hparams.n_embd_k_gqa(),v_bytes=2*m->hparams.n_embd_v_gqa();
    const auto kv=canonical_kv(e.native,position,m->hparams.n_layer(),k_bytes,v_bytes);
    json canonical={{"active",true},{"model_sha256",model_hash},{"role",role},{"active_tokens",position},
        {"positions",{{"min",0},{"max",position-1},{"sequence",0}}},{"pending_id",pending},{"pending_position",position},
        {"layers",m->hparams.n_layer()},{"K_row_bytes",k_bytes},{"V_row_bytes",v_bytes},
        {"order","token/layer/K,V/raw-f16-le"},{"active_KV_bytes",kv.at("active_KV_bytes")},{"active_KV_sha256",kv.at("active_KV_sha256")}};
    e.proof=canonical;e.proof["endpoint_sha256"]=digest_text(canonical.dump());
    e.proof["raw_native_bytes"]=size;e.proof["raw_v_transposed"]=kv.at("raw_v_transposed");
    return e;
}
static json inactive_draft(){json j={{"active",false},{"reason","No draft request initialized"}};j["endpoint_sha256"]=digest_text(j.dump());return j;}
