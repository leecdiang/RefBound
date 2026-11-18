#pragma once
#include "ggml.h"
#include <stdexcept>
#include <cstdint>
#include <cstdlib>

// HS_PREFILL_PACK4 is immutable for the process.  Changing getenv in an
// already running worker is not a profile switch; use a fresh worker.
inline bool hs_prefill_pack4_requested() {
    static const bool value = []() {
        const char * p = std::getenv("HS_PREFILL_PACK4");
        if (!p || (p[0] == '0' && p[1] == 0)) return false;
        if (p[0] == '1' && p[1] == 0) return true;
        throw std::invalid_argument("HS_PREFILL_PACK4 must be 0 or 1");
    }();
    return value;
}
inline bool hs_prefill_pack4_width(int64_t q) {
    return q >= 8 && q <= 32 && q % 4 == 0;
}
extern "C" void hs_work_native4(uint64_t);
static_assert(GGML_MAX_OP_PARAMS >= 64,"Private final matmul metadata slot required");
constexpr int hs_native4_marker_slot=15;
constexpr int hs_native4_marker=0x48534E34;
inline bool hs_native4_marked(const ggml_tensor * t) {
    return t && t->op==GGML_OP_MUL_MAT && t->op_params[hs_native4_marker_slot]==hs_native4_marker;
}
inline void hs_native4_mark(ggml_tensor* t) {
    if(!t || t->op!=GGML_OP_MUL_MAT || t->op_params[hs_native4_marker_slot]!=0)
        throw std::runtime_error("Occupied native4 metadata");
    t->op_params[hs_native4_marker_slot]=hs_native4_marker;
}
inline void hs_native4_require(const ggml_tensor * w,const ggml_tensor * x,const ggml_tensor * y) {
    // Existing q2--4 uses [K,q,1]. P4 preserves the C1 [K,1,q] view.
    const bool small = x && y && x->ne[1]>=2 && x->ne[1]<=4 &&
        x->ne[2]==1 && y->ne[1]==x->ne[1] && y->ne[2]==1;
    const bool wide = x && y && hs_prefill_pack4_requested() &&
        x->ne[1]==1 && hs_prefill_pack4_width(x->ne[2]) &&
        y->ne[1]==1 && y->ne[2]==x->ne[2];
    if(!w || !x || !y || !hs_native4_marked(y) || y->op_params[1]!=0 ||
       (w->type!=GGML_TYPE_Q4_K && w->type!=GGML_TYPE_Q6_K) ||
       x->type!=GGML_TYPE_F32 || y->type!=GGML_TYPE_F32 ||
       w->ne[0]<2048 || w->ne[0]%256 || w->ne[1]%2 || x->ne[0]!=w->ne[0] ||
       (!small && !wide) || y->ne[0]!=w->ne[1] ||
       w->ne[2]!=1 || w->ne[3]!=1 || x->ne[3]!=1 ||
       y->ne[3]!=1 || !ggml_is_contiguous(w) ||
       !ggml_is_contiguous(x) || !ggml_is_contiguous(y) || w->view_src)
        throw std::runtime_error("Native4 candidate rejects descriptor; no fallback");
}
