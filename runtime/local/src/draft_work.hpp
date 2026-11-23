#pragma once
#include <stdexcept>

namespace real_sd {

// The current proposal is consumed only when its output is needed to choose
// another proposal. Its KV is otherwise deferred until target commit is known.
inline bool draft_needs_next_logits(int proposal_index, int proposal_limit, bool is_eog) {
    if (proposal_index < 0 || proposal_limit < 1 || proposal_index >= proposal_limit)
        throw std::runtime_error("Invalid live draft proposal index");
    return !is_eog && proposal_index + 1 < proposal_limit;
}

struct DeferredDraftToken {
    int token = -1;
    int position = -1;

    void defer(int value, int pos) {
        if (position >= 0 || value < 0 || pos < 0)
            throw std::runtime_error("Draft tail must be deferred exactly once");
        token = value;
        position = pos;
    }
    bool exists() const { return position >= 0; }

    bool needs_kv(int keep) const {
        if (!exists()) return false;
        if (keep < 0 || keep > position + 1)
            throw std::runtime_error("Draft commit exceeds computed prefix plus deferred tail");
        // Only the all-accepted bonus case retains the last proposal itself.
        // Accepted-EOG/cap terminal keeps that terminal token pending instead.
        return keep == position + 1;
    }
};

} // namespace real_sd
