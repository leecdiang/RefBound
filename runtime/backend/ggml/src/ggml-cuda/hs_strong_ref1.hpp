#pragma once
#include "ggml.h"
#include <cstring>
#include <stdexcept>
#include <cstdint>
extern "C" void hs_work_quant(uint64_t, uint64_t);
extern "C" void hs_work_dot(uint64_t);
extern "C" void hs_work_backend();
extern "C" void hs_work_quant_payload(const void*,uint64_t,uint64_t,void*);
static_assert(GGML_MAX_OP_PARAMS >= 64,"Private final matmul metadata slot required");
constexpr int hs_strong_marker_slot=15;
constexpr int hs_strong_marker=0x48534231;
inline bool hs_strong_marked(const ggml_tensor * t) {
    return t && t->op==GGML_OP_MUL_MAT && t->op_params[hs_strong_marker_slot]==hs_strong_marker;
}
inline void hs_strong_mark(ggml_tensor* t) {
    if(!t || t->op!=GGML_OP_MUL_MAT || t->op_params[hs_strong_marker_slot]!=0)
        throw std::runtime_error("Occupied or unsupported backend-loop metadata");
    t->op_params[hs_strong_marker_slot]=hs_strong_marker;
}
inline void hs_strong_require(const ggml_tensor * w, const ggml_tensor * x, const ggml_tensor * y) {
    if (!w || !x || !y || !hs_strong_marked(y) || y->op_params[1]!=0 ||
        (w->type != GGML_TYPE_Q4_K && w->type != GGML_TYPE_Q6_K) ||
        x->type != GGML_TYPE_F32 || y->type != GGML_TYPE_F32 ||
        w->ne[0] <= 0 || w->ne[0] % 256 || x->ne[0] != w->ne[0] ||
        x->ne[1] < 1 || x->ne[1] > 32 || y->ne[0] != w->ne[1] || y->ne[1] != x->ne[1] ||
        w->ne[2] != 1 || w->ne[3] != 1 || x->ne[2] != 1 || x->ne[3] != 1 ||
        y->ne[2] != 1 || y->ne[3] != 1 || !ggml_is_contiguous(w) ||
        !ggml_is_contiguous(x) || !ggml_is_contiguous(y) || w->view_src) {
        throw std::runtime_error("strong REF1 backend rejects descriptor; no fallback");
    }
}
