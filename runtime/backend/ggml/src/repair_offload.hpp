#pragma once
#include "../../src/hs_reference_batching.hpp"
#include <cstdio>
#include <cstdlib>
namespace hs_repair_offload {
template<class Backend, class Tensor>
inline bool offload_op(Backend backend, const Tensor * tensor, bool feeds_rope) {
    const bool batch = ggml_backend_offload_op(backend, tensor);
    const auto * norm = tensor->src[0];
    const auto * weight = tensor->src[1];
    const bool head_scale = feeds_rope && tensor->op == GGML_OP_MUL &&
        norm && norm->op == GGML_OP_RMS_NORM && weight &&
        weight->ne[0] == tensor->ne[0] && weight->ne[1] == 1 &&
        weight->ne[2] == 1 && weight->ne[3] == 1 && tensor->ne[3] == 1;
    if (!hs_scope::active || !head_scale || tensor->ne[2] <= 1 || tensor->ne[2] > 32) return batch;
    auto one = *tensor;
    one.ne[2] = 1;
    const bool scalar = ggml_backend_offload_op(backend, &one);
    const bool selected = hs_reference_batching::use_scalar_head_preference(
        hs_scope::active, head_scale, tensor->ne[2], scalar, batch);
    if (std::getenv("HS_RTX164_TRACE")) {
        std::fprintf(stderr,"RTX164_HEAD %s %s heads=%lld rows=%lld scalar=%d batch=%d selected=%d\n",
            tensor->name, ggml_backend_name(backend), (long long)tensor->ne[1],
            (long long)tensor->ne[2], scalar, batch, selected);
    }
    return selected;
}
}
