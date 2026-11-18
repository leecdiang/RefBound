"""Verify displayed precision against saved native records and source summaries."""

if not __debug__:
    raise SystemExit("Optimized Python is unsupported: verification must remain enabled.")

import math
import re
from collections import Counter, defaultdict
from statistics import mean


def same(text, v):
    """Strict display-rounding test, tolerating only binary floating point at a decimal tie."""
    s = str(text).replace(",", "")
    prec = len(s.split(".")[1]) if "." in s else 0
    assert math.isclose(float(s), v, rel_tol=0, abs_tol=0.5*10**(-prec)+1e-10), (text, v)
    if float(s)==0 and (s.startswith("-") or s.startswith("+")) and v:
        assert (s.startswith("-")) == (v < 0), (text, v)


def gmean(values):
    return math.exp(mean([math.log(v) for v in values]))


def near(x, y):
    assert math.isclose(x,y,rel_tol=1e-10,abs_tol=1e-10),(x,y)


def ci(s):
    return s.strip("[]").split(", ")


def hist_bases(body):
    m = re.search(r"(?:Within block|Noncrossing) \((\d+)\).*?Crossing \((\d+)\)", body.source)
    assert m
    return dict(within=m[1],cross=m[2])


def audit(n, body, inputs):
    rows, note = body.rows, body.note
    extra, sources = {}, []
    def use(k,fields,op):
        sources.append((k,fields,op))
        return inputs.get(k)
    def conf():
        return use("conf","results.{A,B}.{ratio,ratio_CI95,block_log_ratios}; primary_endpoints, supporting_endpoints; pairs",
                   "check study/panel, registered role, number of blocks and displayed precision; intervals from frozen summary")
    def m1():
        return use("prior","M1.{census,arm_total_s,contrasts,interaction,bootstrap}",
                   "match arm IDs, time totals, ratio/interval endpoints, conditional paired-root design")
    def native_m1():
        return [x for x in use("mn","kind,root,session,arm,service_s,cycles",
                              "keep kind=measurement; sum native service over sessions without pooling roots or arms") if x["kind"]=="measurement"]
    def rtx():
        return use("rtx","estimates, roots, blocks, counts, workload",
                   "match #269 contrast and role; compare source summaries to each displayed scalar")
    def rpairs():
        data = use("rn","root,root_slot,domain,round,time_block,arm,service_s, *phase_s",
                   "pair eligible B/C1/C4 by actual root, block and round before averaging; retain all formal rows")
        groups = defaultdict(dict)
        for x in data:
            k = (x["root"],int(x["time_block"]),int(x["round"]))
            assert x["arm"] not in groups[k]
            groups[k][x["arm"]]=x
        assert len(data)==3*len(groups) and all(set(t)=={"B","C1","C4"} for t in groups.values())
        return groups
    def native_c():
        records = use("cn","panel,block,case,arm,value_s",
                      "pair exactly one SIMPLE and LOCAL within each same block/case, then take unrounded ratios")
        d = defaultdict(dict)
        for x in records:
            k=(x["panel"],int(x["block"]),x["case"])
            assert x["arm"] not in d[k]
            d[k][x["arm"]]=float(x["value_s"])
        assert len(records)==2*len(d) and all(set(t)=={"SIMPLE","LOCAL"} for t in d.values())
        return d
    if n in ("1","2","7","S17"):
        # These are design/qualification/literature inventories. Their complete
        # source is the identified TeX row + note, not a timing estimator.
        assert len(rows)=={"1":3,"2":7,"7":6,"S17":3}[n]
    elif n=="3":
        doc=use("dep","Deployment profiles: Hardware / backend / build binding and Models and placement",
                "select the named #259, #256 and #247 rows; read hardware strings and both RTX Q8_0 model names before layout")
        find=lambda k:next(l.split("|") for l in doc.splitlines() if l.startswith("| "+k+" ("))
        a,r,b=(find(k) for k in ["A5000 C4","RTX C4 bridge","B570 formal"])
        names=re.fullmatch(r" (.+?) target; (.+?) draft;.*",r[3])
        extra.update(device_a=a[2].split(";")[0].strip(),device_r=r[2].split(";")[0].strip(),
                     device_b=b[2].split(";")[0].strip(),
                     rtx_models=" / ".join(x.replace("_",r"\_") for x in names.groups()))
    elif n=="4":
        work=use("work","study_pr,root,domain,prompt_tokens,display_tokens,display_tokens_status",
                 "check earlier modern input ranges, known output ranges and missing output status per study")
        reg=use("plot","row_counts.{study,roots,rounds,arms,selected_requests}",
                "check each original complete-request design: roots × rounds × arms = measured observations")
        for i,pr in [(0,259),(1,256),(3,257),(4,255),(9,247),(10,254)]:
            a=rows[i]
            w=[x for x in work if x["study_pr"]==str(pr)]
            v=next(x for x in reg["row_counts"] if x["study"].endswith("_"+str(pr)))
            assert len(w)==v["roots"]
            same(a[5],v["selected_requests"])
            same(a[5],len(w)*v["rounds"]*len(v["arms"]))
            lo,hi=min(int(x["prompt_tokens"]) for x in w),max(int(x["prompt_tokens"]) for x in w)
            assert [lo,hi]==list(map(int,re.findall(r"\d+",a[3])))
            actual=[int(x["display_tokens"]) for x in w if x["display_tokens"].isdigit()]
            expected=sorted(set(map(int,re.findall(r"\d+",a[4]))))
            assert (sorted({min(actual),max(actual)}) if actual else []) == expected
        v=rtx()
        same(rows[2][5],v["counts"]["formal_measured"])
        assert v["workload"]["prompt_tokens_range"]==list(map(int,re.findall(r"\d+",rows[2][3])))
        assert v["workload"]["display_tokens_excluding_EOG_range"]==list(map(int,re.findall(r"\d+",rows[2][4])))
        f=conf()
        for ix, panel in [(7,"A"),(8,"B")]:
            same(rows[ix][5],sum(x["panel"]==panel for x in f["measured"]))
        ma=native_m1()
        same(rows[6][5],len(ma))
        l=use("prior","LOCAL.{case,step,pairs} and M1 design", "check original first-transaction count; successors separate")
        same(rows[5][5],2*sum(len(x["pairs"]) for x in l["LOCAL"] if x["step"]==0))
    elif n=="5":
        m=m1()["M1"]
        arms=native_m1()
        c=m["census"]
        which=["W_L4_D4","L_L4_D4","W_P_D4","L_P_D4"]
        counts={arm:(sum(c[arm]["verify_physical_width_hist"].values()),c[arm]["cycles"]) for arm in which}
        w,cy=counts[which[0]]
        l,cl=counts[which[1]]
        assert counts[which[0]]==counts[which[2]] and counts[which[1]]==counts[which[3]] and cy==cl
        for i,arm in enumerate(which):
            records=[x for x in arms if x["arm"]==arm]
            near(sum(float(x["service_s"]) for x in records), m["arm_total_s"][arm])
            assert sum(int(x["cycles"]) for x in records)==cy and len(records)==m["roots"]*m["sessions"]
            same(rows[i//2][i%2+1],m["arm_total_s"][arm])
        for a,x in zip(rows[-2:],m["contrasts"][:2]):
            same(a[1],100*(1-x["ratio"]))
            for v,z in zip(ci(a[2]),reversed(x["ci99_ratio"])): same(v,100*(1-z))
        extra.update(removed=w-l,cycles_fmt=f"{cy:,}",whole_fmt=f"{w:,}",local_fmt=f"{l:,}",
                     opportunity=f"{100*(w-l)/cy:.2f}")
    elif n in ("6","S3","S4","S5"):
        f=conf()
        native=native_c()
        for x in f["pairs"]:
            clean=native[x["panel"],x["block"],x["case"]]
            for arm in ["LOCAL","SIMPLE"]: near(clean[arm],x[arm+"_s"])
            near(clean["LOCAL"]/clean["SIMPLE"],x["ratio"])
        if n in ("6","S3"):
            endpoints=([("B","equal_conversation_overall"),("B","C0"),("B","C1")] if n=="6" else
                       [("A","negative"),("A","positive"),("A","interaction"),
                        ("B","equal_conversation_overall"),("B","C0"),("B","C1")])
            for a,(panel,case) in zip(rows,endpoints):
                x=f["results"][panel][case]
                assert (panel+"/"+case in f["primary_endpoints"]) == (a[1]=="Primary")
                assert (panel+"/"+case in f["supporting_endpoints"]) == (a[1]=="Supporting")
                logs=x["block_log_ratios"]
                def ratio(block,case):
                    pair=native[panel,block,case]
                    return pair["LOCAL"]/pair["SIMPLE"]
                blocks=sorted({key[1] for key in native if key[0]==panel})
                paired=[gmean([ratio(b,"C0"),ratio(b,"C1")]) if case=="equal_conversation_overall" else
                        ratio(b,"positive")/ratio(b,"negative") if case=="interaction" else ratio(b,case) for b in blocks]
                assert len(logs)==len(paired)
                near(gmean(paired), x["ratio"])
                if n=="6":
                    same(a[2],100*(1-x["ratio"]))
                    for v,z in zip(ci(a[3]),reversed(x["ratio_CI95"])): same(v,100*(1-z))
                    same(a[4],len(blocks))
                else:
                    for v,z in zip(a[2:], [x["ratio"]]+x["ratio_CI95"]): same(v,z)
            if n=="6":
                obj=use("dispatch","observed_partitions.B/{C0,C1}/{W,L}.{physical_projection_calls,physical_rows,width_counts}",
                        "sum width-count frequencies and weighted rows independently. Cross-bind W/L to SIMPLE/LOCAL and both cases against sections/supplement.tex; no estimate for aggregate calls.")
                assert obj["status"]=="PASS"
                calls,counts={},{}
                for case in ["C0","C1"]:
                    d = [obj["observed_partitions"][f"B/{case}/{a}"] for a in ("W","L")]
                    for o in d:
                        assert sum(o["width_counts"].values())==o["physical_projection_calls"]
                        assert sum(int(k)*v for k,v in o["width_counts"].items())==o["physical_rows"]
                    assert d[0]["physical_rows"]==d[1]["physical_rows"]
                    calls[case]=[o["physical_projection_calls"] for o in d]
                    counts[case]=d[0]["physical_rows"]
                txt=inputs.tex("sections/supplement.tex")
                assert f"C0 retains {calls['C0'][0]} physical calls and {counts['C0']} target rows in either arm." in txt
                assert f"C1 has {calls['C1'][0]} SIMPLE versus {calls['C1'][1]} LOCAL calls at {counts['C1']} rows" in txt
                extra.update(calls=calls,target_rows=counts,c0s=calls["C0"][0],c0l=calls["C0"][1],
                             c1s=calls["C1"][0],c1l=calls["C1"][1])
        else:
            panel="A" if n=="S4" else "B"
            cases=("negative","positive") if panel=="A" else ("C0","C1")
            for a in rows:
                for j,case in enumerate(cases):
                    pair=native[(panel,int(a[0]),case)]
                    factor=1000 if panel=="A" else 1
                    for v,z in zip(a[1+3*j:4+3*j],[pair["SIMPLE"]*factor, pair["LOCAL"]*factor,pair["LOCAL"]/pair["SIMPLE"]]): same(v,z)
            if panel=="A": extra.update(hist_bases(body))
    elif n=="S1":
        local=use("prior","LOCAL[].{case,step,pairs[].{base,round,SIMPLE_ms,LOCAL_ms,ratio}}",
                  "index by geometry, step and repeat; verify all eight clean pairs at 3/6 decimal places")["LOCAL"]
        for a in rows:
            geom="positive" if a[0]=="Crossing" else "negative"
            step=next(x for x in local if x["case"]==geom and x["step"]==int(a[1]=="Successor"))
            x=next(x for x in step["pairs"] if x["round"]==int(a[3]))
            for v,k in zip([a[2]]+a[4:],["base","SIMPLE_ms","LOCAL_ms","ratio"]): same(v,x[k])
    elif n=="S2":
        diag=use("plot","local_diagnostics[].{request_id,category_calls,category_kernel_ms,memcpy_ms}",
                 "order actual c0/c1 and SIMPLE/LOCAL runs; sum projection_prepare + projection_dot milliseconds; absent stitch events have zero calls/time")
        for i,(case,arm) in enumerate((("c0","SIMPLE"),("c0","LOCAL"),("c1","SIMPLE"),("c1","LOCAL"))):
            x=next(x for x in diag["local_diagnostics"] if "-"+case+"-" in x["request_id"] and "-"+arm+"-" in x["request_id"])
            calls=x["category_calls"];ms=x["category_kernel_ms"]
            vals=[calls["projection_prepare"],calls["projection_dot"],calls["attention_core"],calls.get("attention_stitch",0),
                  ms["projection_prepare"]+ms["projection_dot"],ms["attention_core"],ms.get("attention_stitch",0),x["memcpy_ms"]]
            for a,z in zip(rows,vals): same(a[i+1],z)
        extra.update(hist_bases(body))
    elif n=="S6":
        f=use("conf","measured[panel=B].{case,block,arm,phases.*,value_s}",
              "within each fixed conversation, average all matched block differences ×1000 (s→ms); all 12 components close to the full original clock")
        keys=["actual_consumer_s","canonical_producer_s","controller_reset_overhead_s","controller_response_overhead_s",
              "decode_sync_and_budget_s","greedy_sampling_s","native_reset_s","native_response_residual_s",
              "output_owned_copy_s","reconcile_and_checkpoint_s","request_finish_s","request_reserve_s"]
        for j,case in enumerate(["C0","C1"]):
            d={(x["arm"],x["block"]):x for x in f["measured"] if x["panel"]=="B" and x["case"]==case}
            bs=sorted({b for _,b in d})
            diffs=[1000*mean(d["LOCAL",b]["phases"][k]-d["SIMPLE",b]["phases"][k] for b in bs) for k in keys]
            total=1000*mean(d["LOCAL",b]["value_s"]-d["SIMPLE",b]["value_s"] for b in bs)
            near(sum(diffs),total)
            for a,v in zip(rows,diffs+[total]): same(a[j+1],v)
    elif n in ("S7","S8","S9","S10"):
        v=rtx();d=rpairs(); contrasts=list(v["estimates"])
        def readratio(k,c):
            a,b=c.split("/");return float(d[k][a]["service_s"])/float(d[k][b]["service_s"])
        if n=="S7":
            for a in rows:
                c,role=a[0].split(" / ");x=v["estimates"][c]
                assert role in x["role"]
                near(gmean(readratio(k,c) for k in d),x["ratio"])
                for y,z in zip([a[1],*ci(a[2]),a[3]],[x["ratio"],*x["ci95"],x["reduction_percent"]]):same(y,z)
        elif n in ("S8","S9"):
            which="blocks" if n=="S8" else "roots"
            assert len(rows)==len(v[which])
            for a,x in zip(rows,v[which]):
                if n=="S8":
                    assert int(a[0])==x["time_block"]+1
                    ks=[k for k in d if k[1]==x["time_block"]]
                else:
                    assert a[0]==x["root"].replace("CodeContests","Code").replace("counting_and_probability","counting/prob.")
                    ks=[k for k in d if k[0]==x["root"]]
                for i,c in enumerate(contrasts):
                    near(gmean(readratio(k,c) for k in ks), x[c])
                    same(a[i+1],x[c])
        else:
            keys=["context","target_prefill","target_decode","target_verify","draft_prefill","draft_sync","draft_propose",
                  "decision_commit","terminal_sync","other_host","service"]
            for j,c in enumerate(contrasts):
                ca,co=c.split("/")
                values=[1000*mean(float(a[ca][k+"_s"])-float(a[co][k+"_s"]) for a in d.values()) for k in keys]
                near(sum(values[:-1]),values[-1])
                for a,k,x in zip(rows,keys,values):
                    same(a[j+1],x)
                    near(x,v["estimates"][c]["phase_ms"][k])
    elif n=="S11":
        modern=use("prior","modern_effects[study_pr,contrast].{candidate,control,ratio,ci95_ratio}",
                   "retain all 16 named contrasts from the five baseline studies; validate point and interval to six decimals")["modern_effects"]
        observations=use("pairs","study_pr,contrast,root,round,candidate_s,control_s",
                         "form each root's paired geometric ratio from all its rounds then equal-root geometric mean; contrasts are not independent requests")
        ids={"A5000 C4":259,"RTX C4":256,"A5000 P4":257,"RTX P4":255,"B570 formal":247}
        for a in rows:
            c=a[1].replace(r"\_","_");pr=ids[a[0]]
            x=next(x for x in modern if x["study_pr"]==pr and x["contrast"]==c)
            by=defaultdict(list)
            for t in observations:
                if t["study_pr"]==str(pr) and t["contrast"]==c:
                    by[t["root"]].append(float(t["candidate_s"])/float(t["control_s"]))
            near(gmean(gmean(z) for z in by.values()),x["ratio"])
            for y,z in zip(a[2:],[x["ratio"],*x["ci95_ratio"]]): same(y,z)
    elif n=="S12":
        s=use("plot","stage_costs[study,contrast].{signed_mean_ms,candidate_mean_ms.service_s,control_mean_ms.service_s}",
              "sum original signed ms over each printed phase group; total = difference of service means (already expressed in ms)")["stage_costs"]
        groups=[["target_prefill_s"],["target_verify_s"],["draft_prefill_s","draft_sync_s","draft_propose_s"],
                ["decision_commit_s"],["context_s","terminal_sync_s","other_host_s"]]
        for i,(study,contra) in enumerate(zip(["259","256","257","255"],["C4/C1"]*2+["SD_P4/SD_C4"]*2)):
            x=next(x for x in s if x["study"].endswith("_"+study) and x["contrast"]==contra)
            v=[sum(x["signed_mean_ms"][k] for k in g) for g in groups]
            tot=x["candidate_mean_ms"]["service_s"]-x["control_mean_ms"]["service_s"]
            near(sum(v),tot)
            for a,z in zip(rows,v+[tot]):same(a[i+1],z)
    elif n=="S13":
        m=m1()["M1"]
        for a,x in zip(rows,m["contrasts"]+[m["interaction"]]):
            for y,z in zip(a[1:],[x["ratio"],*x["ci99_ratio"]]): same(y,z)
    elif n=="S14":
        vals=defaultdict(lambda:defaultdict(list))
        for x in native_m1(): vals[x["root"]][x["arm"]].append(float(x["service_s"]))
        assert len(vals)==len(rows)
        for a in rows:
            k=a[0].replace(" / ","/").replace("interm. algebra","intermediate_algebra").replace("number theory","number_theory")
            domain,slot=k.rsplit("/",1); arms=vals[domain+"/train/"+slot]
            sums=[sum(arms[k]) for k in ("W_L4_D4","L_L4_D4","W_P_D4","L_P_D4")]
            for y,z in zip(a[1:],sums+[sums[1]/sums[0],sums[3]/sums[2]]):same(y,z)
    elif n=="S15":
        nats=use("prior","natural_service.historical_RTX.pairs and historical_A5000_target_only",
                 "RTX: all four roots × three sessions geometric paired ratios; A5000: ratio of total complete episodes, never pooled")["natural_service"]
        x=nats["historical_RTX"]
        near(gmean(p["LOCAL_s"]/p["WHOLE_s"] for p in x["pairs"]),x["ratio"])
        same(rows[0][2],x["ratio"])
        data=use("nat","stage,arm,physical_calls,timing.controller_service_plus_reset_s,phases.greedy_sampling_s",
                 "filter MEASURE episodes: sum totals/calls by L/W and difference in common sampling (not confirmatory data)")
        measured=[x for x in data if x["stage"]=="MEASURE"]
        totals={a:sum(x["timing"]["controller_service_plus_reset_s"] for x in measured if x["arm"]==a) for a in ["W","L"]}
        samp={a:sum(x["phases"]["greedy_sampling_s"] for x in measured if x["arm"]==a) for a in ["W","L"]}
        same(rows[1][2],totals["L"]/totals["W"])
        text=re.findall(r"(\d+\.\d+)\\,s", rows[1][3])
        for t,a in zip(text,("W","L")): same(t,totals[a])
        for t,val in zip(re.findall(r"(\d+\.\d+)\\,s",note),[totals["L"]-totals["W"],samp["L"]-samp["W"]]): same(t,val)
        for a,v in nats["historical_A5000_target_only"]["physical_calls"].items():
            assert sum(x["physical_calls"] for x in measured if x["arm"]==a)==v and f"{v:,}" in note
    elif n=="S16":
        raw=use("ra","included,stage,role,request_id",
                "formal eligibility = included=True AND stage=formal AND role=measured; preserve both excluded six-request units, even when internally labelled measured")
        eligible=[x for x in raw if x["included"]=="True"]
        formal=[x for x in eligible if x["stage"]=="formal"]
        a=next(t for t in rows if t[0]=="RTX confirmation");c=Counter(x["role"] for x in formal)
        for t,val in zip(a[1:],[len(raw),c["measured"],c["warmup"],len(raw)-len(formal)]):same(t,val)
        excluded=Counter(x["stage"] for x in raw if x["included"]!="True")
        assert len(set(excluded.values()))==1 and len(excluded)==2
        for a in rows:
            nums=[int(k.replace(",","")) for k in a[1:]]; assert nums[0]==sum(nums[1:]),a
        v=use("plot","row_counts[].{study,raw_rows,selected_requests}",
              "six earlier independent timing registries: check total and eligible counts")["row_counts"]
        for i,j in [(0,0),(1,1),(4,2),(5,3),(6,4),(7,5)]:
            same(rows[i][1],v[j]["raw_rows"]);same(rows[i][2],v[j]["selected_requests"])
        same(rows[-1][2],len(native_m1()))
        same(rows[3][2],len(conf()["measured"]))
    elif n=="S18":
        m=use("prior","modern_effects[study_pr=254].{contrast,root_points,ratio,population_interval}",
              "verify two predeclared roots, three ratios and absence of a population interval")["modern_effects"]
        for a in rows[:3]:
            x=next(x for x in m if x["study_pr"]==254 and x["contrast"]==a[0].replace(r"\_","_"))
            vals=[next(t["ratio"] for t in x["root_points"] if t["domain"]==d) for d in ("code","math")]
            assert not x["population_interval"]
            for t,z in zip(a[1:],vals+[x["ratio"]]):same(t,z)
        v=use("plot","stage_costs[B570_repair_254,SD_C/TO_C].{candidate_mean_ms,control_mean_ms}",
              "draft prefill+sync+propose versus target decode-to-verify saving; divide source means by 1000 to show seconds")
        x=next(x for x in v["stage_costs"] if x["study"].endswith("_254") and x["contrast"]=="SD_C/TO_C")
        ca,co=x["candidate_mean_ms"],x["control_mean_ms"]
        for a,z in zip(rows[3:],[sum(ca[k] for k in ["draft_prefill_s","draft_sync_s","draft_propose_s"]),
                                co["target_decode_s"]-ca["target_verify_s"]]):
            same(re.search(r"\{([\d.]+)\}$",a[1])[1],z/1000)
    elif n=="S19":
        h=use("hist","vulkan_width[].{deployment,q,blocks,cross,inside}",
              "match fixed-cell keys, invert each original W/L separately (1/cross,1/inside) to display L/W; no CI or pooling")["vulkan_width"]
        assert len(h)==len(rows)
        for a,x in zip(rows,h):
            assert a[0]==x["deployment"].replace("dual-resident","dual").replace("target-only","target only")
            for t,z in zip(a[1:],[x["q"],x["blocks"],1/x["cross"],1/x["inside"]]):same(t,z)
    elif n=="S20":
        v=use("apps","[pr].{totals,reported_ratios,reported_intervals,process_s,process_values_rounded,root_ratios_best_M,commit,source_path}",
              "independently choose fastest available measured M for each lifetime; direct resident family endpoints; worker difference = process_s[L_P_D4] minus its own fastest M")
        controls=["W_L4_M","W_P_M","L_L4_M","L_P_M"];out=[]
        for a,x in zip(rows,v):
            j=controls.index(min(controls,key=lambda k:x["totals"][k]))
            work=x["process_s"];fast=min(work[k] for k in controls if k in work);cand=work["L_P_D4"]
            vals=[x["roots"],x["reported_ratios"][j],*x["reported_intervals"][j],fast,cand]
            for y,z in zip([a[1],a[2],*ci(a[3]),*a[4:]],vals):same(y,z)
            out.append(f"{cand-fast:+.3f}")
        extra["worker_delta"]=out
    else: raise KeyError(n)
    return extra,sources
