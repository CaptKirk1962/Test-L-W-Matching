# match_demo.py — Life Minus Work • Matching Demo (self-contained)
from __future__ import annotations
import math, itertools, textwrap
from typing import Dict, List, Tuple
import streamlit as st

# -----------------------------
# 1) Domain model & sample data
# -----------------------------
THEMES = ["Identity","Growth","Connection","Peace","Adventure","Contribution"]

# Each profile looks like: {name, email, tz, city, themes{}, strengths[], interests[], energizers[], drainers[], needs[]}
# (In production you'd build this from each person’s Reflection Report + short opt-in form.)
PROFILES: List[Dict] = [
    dict(
        name="Ava", email="ava@example.com", tz="ET", city="NYC",
        themes={"Identity":7,"Growth":6,"Connection":4,"Peace":6,"Adventure":3,"Contribution":5},
        strengths=["calm focus","follow-through","listens"],
        interests=["writing","yoga","city-walks","journaling"],
        energizers=["quiet mornings","finishing things"],
        drainers=["constant meetings","late nights"],
        needs=["accountability","gentle structure"]
    ),
    dict(
        name="Ben", email="ben@example.com", tz="ET", city="NYC",
        themes={"Identity":5,"Growth":7,"Connection":6,"Peace":4,"Adventure":6,"Contribution":3},
        strengths=["starter","social spark","quick learner"],
        interests=["coding","coffee-walks","bouldering","short trips"],
        energizers=["new ideas","pairing"],
        drainers=["long docs"],
        needs=["follow-through","calming cadence"]
    ),
    dict(
        name="Cam", email="cam@example.com", tz="PT", city="SF",
        themes={"Identity":4,"Growth":6,"Connection":3,"Peace":8,"Adventure":2,"Contribution":6},
        strengths=["systems","clarity","steadiness"],
        interests=["reading","photography","museum days","tea"],
        energizers=["clear plan","quiet afternoons"],
        drainers=["context switching"],
        needs=["more play","light social"]
    ),
    dict(
        name="Dia", email="dia@example.com", tz="PT", city="SF",
        themes={"Identity":6,"Growth":5,"Connection":7,"Peace":3,"Adventure":7,"Contribution":4},
        strengths=["initiator","connector","storytelling"],
        interests=["hiking","live music","street markets","sketching"],
        energizers=["new places","spontaneity"],
        drainers=["rigid schedules"],
        needs=["gentle structure","reflection habit"]
    ),
    dict(
        name="Eli", email="eli@example.com", tz="CT", city="Austin",
        themes={"Identity":5,"Growth":5,"Connection":5,"Peace":6,"Adventure":4,"Contribution":7},
        strengths=["teaching","empathy","reliable"],
        interests=["workshops","running","cooking","board games"],
        energizers=["helping","small wins"],
        drainers=["unclear goals"],
        needs=["starter energy","novelty nudge"]
    ),
    dict(
        name="Fin", email="fin@example.com", tz="ET", city="Boston",
        themes={"Identity":8,"Growth":4,"Connection":3,"Peace":7,"Adventure":2,"Contribution":5},
        strengths=["deep work","craft","precision"],
        interests=["writing","long walks","gardens","classical"],
        energizers=["solitude","early mornings"],
        drainers=["noise","slack pings"],
        needs=["light social","gentle stretch"]
    ),
    dict(
        name="Gio", email="gio@example.com", tz="ET", city="Philly",
        themes={"Identity":3,"Growth":7,"Connection":6,"Peace":3,"Adventure":8,"Contribution":4},
        strengths=["courage","openness","play"],
        interests=["food tours","street photography","travel deals","pickup soccer"],
        energizers=["crowds","new scenes"],
        drainers=["routine"],
        needs=["post-adventure reflection","accountability"]
    ),
    dict(
        name="Hana", email="hana@example.com", tz="PT", city="LA",
        themes={"Identity":4,"Growth":6,"Connection":6,"Peace":6,"Adventure":5,"Contribution":5},
        strengths=["translator","warmth","consistency"],
        interests=["co-working","podcasts","pilates","farmers markets"],
        energizers=["shared pace","clear goals"],
        drainers=["overcommitting"],
        needs=["strong start cues"]
    ),
]

# -----------------------------
# 2) Similarity / Complement math
# -----------------------------
def cosine(a: List[float], b: List[float]) -> float:
    num = sum(x*y for x, y in zip(a, b))
    da = math.sqrt(sum(x*x for x in a)); db = math.sqrt(sum(y*y for y in b))
    return 0.0 if da == 0 or db == 0 else num/(da*db)

def jaccard(a: set, b: set) -> float:
    if not a and not b: return 0.0
    return len(a & b) / max(1, len(a | b))

def weight_vec(vec: Dict[str, float], weights: Dict[str, float]) -> List[float]:
    return [vec.get(t, 0.0) * weights.get(t, 0.0) for t in THEMES]

def normalize_w(weights: Dict[str, float]) -> Dict[str, float]:
    s = sum(weights.values()) or 1.0
    return {k: v/s for k, v in weights.items()}

# -----------------------------
# 3) Event presets
# -----------------------------
PRESETS = {
    "Deep Work Sprint (virtual)": dict(
        weights={"Identity":.25,"Peace":.25,"Growth":.25,"Contribution":.15,"Connection":.10,"Adventure":0.0},
        α=0.60, β=0.25, γ=0.00, δ=0.15, virtual=True, use_complement=False,
        rationale="Focus + calm + small progress; pair similar pace and interests."
    ),
    "Micro-Adventure Saturday (in-person)": dict(
        weights={"Adventure":.35,"Connection":.25,"Growth":.20,"Peace":.10,"Identity":.05,"Contribution":.05},
        α=0.55, β=0.20, γ=0.20, δ=0.05, virtual=False, use_complement=True,
        rationale="Energy + connection; allow a little complement to nudge exploration."
    ),
    "Skill-Share (virtual or local)": dict(
        weights={"Contribution":.30,"Growth":.25,"Connection":.20,"Identity":.15,"Peace":.10,"Adventure":0.0},
        α=0.45, β=0.20, γ=0.25, δ=0.10, virtual=True, use_complement=True,
        rationale="Teach & learn; match strengths to needs with some complement."
    ),
}

# -----------------------------
# 4) Compatibility scoring
# -----------------------------
def pair_score(A: Dict, B: Dict, preset: Dict) -> Tuple[float, Dict]:
    W = normalize_w(preset["weights"])
    v = weight_vec(A["themes"], W); w = weight_vec(B["themes"], W)
    sim = cosine(v, w)
    comp = cosine(v, [1-x for x in w]) if preset.get("use_complement") else 0.0
    intr = jaccard(set(A["interests"]), set(B["interests"]))
    str_need = jaccard(set(A.get("strengths", [])), set(B.get("needs", []))) \
             + jaccard(set(B.get("strengths", [])), set(A.get("needs", [])))
    str_need *= 0.5  # symmetrize
    tz_ok = (A["tz"] == B["tz"]) or preset.get("virtual", True)
    penalty = 0.0 if tz_ok else 0.15
    S = preset["α"]*sim + preset["β"]*intr + preset["γ"]*comp + preset["δ"]*str_need - penalty
    S = max(0.0, min(1.0, S))
    info = dict(sim=sim, intr=intr, comp=comp, str_need=str_need, tz_ok=tz_ok)
    return 100.0*round(S, 4), info

def best_pairs(profiles: List[Dict], preset: Dict, top_n: int = 8) -> List[Tuple[Dict, Dict, float, Dict]]:
    pairs = []
    for A, B in itertools.combinations(profiles, 2):
        # if in-person, require same city (simple rule for demo)
        if not preset.get("virtual", True) and A["city"] != B["city"]:
            continue
        score, info = pair_score(A, B, preset)
        pairs.append((A, B, score, info))
    pairs.sort(key=lambda x: x[2], reverse=True)
    return pairs[:top_n]

def best_pods(profiles: List[Dict], preset: Dict, size: int = 3, top_n: int = 5):
    """Greedy triads: start with best pair, add the person that maximizes average pair score."""
    pairs_all = best_pairs(profiles, preset, top_n=999)
    used = set()
    pods = []
    for A, B, score, _ in pairs_all:
        key = tuple(sorted([A["email"], B["email"]]))
        if key in used: 
            continue
        # candidate third
        best_third = None; best_avg = -1.0
        for C in profiles:
            if C is A or C is B: 
                continue
            # City constraint for in-person
            if not preset.get("virtual", True):
                if not (A["city"] == B["city"] == C["city"]):
                    continue
            sAB = score
            sAC, _ = pair_score(A, C, preset)
            sBC, _ = pair_score(B, C, preset)
            avg = (sAB + sAC + sBC) / 3.0
            if avg > best_avg:
                best_avg = avg; best_third = C
        if best_third:
            pods.append((A, B, best_third, round(best_avg, 1)))
            used.add(key)
        if len(pods) >= top_n:
            break
    return pods

def shared_bits(A: Dict, B: Dict):
    ts = list(set(top_n(A["themes"])) & set(top_n(B["themes"])))
    interests = list(set(A["interests"]) & set(B["interests"]))
    return ts, interests

def top_n(themes: Dict[str, float], n: int = 3):
    return [k for k, _ in sorted(themes.items(), key=lambda kv: kv[1], reverse=True)[:n]]

def intro_email(A: Dict, B: Dict, preset_name: str, when_hint: str = "next week"):
    shared_t, shared_i = shared_bits(A, B)
    t_str = ", ".join(shared_t) if shared_t else "matching pace"
    i_str = ", ".join(shared_i[:2]) if shared_i else "overlap in style"
    body = f"""\
    Subject: You two might enjoy a {preset_name}

    Hi {A['name']} & {B['name']},

    Based on your Life Minus Work reflections, you share strong {t_str} and a nice overlap in {i_str}.
    Would you like to try a {preset_name.lower()} together {when_hint}?

    • Suggested format: 5-min hello → 40-min main session → 5-min wrap
    • Tips: start small, keep it kind, finish with one tiny next step

    If you’re in, reply-all with 2–3 time windows. We’ll help you lock it in.

    — Life Minus Work
    """
    return textwrap.dedent(body).strip()

# -----------------------------
# 5) Streamlit UI
# -----------------------------
st.set_page_config(page_title="LMW — Matching Demo", page_icon="🤝", layout="wide")
st.title("Life Minus Work — Matching Demo")
st.caption("Prototype to show how we can pair/pod people for events based on Reflection Reports.")

colL, colR = st.columns([1,1.2], gap="large")

with colL:
    preset_name = st.selectbox("Choose an event preset", list(PRESETS.keys()))
    preset = PRESETS[preset_name]
    st.write(f"**How scoring works for this preset**")
    st.markdown(f"- Weights → {preset['weights']}")
    st.markdown(f"- Mix: α·similarity + β·interests + γ·complement + δ·strength→need")
    st.info(preset["rationale"])

    st.markdown("**People in the pool**")
    for p in PROFILES:
        st.markdown(
            f"- **{p['name']}** · {p['city']} ({p['tz']}) · "
            f"Top: {', '.join(top_n(p['themes']))} · Interests: {', '.join(p['interests'][:3])}"
        )

with colR:
    st.subheader("Top pairs")
    pairs = best_pairs(PROFILES, preset, top_n=6)
    if not pairs:
        st.warning("No eligible pairs for this preset (try a virtual one).")
    for A, B, score, info in pairs:
        with st.container(border=True):
            st.markdown(f"### {A['name']} ↔ {B['name']} — **{score:.1f}**")
            ts, intr = shared_bits(A, B)
            st.markdown(
                f"Shared themes: {', '.join(ts) if ts else '—'}  ·  "
                f"Shared interests: {', '.join(intr) if intr else '—'}"
            )
            st.caption(
                f"sim: {info['sim']:.2f} · interests: {info['intr']:.2f} · "
                f"complement: {info['comp']:.2f} · strengths→needs: {info['str_need']:.2f} · "
                f"timezone_ok: {info['tz_ok']}"
            )
            if st.button(f"Preview intro email: {A['name']} + {B['name']}", key=f"email_{A['email']}_{B['email']}"):
                st.code(intro_email(A, B, preset_name), language="markdown")

    st.subheader("Top pods (triads)")
    pods = best_pods(PROFILES, preset, size=3, top_n=3)
    if not pods:
        st.info("Pods need at least three in the same city for in-person presets.")
    for A, B, C, avg in pods:
        with st.container(border=True):
            st.markdown(f"### {A['name']} + {B['name']} + {C['name']} — **avg {avg:.1f}**")
            cities = {A['city'], B['city'], C['city']}
            st.caption(f"Cities: {', '.join(cities)} · Timezones: {A['tz']}, {B['tz']}, {C['tz']}")
            st.markdown(
                f"- {A['name']} top: {', '.join(top_n(A['themes']))}\n"
                f"- {B['name']} top: {', '.join(top_n(B['themes']))}\n"
                f"- {C['name']} top: {', '.join(top_n(C['themes']))}"
            )

