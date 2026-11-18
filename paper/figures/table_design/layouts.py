"""Editorial projections. All body values/prose are read from the pinned TeX/data."""

if not __debug__:
    raise SystemExit("Optimized Python is unsupported: verification must remain enabled.")

import re

END = r"\\"
MID = r"\midrule"
GAP = r"\addlinespace[2.5pt]"
X = r">{\raggedright\arraybackslash}X"


def p(frac):
    return r">{\raggedright\arraybackslash}p{"+str(frac)+r"\linewidth}"


def num(a):
    s = str(a)
    # With common precision, right alignment aligns decimal points and gives
    # a real mathematical minus sign. Never normalize negative rounded zeros.
    if re.fullmatch(r"[+-]?\d[\d,]*(?:\.\d+)?", s):
        return "$"+s.replace(",", "{,}")+"$"
    return s


def row(*cells):
    return " & ".join(map(num, cells)) + END


def span(k, text, align="c"):
    return rf"\multicolumn{{{k}}}{{{align}}}{{{text}}}"


def band(k, text):
    return row(span(k, r"\textbf{"+text+"}", "@{}l"))


def rules(*pairs):
    return "".join(rf"\cmidrule(lr){{{a}-{b}}}" for a, b in pairs)


def grid(spec, head, rows):
    env = "tabularx" if "X" in spec else "tabular*"
    left = "@{}" if env == "tabularx" else r"@{\extracolsep{\fill}}"
    return "\n".join([rf"\begin{{{env}}}{{\linewidth}}{{{left}{spec}@{{}}}}",
                      r"\toprule", *head, MID, *rows, r"\bottomrule", rf"\end{{{env}}}"])


def wrap(content, note, size="8.7", leading="10.5", pad="3.5", note_tag="Note"):
    t = [r"\begingroup", rf"\fontsize{{{size}}}{{{leading}}}\selectfont",
         rf"\setlength{{\tabcolsep}}{{{pad}pt}}\renewcommand{{\arraystretch}}{{1.03}}",
         r"\noindent", content]
    if note:
        t.extend([r"\par\smallskip", r"\fontsize{8}{9.6}\selectfont\raggedright",
                  r"\textit{"+note_tag+".} "+note])
    t.extend([r"\par\endgroup", ""])
    return "\n".join(t)


def bounds(s):
    m = re.fullmatch(r"\[([^,]+), ([^]]+)\]", s)
    assert m, s
    return m.groups()


def record(a, b):
    return r"\textbf{"+a+r"}\newline "+b


def labels(src, indices):
    return [src[i] for i in indices]


def render(n, body, e):
    r, note = body.rows, body.note
    if n == "1":
        h = [row("Per MMVQ operation", *[rf"\textbf{{{a[0]}}}" for a in r])]
        rr = [row("Invocations", *[a[1] for a in r]), row("Columns per group", *[a[2] for a in r]),
              MID, row("After shared preparation", *[a[3] for a in r])]
        return wrap(grid(p(.19)+X+X+X, h, rr), note, note_tag="Admission"), {
            "column keys": "source Path; transpose each source row to a named column in B/C1/C4 order",
            "rows": "Invocations; Columns/group; Work organization after preparation; note verbatim"}

    if n == "2":
        rr = []
        for i, (profile, cases, objects) in enumerate(r):
            if i in (0, 5):
                if i: rr.append(MID)
                rr.append(band(2, "Confirmation studies" if i else "Original path qualifications"))
            elif i: rr.append(GAP)
            rr.append(row(record(profile, cases), objects))
        return wrap(grid(p(.43)+X, [row("Bound path and exercised cases", "Object and observation boundary")], rr),
                    note, note_tag="Coverage"), {
            "left": "Bound profile + Exercised cases on consecutive lines, in original order",
            "right": "Observation boundary, unchanged; split before the two confirmation rows",
            "scope": "original note retains absent width/tail cases and all qualification limits"}

    if n == "3":
        h = [row("Study profile", "Target / draft", "Placement and execution settings")]
        rr = []
        def entry(i, prefix):
            a = r[i]
            return row(a[0].removeprefix(prefix+" ").capitalize() if a[0].endswith(("modern", "formal", "pilot"))
                       else a[0].removeprefix(prefix+" "), a[1], a[2])
        rr.extend([band(3, e["device_a"]+" / CUDA"), entry(0, "A5000"), GAP, entry(2, "A5000"), GAP])
        conf = r[3]
        # The baseline co-locates two disjoint configurations in a single row.
        label_a, label_b = conf[0].removeprefix("A5000 ").split(" / ")
        a, b = conf[1].removeprefix("A: ").split(". B: ")
        sa, sb = conf[2].removeprefix("A: ").split(". B: ")
        rr += [row("Confirmation A", a, sa+"."), GAP, row("Confirmation "+label_b, b, sb),
               MID, band(3, e["device_r"]+" / CUDA"),
               row(r[1][0].removeprefix("RTX ").capitalize(), e["rtx_models"], r[1][2]),
               MID, band(3, e["device_b"]+" / Vulkan"), entry(4, "B570"), GAP, entry(5, "B570")]
        return wrap(grid(p(.16)+p(.27)+X, h, rr), note, note_tag="Common settings"), {
            "panel": "hardware name from frozen deployment register; backend from baseline/register",
            "study / target–draft / settings": "map original rows 1,3,4A,4B,2,5,6 into three device panels; "
              "split the A/B model AND settings at the same A:/B: source markers; no duplicated study",
            "RTX model": "full model names and both Q8_0 precisions from the same deployment register row",
            "limits": "original common settings and NR definition retained; M1 layer placement stays NR"}

    if n == "4":
        h = [row("Study", "Sampling", "Arms", "Input", "Output", "Meas.")]
        rr = []
        for title, inds in [
                ("Selected transactions / verify through commit", [5, 7]),
                ("Independent CUDA requests / reset through final synchronization", [0, 1, 2, 3, 4]),
                ("Natural service / native-service clock", [6]),
                ("Natural service / two-turn response plus reset", [8]),
                ("Vulkan service / compute plus normal teardown", [9, 10])]:
            if rr: rr.append(MID)
            rr.append(band(6, title))
            for i in inds:
                a = r[i]
                rr.append(row(*a))
        units = ("Input is prompt tokens (history tokens for transactions); output is generated tokens "
                 "(requested rows for transactions). Sampling is roots $\\times$ repeats unless annotated. "
                 "Meas. counts formal arm observations; warmup and qualification are excluded. ")
        # Every original clock is now named on the corresponding in-table panel.
        note = units + note.split(" CUDA C4/P4", 1)[0] + " NR: unreported visible output range."
        return wrap(grid(p(.197)+"l"+X+"rrr", h, rr), note, pad="3.0", note_tag="Units"), {
            "panels": "clock and unit class moved from source caption/footnote and sections/design.tex §Measurement boundaries to matching rows",
            "fields": "Study / Roots × repetitions / Arms / Input / Output / Measured from source columns 1…6, unchanged values",
            "order": "source rows 6,8 | 1,2,3,4,5 | 7 | 9 | 10,11; each appears exactly once",
            "eligibility": "all a–d footnote marks and conditional scope (history lengths, dependent successors, blocks, EOG, prompts, balanced domains) retained"}

    if n == "5":
        h = [row("Projection", span(2, "Native service total (s)"), span(3, r"LOCAL time reduction (\%)")),
             rules((2, 3), (4, 6)), row("organization", "WHOLE", "LOCAL", "Estimate", r"99\% low", r"99\% high")]
        # Source has a header between the two matrices; join by projection, not by looking at the displayed time.
        rr = []
        for a in r[:2]:
            effect = next(t for t in r if t[0] == a[0]+" held fixed")
            rr.append(row(a[0], a[1], a[2], effect[1], *bounds(effect[2])))
        rr += [MID, row(span(6, r"\textbf{Verification calls removed:} "+num(e["removed"])+
                 " per "+num(e["cycles_fmt"])+r" logical cycles ("+e["opportunity"]+r"\%) per arm.", "@{}l")),
               row(span(6, "Physical calls: WHOLE "+num(e["whole_fmt"])+", LOCAL "+num(e["local_fmt"])+".", "@{}l"))]
        note = note[note.index("Reductions use"):]
        return wrap(grid(X+"rrrrr", h, rr), note, note_tag="Estimator"), {
            "time and effect per projection": "join baseline upper 2×2 and lower direct reductions by loop4/packed; split interval at comma; 3/4 decimal places retained",
            "opportunity strip": "sum verify_physical_width_hist values by arm and subtract LOCAL from WHOLE; denominator = logical cycles per arm, not measured requests or all target calls",
            "note": "baseline estimator/policy language retained; call counts moved from note into ruled body"}

    if n == "6":
        h = [row("Endpoint", "Role", span(3, r"Time reduction (\%)"), span(2, "Physical target calls")),
             rules((3, 5), (6, 7)), row("", "", "Estimate", r"95\% low", r"95\% high", "SIMPLE", "LOCAL")]
        rr = []
        for i, a in enumerate(r):
            if i == 1: rr.append(MID)
            calls = ("---", "---") if not i else e["calls"][f"C{i-1}"]
            label = a[0] if not i else f"{a[0]} (C{i-1})"
            rr.append(row(label, a[1], a[2], *bounds(a[3]), *calls))
        note = ("All endpoints use "+num(r[0][4])+" paired time blocks. Calls are outer target invocations "
                "per two-turn episode, not per-layer projections or GPU kernels; "
                "target rows under either arm: C0, "+num(e["target_rows"]["C0"])+"; C1, "+
                num(e["target_rows"]["C1"])+". Dashes: no physical call count for a statistical aggregate. "+note)
        return wrap(grid(X+"lrrrrr", h, rr), note, pad="3.0", note_tag="Units"), {
            "endpoints / effects": "baseline columns 1–4; split percent interval into endpoints; move common Blocks value into first note sentence",
            "calls": "observed_partitions.B/{C0,C1}/{W,L}.physical_projection_calls is the saved alias of native dispatch.physical_calls; W→SIMPLE and L→LOCAL. These are outer target invocations per episode; sum the width histogram for calls and sum(width × frequency) for rows.",
            "rows": "physical_rows checked against sum(width × frequency) per episode; equal across arms. No pooled call count for overall."}

    if n == "7":
        rr = []
        for i, a in enumerate(r):
            if i: rr.append(MID if i == len(r)-1 else GAP)
            rr.append(row(record(a[0].replace(r"\newline", "~"), a[1]), a[2], a[3]))
        return wrap(grid(p(.31)+p(.32)+X,
                         [row("System and fixed reference", "What may vary", "State and consumer")], rr),
                    "", pad="4.0"), {
            "left": "combine Work (with original citation) and Reference/invariant; only replace forced citation wrap in BlockLock",
            "middle/right": "Retained execution freedom and State/consumer connection, verbatim; source order maintained, final construction divided by rule"}

    if n == "S1":
        h = [row("Repeat", span(3, "Noncrossing"), span(3, "Crossing")),
             rules((2, 4), (5, 7)), row("", "SIMPLE (ms)", "LOCAL (ms)", "L/S", "SIMPLE (ms)", "LOCAL (ms)", "L/S")]
        rr = []
        for step in ["First", "Successor"]:
            ss = [a for a in r if a[1] == step]
            cap = [next(a[2] for a in ss if a[0]==g) for g in ("Within block", "Crossing")]
            if rr: rr.append(MID)
            rr.append(band(7, ("First transaction" if step=="First" else "Dependent successor") +
                           " / history bases "+cap[0]+" (noncrossing), "+cap[1]+" (crossing)"))
            for rep in sorted({a[3] for a in ss}):
                vals = [next(a for a in ss if a[3]==rep and a[0]==g)[4:] for g in ("Within block", "Crossing")]
                rr.append(row(rep, *vals[0], *vals[1]))
        return wrap(grid("lrrrrrr", h, rr), note, pad="3.0"), {
            "pivot": "source Transaction→panel, Geometry→column triplet, Base→panel label, Rep.→row; SIMPLE/LOCAL milliseconds + ratio each appear once per pair"}

    if n == "S2":
        h = [row("Profiler output", span(2, "Noncrossing / base "+e["within"]), span(2, "Crossing / base "+e["cross"])),
             rules((2, 3), (4, 5)), row("", "SIMPLE", "LOCAL", "SIMPLE", "LOCAL")]
        rr = [band(5, "Event counts")]
        for i, a in enumerate(r):
            if i == 4: rr.extend([MID, band(5, "Device-event duration (ms)")])
            rr.append(row(a[0].removesuffix(" (ms)"), *a[1:]))
        return wrap(grid(X+"rrrr", h, rr), note, note_tag="Clock"), {
            "fields": "same four profiler runs in source order; split counts from event milliseconds at Projection (ms); original zeros and precision retained",
            "labels": "history bases from baseline group headers; memcpy = exported aggregate; note preserved"}

    if n == "S3":
        h = [row("Endpoint", "Role", "Ratio", span(2, r"95\% interval")), rules((4, 5)), row("", "", "", "Lower", "Upper")]
        rr = []
        for i, a in enumerate(r):
            if i in (0, 3):
                if i: rr.append(MID)
                rr.append(band(5, "A / 32B verification through commit" if not i else "B / 8B two-turn response plus reset"))
            key = a[0].removeprefix("32B ").removeprefix("8B ")
            rr.append(row(key[:1].upper()+key[1:], *a[1:]))
        return wrap(grid(X+"lrrr", h, rr), note), {
            "panel": "numerical profile from source endpoint; separate clocks from sections/supplement.tex. Keep six roles and estimates; interaction retains ratio-of-ratios interpretation",
            "columns": "endpoint label / role / ratio / 95% lower / 95% upper; remove only repeated profile prefix"}

    if n in ("S4", "S5"):
        is_a = n == "S4"
        g = ("Noncrossing / "+e["within"], "Crossing / "+e["cross"]) if is_a else ("Conversation 0", "Conversation 1")
        short = ("Noncrossing", "Crossing") if is_a else ("C0", "C1")
        unit = "ms" if is_a else "s"
        h = [row("Block", span(2, g[0]+" ("+unit+")"), span(2, g[1]+" ("+unit+")"), span(2,"LOCAL / SIMPLE")),
             rules((2, 3), (4, 5), (6, 7)), row("", "SIMPLE", "LOCAL", "SIMPLE", "LOCAL", *short)]
        rr = []
        for i, a in enumerate(r):
            if i and i % 4 == 0: rr.append(GAP)
            rr.append(row(*labels(a, (0,1,2,4,5,3,6))))
        note = note.split(" A uses ", 1)[0] + (
            " This 32B study uses the first-transaction verification-through-commit clock and contains 48 formal arm observations."
            if is_a else
            " This 8B study uses the complete two-turn response-plus-reset clock and contains 48 formal arm observations.")
        return wrap(grid("lrrrrrr", h, rr), note), {
            "per time block": "baseline fields [block, S0, L0, L0/S0, S1, L1, L1/S1] → [block, S0, L0, S1, L1, L0/S0, L1/S1]; raw times stay paired; adjacent ratio columns",
            "units": "A = s×1000 to ms; B = s. Ratios computed before rounding, original block order preserved. Notes retain only the current study's clock and 48-observation scope; the neighboring study is defined in its own table."}

    if n in ("S6", "S10"):
        s6 = n == "S6"
        h = [row("Phase", span(2, "LOCAL minus SIMPLE (ms)")) if s6 else row("Phase", span(3,"Candidate minus control (ms)")),
             rules((2,3 if s6 else 4)), row("", "Conversation 0", "Conversation 1") if s6 else row("", "C1 $-$ B", "C4 $-$ C1", "C4 $-$ B")]
        groups = ([("Sampling and controller overhead", [5, 2, 3]), ("Execution, state and request accounting",
                     [0, 1, 4, 6, 7, 8, 9, 10, 11])] if s6 else
                  [("Target work", [1,2,3]), ("Draft work", [4,5,6]), ("Request and host work", [0,7,8,9])])
        assert sorted(k for _, inds in groups for k in inds)==list(range(len(r)-1))
        rr = []
        for title, inds in groups:
            if rr: rr.append(GAP)
            rr.append(band(len(r[0]), title))
            rr.extend(row(*r[i]) for i in inds)
        rr += [MID, row(r"\textbf{"+r[-1][0]+"}", *r[-1][1:])]
        if not s6:
            note = "The C1 minus B column has the opposite sign to Figure~\\ref{fig:c4}(c), which shows B minus C1 savings. " + note
        return wrap(grid(X+"r"*(len(r[0])-1), h, rr), note, note_tag="Clock"), {
            "phase": "groups of original source row numbers: "+str([(t,[k+1 for k in v]) for t,v in groups])+"; complete-account total remains separate",
            "values": "unmodified signed arithmetic mean milliseconds in same candidate-minus-control order; keep +/- signs, including printed signed zeros"}

    if n == "S7":
        h = [row("Candidate / control", "Registered role", "Time ratio", span(2,r"95\% ratio interval"), r"Reduction (\%)"),
             rules((4,5)), row("","","","Lower","Upper","")]
        rr = []
        for i, a in enumerate(r):
            contrast, role = a[0].split(" / ")
            if i == 1: rr.append(MID)
            rr.append(row(contrast, role.capitalize(), a[1], *bounds(a[2]), a[3]))
        return wrap(grid(X+"lrrrr", h, rr), note, pad="3.0"), {
            "fields": "split comparison and role at spaced slash (not contrast slash); split ratio CI into lower/upper; reduction unchanged including negative primary",
            "scope": "new column headers distinguish ratio units from percentage; crossed interval remains the principal one"}

    if n == "S8":
        effects = ["C1/B", "C4/C1", "C4/B"]
        h = [row("Comparison", span(len(r),"Time block in execution order")), rules((2, len(r)+1)),
             row("Time ratio", *[a[0] for a in r])]
        rr = [row(label, *[a[i+1] for a in r]) for i, label in enumerate(effects)]
        return wrap(grid(X+"r"*len(r), h, rr), note, pad="3.0"), {
            "pivot": "Time block→column in original order, C1/B, C4/C1, C4/B→rows; all 18 ratios, including the contrary C1/B block"}

    if n == "S9":
        paths = [a for a in r if a[0].startswith("Code/test/")]
        math = [a for a in r if a[0].startswith("MATH/")]
        assert len(paths)==len(math) and len(r)==len(paths)+len(math)
        h = [row(span(4,"CodeContests / test"), span(4,"MATH / train")), rules((1,4),(5,8)),
             row("ID", "C1/B", "C4/C1", "C4/B", "Category / ID", "C1/B", "C4/C1", "C4/B")]
        rr = []
        for i, (a, b) in enumerate(zip(paths, math)):
            if i and i%4==0: rr.append(GAP)
            name = b[0].removeprefix("MATH/").replace("/train/", " / ")
            rr.append(row(a[0].rsplit("/",1)[1], *a[1:], name, *b[1:]))
        note = "The two lists share column headings, not paired root identities. "+note
        return wrap(grid("lrrr"+r"@{\hspace{9pt}}"+X+"rrr", h, rr), note, size="8.5", leading="10.2", pad="2.5"), {
            "panels": "factor Code/test and MATH/train out of root paths; retain original within-domain order and category/ID; horizontal juxtaposition is not matching",
            "values": "each source root's three ratios contiguous; 24 distinct source rows in two lists of 12"}

    if n == "S11":
        h = [row("Independent study", "Candidate", "Control", "Time ratio", span(2,r"95\% interval")),
             rules((5,6)), row("","","","","Lower","Upper")]
        rr = []
        for i, (study, contrast, ratio, lo, hi) in enumerate(r):
            first = not i or study != r[i-1][0]
            if first and i: rr.append(MID)
            a, b = contrast.split("/")
            rr.append(row(study+(" (initial)" if study=="RTX C4" else "") if first else "", a, b, ratio, lo, hi))
        return wrap(grid(X+"llrrr", h, rr), note, pad="3.2"), {
            "group": "consecutive original study labels (initial RTX clarified); source row count unchanged",
            "contrast": "split Direct contrast at / so every contemporaneous denominator has its own column; ratio and interval retained to six places"}

    if n == "S12":
        h = [row("Request component", span(2,"A5000 studies"), span(2,"RTX studies")),
             rules((2,3),(4,5)), row("Difference (ms)", "C4 $-$ C1", "P4 $-$ C4", "C4 $-$ C1", "P4 $-$ C4")]
        rr = [row(*labels(a,(0,1,3,2,4))) for a in r[:-1]] + [MID,row(*labels(r[-1],(0,1,3,2,4)))]
        note = r"C4 $-$ C1 compares the speculative C4 and C1 arms; P4 $-$ C4 compares SD\_P4 and SD\_C4. "+note
        return wrap(grid(X+"rrrr", h, rr), note), {
            "column order": "re-index source [A5000 C4/C1, RTX C4/C1, A5000 SD_P4/SD_C4, RTX SD_P4/SD_C4] as [1,3,2,4]; header spells subtraction for arithmetic differences",
            "phase and total": "all original component groups, residual and whole-clock total preserved including sign; same-study only"}

    if n == "S13":
        h = [row("Comparison", "Held fixed", "Ratio", span(2,r"99\% interval")), rules((4,5)), row("","","","Lower","Upper")]
        rr = []
        for a in r[:-1]:
            k,c = a[0].split(", ")
            rr.append(row(k,c,*a[1:]))
        rr += [MID,row(r[-1][0],"---",*r[-1][1:])]
        return wrap(grid(X+"lrrr", h, rr), note, note_tag="Family"), {
            "direct": "split original Contrast at comma into varying factor comparison and its conditioning factor",
            "interaction": "separate row; no single factor held fixed; keep ratio and endpoints to eight decimals"}

    if n == "S14":
        h = [row("Training root", span(3,"loop4"), span(3,"packed")), rules((2,4),(5,7)),
             row("Category / ID", "WHOLE (s)", "LOCAL (s)", "L/W", "WHOLE (s)", "LOCAL (s)", "L/W")]
        rr = []
        for i,a in enumerate(r):
            domain, name = a[0].split(" / ",1)
            if not i or domain!=r[i-1][0].split(" / ",1)[0]:
                if rr: rr.append(MID)
                rr.append(band(7, domain+" / train"))
            rr.append(row(name, *labels(a,(1,2,5,3,4,6))))
        return wrap(grid(X+"rrrrrr", h, rr), note, size="8.7", leading="10.5", pad="2.8"), {
            "root": "factor APPS or MATH and common train split into panel heading; keep category + ID and all 16 cases",
            "arm values": "source columns 2,3,6 | 4,5,7: put each policy's WHOLE, LOCAL and LOCAL/WHOLE together; no recomputation from rounded time"}

    if n == "S15":
        h = [row("Fixed historical panel", *[a[0] for a in r])]
        rr = [row("Unit and clock", *[a[1] for a in r]), MID, row("LOCAL / WHOLE", *[a[2] for a in r]),
              row("Cost or estimator", *[a[3] for a in r])]
        return wrap(grid(p(.235)+X+X, h, rr), note), {
            "pivot": "Profile→column; Unit and clock, L/W, Cost observation→rows; retain distinct clocks and original estimators",
            "note": "original episode/call/cost breakdown and explicit no-population-interval retained"}

    if n == "S16":
        h = [row("Study or record set", "Measured", "Warm / primer", "Other", "Ledger rows")]
        rr = []
        for group, inds in [("RTX and A5000 request ledgers", range(6)),("B570 timing tables", (6,7)),
                            ("Reservations and native receipts",(8,9))]:
            if rr: rr.append(MID)
            rr.append(band(5, group))
            rr.extend(row(*labels(r[i],(0,2,3,4,1))) for i in inds)
        return wrap(grid(X+"rrrr",h,rr), note, note_tag="Role definitions"), {
            "columns": "Study / Measured / Warm or primer / Other roles / Ledger rows; total moved last; each original ledger appears once",
            "groups and status": "separate timing-table scopes and reservations/receipts; keep original resource exclusions, technical replacements and failed-checker note"}

    if n == "S17":
        rr = []
        for a in r:
            if rr: rr.append(MID)
            rr.extend([band(2, a[0]), row(a[1],a[2])])
        return wrap(grid(p(.43)+X,[row("Complete numerical objects", "Exact coverage and unavailable objects")],rr),
                    note, note_tag="Access"), {
            "panel": "original Evidence layer→row-group title; Complete numerical objects and Exact coverage become two wide cells",
            "missing/aliases": "keep original crossing-KV absence, invalid B frontier, alias/deduplication counts; no replay implied"}

    if n == "S18":
        h = [row("Complete-service contrast", "Code root", "Math root", "Geometric ratio")]
        top = grid(X+"rrr",h,[row(*a) for a in r[:3]])
        rr = []
        for name, multi in r[3:]:
            v = re.fullmatch(r"\\multicolumn\{3\}\{r@\{\}\}\{([^}]+)\}",multi)
            assert v, multi
            rr.append(row(name, v[1]))
        bottom = grid(X+"r",[row("Pilot-only arithmetic stage account", "Mean (s)")], rr)
        return wrap(top+r"\par\smallskip\noindent"+"\n"+bottom, note), {
            "upper": "source first three pilot contrasts, their two root ratios and geometric mean",
            "lower": "unwrap baseline multicolumn for each of the final two original stage means (s), separate native grid; not a ratio or additive decomposition"}

    if n == "S19":
        deployments = list(dict.fromkeys(a[0] for a in r))
        blocks = {d:{a[2] for a in r if a[0]==d} for d in deployments}
        assert all(len(v)==1 for v in blocks.values())
        names = [d.replace("target only","target-only") for d in deployments]
        h = [row("Width", *[span(2, d) for d in names]), rules((2,3),(4,5),(6,7)),
             row("$q$",*[span(2,next(iter(blocks[d]))+" blocks") for d in deployments]),
             row("", *(["Crossing","Inside"]*3))]
        rr = []
        cells = {(a[0],a[1]):a[3:] for a in r}
        for q in sorted({a[1] for a in r}, key=int):
            rr.append(row(q, *[v for d in deployments for v in cells.get((d,q),("NM","NM"))]))
        return wrap(grid("lrrrrrr",h,rr), "All entries are LOCAL/WHOLE time ratios. NM: not measured. "+note,
                    size="8.7", leading="10.5", pad="2.8"), {
            "pivot": "q→row; deployment→two-column group with its recorded block count; original Crossing L/W and Inside L/W from each of 14 measured cells",
            "missing": "outer join of actually exercised q values. Smol q4 is explicitly unmeasured (NM), never zero or interpolated"}

    if n == "S20":
        h = [row("Profile","Roots",span(3,"Resident L-P-D4 / fastest M"),span(3,"Worker lifetime (s)")), rules((3,5),(6,8)),
             row("","","Ratio",r"99\% low",r"99\% high","Fastest M","L-P-D4",r"$\Delta$")]
        rr = [row(a[0],a[1],a[2],*bounds(a[3]),a[4],a[5],v) for a,v in zip(r,e["worker_delta"])]
        return wrap(grid(X+"rrrrrrr",h,rr), r"Worker $\Delta$ is L-P-D4 minus its fastest measured M; positive adds time. "+note,
                    size="8.5",pad="2.6"), {
            "resident": "source roots, ratio and family CI endpoints; matched to fastest resident control (no cross-lifetime denominator)",
            "worker": "two source process totals in seconds; new signed Δ from recorded process_s values at their available precision, not from resident ratios",
            "limits": "original order confounding, slower roots, four sessions/root and worker/resident scope retained"}
    raise KeyError(n)
