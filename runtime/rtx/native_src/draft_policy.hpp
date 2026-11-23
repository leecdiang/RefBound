#pragma once
#include <algorithm>
#include <cstdlib>
#include <stdexcept>
#include <string>

// CPU-testable policy; model arithmetic and target selection are elsewhere.
struct DriverOptions {
    std::string draft_profile = "legacy";
    std::string frontend_profile = "legacy";
    bool target_pack4 = false;
    std::string unused_draft_logits = "keep";
    bool native_draft() const { return draft_profile == "native32"; }
    bool deferred() const { return frontend_profile == "deferred"; }
    int draft_mode() const { return native_draft() ? 0 : 1; }
    int draft_ubatch() const { return native_draft() ? 32 : 1; }
    bool keep_unused_logits() const { return unused_draft_logits == "keep"; }
};

inline DriverOptions driver_options(const char * draft, const char * frontend, const char * pack4 = nullptr, const char * unused = nullptr) {
    DriverOptions o;
    if (draft && *draft) o.draft_profile = draft;
    if (frontend && *frontend) o.frontend_profile = frontend;
    if (o.draft_profile != "legacy" && o.draft_profile != "native32")
        throw std::invalid_argument("HS_SD_DRAFT_PROFILE must be legacy or native32");
    if (o.frontend_profile != "legacy" && o.frontend_profile != "deferred")
        throw std::invalid_argument("HS_SD_FRONTEND must be legacy or deferred");
    if (pack4 && *pack4) {
        if (std::string(pack4) != "0" && std::string(pack4) != "1")
            throw std::invalid_argument("HS_SD_TARGET_PACK4 must be 0 or 1");
        o.target_pack4 = std::string(pack4) == "1";
    }
    if (unused && *unused) o.unused_draft_logits = unused;
    if (o.unused_draft_logits != "keep" && o.unused_draft_logits != "omit")
        throw std::invalid_argument("HS_SD_UNUSED_DRAFT_LOGITS must be keep or omit");
    return o;
}

struct OutputPolicy { bool request_logits; bool own_logits; };
inline OutputPolicy prefill_output_policy(bool draft, bool deferred, bool capture, bool last_chunk, bool keep_unused = false) {
    if (!deferred || capture) return {true, true};
    // Target backend execution is unchanged; only unused host copies disappear.
    // Draft prompt logits are unused: the first seed comes from the target.
    return draft ? OutputPolicy{keep_unused, false} : OutputPolicy{true, last_chunk};
}

inline bool materialize_proposal_now(bool deferred, int index, int k_eff, bool draft_eog) {
    return !deferred || (!draft_eog && index + 1 < k_eff);
}

struct DraftCommitPlan { int missing_rows; int skipped_rows; };
inline DraftCommitPlan draft_commit_plan(bool deferred, int proposal_count,
                                        int materialized_end, int keep) {
    int missing = std::max(0, keep - materialized_end);
    if (missing > 1 || (missing && (!deferred || proposal_count == 0)))
        throw std::logic_error("draft materialization gap exceeds deferred last proposal");
    return {missing, deferred && proposal_count ? 1 - missing : 0};
}

inline int request_k_max(bool sd, bool capture, bool qualification, int requested, int qual_only) {
    if (qual_only) {
        if (!sd || !capture || !qualification || qual_only != 2 || requested != 2)
            throw std::invalid_argument("qual_only_k_max=2 requires captured SD/R_TRACE qualification");
        return 2;
    }
    if (sd && requested != 3)
        throw std::invalid_argument("main SD k_max must remain 3");
    return 3;
}
