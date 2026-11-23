#pragma once
#include "support.hpp"
#include <cupti.h>
#include <array>
#include <atomic>
#include <malloc.h>
#include <mutex>

namespace hs_capture {

inline void cu(CUptiResult rc, const char * call) {
    if (rc == CUPTI_SUCCESS) return;
    const char * detail = nullptr;
    cuptiGetResultString(rc, &detail);
    throw std::runtime_error(std::string(call) + ": " + (detail ? detail : "unknown CUPTI error"));
}

struct Session {
    static inline std::atomic<Session *> active{nullptr};
    static constexpr auto correlation_kind = CUPTI_EXTERNAL_CORRELATION_KIND_CUSTOM0;
    static constexpr std::array kinds = {
        CUPTI_ACTIVITY_KIND_EXTERNAL_CORRELATION, CUPTI_ACTIVITY_KIND_DRIVER, CUPTI_ACTIVITY_KIND_RUNTIME,
        CUPTI_ACTIVITY_KIND_CONCURRENT_KERNEL, CUPTI_ACTIVITY_KIND_MEMCPY, CUPTI_ACTIVITY_KIND_MEMSET,
    };
    std::mutex lock;
    std::ofstream records, raw, buffers, scopes;
    fs::path directory;
    std::atomic<uint64_t> sequence{0};
    uint64_t raw_offset = 0, buffer_count = 0, dropped = 0, decoded = 0;
    std::atomic<bool> failed{false};
    uint32_t version = 0;
    bool finished = false;

    explicit Session(const fs::path & dir) : directory(dir) {
        need(active == nullptr, "one CUPTI session per worker");
        records.open(dir / "cupti.activities.jsonl", std::ios::binary);
        raw.open(dir / "cupti.buffers.bin", std::ios::binary);
        buffers.open(dir / "cupti.buffers.jsonl", std::ios::binary);
        scopes.open(dir / "cupti.scopes.jsonl", std::ios::binary);
        need(records && raw && buffers && scopes, "CUPTI evidence file open");
        cu(cuptiGetVersion(&version), "cuptiGetVersion");
        cu(cuptiSetThreadIdType(CUPTI_ACTIVITY_THREAD_ID_TYPE_SYSTEM), "cuptiSetThreadIdType");
        active = this;
        try {
            cu(cuptiActivityRegisterCallbacks(requested, completed), "cuptiActivityRegisterCallbacks");
            for (auto kind : kinds) cu(cuptiActivityEnable(kind), "cuptiActivityEnable");
        } catch (...) {
            active = nullptr;
            throw;
        }
    }

    static void CUPTIAPI requested(uint8_t ** data, size_t * size, size_t * max_records) noexcept {
        *size = 1 << 20;
        *data = static_cast<uint8_t *>(_aligned_malloc(*size, 8));
        *max_records = 0;
        if (!*data) {
            *size = 0;
            if (auto * session = active.load()) session->failed = true;
        }
    }

    static void CUPTIAPI completed(CUcontext context, uint32_t stream, uint8_t * bytes,
                                    size_t, size_t valid) noexcept {
        try {
            if (auto * session = active.load()) session->accept(context, stream, bytes, valid);
        } catch (...) {
            if (auto * session = active.load()) session->failed = true;
        }
        _aligned_free(bytes);
    }

    void emit(const json & entry) {
        records << entry.dump() << '\n';
        ++decoded;
    }

    void accept(CUcontext context, uint32_t stream, uint8_t * bytes, size_t valid) {
        std::lock_guard<std::mutex> guard(lock);
        size_t lost = 0;
        cu(cuptiActivityGetNumDroppedRecords(context, stream, &lost), "cuptiActivityGetNumDroppedRecords");
        dropped += lost;
        buffers << json{{"buffer", ++buffer_count}, {"offset", raw_offset}, {"bytes", valid},
                        {"callback_stream", stream}, {"dropped", lost}}.dump() << '\n';
        raw.write(reinterpret_cast<const char *>(bytes), valid);
        raw_offset += valid;
        if (!valid) return;
        CUpti_Activity * current = nullptr;
        for (;;) {
            auto rc = cuptiActivityGetNextRecord(bytes, valid, &current);
            if (rc == CUPTI_ERROR_MAX_LIMIT_REACHED) break;
            cu(rc, "cuptiActivityGetNextRecord");
            switch (current->kind) {
            case CUPTI_ACTIVITY_KIND_EXTERNAL_CORRELATION: {
                auto & a = *reinterpret_cast<const CUpti_ActivityExternalCorrelation *>(current);
                if (a.externalKind == correlation_kind) {
                    emit({{"kind", "external"}, {"corr", a.correlationId}, {"scope", a.externalId}});
                }
                break;
            }
            case CUPTI_ACTIVITY_KIND_RUNTIME:
            case CUPTI_ACTIVITY_KIND_DRIVER: {
                auto & a = *reinterpret_cast<const CUpti_ActivityAPI *>(current);
                const bool runtime = current->kind == CUPTI_ACTIVITY_KIND_RUNTIME;
                const char * name = nullptr;
                cuptiGetCallbackName(runtime ? CUPTI_CB_DOMAIN_RUNTIME_API : CUPTI_CB_DOMAIN_DRIVER_API, a.cbid, &name);
                emit({{"kind", runtime ? "runtime" : "driver"}, {"corr", a.correlationId},
                      {"start", a.start}, {"end", a.end}, {"pid", a.processId}, {"tid", a.threadId},
                      {"cbid", a.cbid}, {"api", name ? name : ""}, {"result", a.returnValue}});
                break;
            }
            case CUPTI_ACTIVITY_KIND_CONCURRENT_KERNEL: {
                auto & a = *reinterpret_cast<const CUpti_ActivityKernel9 *>(current);
                emit({{"kind", "kernel"}, {"corr", a.correlationId}, {"start", a.start}, {"end", a.end},
                      {"device", a.deviceId}, {"context", a.contextId}, {"stream", a.streamId},
                      {"grid", {a.gridX, a.gridY, a.gridZ}}, {"block", {a.blockX, a.blockY, a.blockZ}},
                      {"name", a.name ? a.name : ""}});
                break;
            }
            case CUPTI_ACTIVITY_KIND_MEMCPY: {
                auto & a = *reinterpret_cast<const CUpti_ActivityMemcpy6 *>(current);
                emit({{"kind", "memcpy"}, {"corr", a.correlationId}, {"start", a.start}, {"end", a.end},
                      {"device", a.deviceId}, {"context", a.contextId}, {"stream", a.streamId},
                      {"copy_kind", a.copyKind}, {"bytes", a.bytes}});
                break;
            }
            case CUPTI_ACTIVITY_KIND_MEMSET: {
                auto & a = *reinterpret_cast<const CUpti_ActivityMemset4 *>(current);
                emit({{"kind", "memset"}, {"corr", a.correlationId}, {"start", a.start}, {"end", a.end},
                      {"device", a.deviceId}, {"context", a.contextId}, {"stream", a.streamId}, {"bytes", a.bytes}});
                break;
            }
            default:
                emit({{"kind", "other"}, {"activity_kind", int(current->kind)}});
            }
        }
        need(records && raw && buffers, "write CUPTI evidence");
    }

    void finish(bool completed_request) {
        if (finished) return;
        cu(cuptiActivityFlushAll(0), "cuptiActivityFlushAll");
        for (auto kind : kinds) cu(cuptiActivityDisable(kind), "cuptiActivityDisable");
        {
            std::lock_guard<std::mutex> guard(lock);
            records.flush();
            raw.flush();
            buffers.flush();
            scopes.flush();
            write_json(directory / "cupti.summary.json",
                       {{"version", version}, {"worker_pid", GetCurrentProcessId()}, {"scope_count", sequence.load()},
                        {"native_request_completed", completed_request}, {"activity_records", decoded},
                        {"raw_buffer_count", buffer_count}, {"raw_buffer_bytes", raw_offset}, {"dropped", dropped},
                        {"collector_error", failed.load() || !records || !raw || !scopes || !buffers}});
        }
        finished = true;
        active = nullptr;
        need(!completed_request || (!failed && dropped == 0 && decoded > 0 && raw && records && scopes && buffers),
             "incomplete CUPTI capture");
    }

    ~Session() {
        if (!finished) {
            try { finish(false); } catch (...) { active = nullptr; }
        }
    }
};

struct Scope {
    static inline thread_local uint64_t top = 0;
    Session * session = Session::active.load();
    uint64_t id = 0, parent = 0, begin = 0;
    json fields;

    Scope(const char * kind, const std::string & name, json metadata = json::object()) : fields(std::move(metadata)) {
        if (!session) return;
        id = ++session->sequence;
        parent = top;
        fields["kind"] = kind;
        fields["name"] = name;
        cu(cuptiGetTimestamp(&begin), "cuptiGetTimestamp begin");
        cu(cuptiActivityPushExternalCorrelationId(Session::correlation_kind, id),
           "cuptiActivityPushExternalCorrelationId");
        top = id;
    }

    Scope(const Scope &) = delete;
    Scope & operator=(const Scope &) = delete;

    ~Scope() noexcept {
        if (!session) return;
        try {
            uint64_t popped = 0, end = 0;
            cu(cuptiActivityPopExternalCorrelationId(Session::correlation_kind, &popped),
               "cuptiActivityPopExternalCorrelationId");
            need(popped == id && top == id, "CUPTI scope stack");
            cu(cuptiGetTimestamp(&end), "cuptiGetTimestamp end");
            fields.update({{"id", id}, {"parent", parent}, {"pid", GetCurrentProcessId()},
                           {"tid", GetCurrentThreadId()}, {"start", begin}, {"end", end}});
            session->scopes << fields.dump() << '\n';
            if (!session->scopes) session->failed = true;
        } catch (...) {
            session->failed = true;
        }
        top = parent;
    }
};

} // namespace hs_capture
