"""Generate CIV-Bench v2: whole-person, longitudinal clinical+social safety invariants.

Eight domains. Medical spine: triage/partial-context (missing-data-not-reassuring monotonicity),
medication safety (contraindicated-pair mutual exclusion + no-rule-chain-re-enables-a-disabled-guard),
workup completeness (omission), differential breadth (omission). Social/behavioral wedge:
mental health (self-harm escalation never suppressed + persists), social needs/SDOH (documented need
never dropped), trust/preference (never silently overridden + persists across episodes), substance
use (MOUD continuity + contraindicated co-prescription).

Decision domains are graded by interaction depth (conditions that must conjoin); transition-system
(longitudinal) domains are graded by episode depth (encounters a violation must span). Ground truth
is the solver-independent oracle in verifier.execute; every violation witness is replay-confirmed
and the SMT verifier is cross-checked to agree. Items are synthetic and physician-authored in form;
the domain taxonomy follows goal categories used in operational care-management systems.
Deterministic: seeds derive from a stable sha256.

    python benchmark/generate_v2.py [--check]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

from jsonschema import Draft202012Validator

from verifier.execute import oracle
from verifier.model import Item
from verifier.replay import confirm_witness
from verifier.smt import verify

ROOT = Path(__file__).resolve().parent.parent
SUITE = ROOT / "benchmark" / "suite_v2"
ITEM_SCHEMA = json.loads((ROOT / "benchmark" / "schema" / "benchmark.schema.json").read_text())
ACUITY = ["self_care", "routine", "urgent", "emergent"]
DEC_DEPTHS = [1, 2, 3, 4]
EP_DEPTHS = [1, 2, 4, 6]


def _seed(*p):
    return int(hashlib.sha256("-".join(map(str, p)).encode()).hexdigest(), 16) % (2**32)


def _and(names):
    return {"var": names[0]} if len(names) == 1 else {"op": "and", "args": [{"var": n} for n in names]}


def _meta(desc, intent):
    return {"description": desc, "source": "synthetic", "clinical_intent": intent}


# --------------------------------------------------------------------------- medical spine

def triage_missingdata(depth, seed, holds):
    """Missing-data-not-reassuring: marking the vitals unknown must never LOWER acuity.

    Encoded as monotonicity: set_true on vitals_unknown is non-acuity-lowering. A violated item has
    a rule that, when vitals are unknown and depth-1 distractors hold, defers to a low-acuity
    disposition (treating missing data as reassuring); the holds variant treats any unknown vitals as
    worst-case (emergent)."""
    rng = random.Random(_seed("triage_md", depth, seed, holds))
    distract = rng.sample(["fever", "rash", "cough", "headache", "nausea"], max(0, depth - 1))
    inputs = [{"name": "vitals_unknown", "type": "bool"}, {"name": "concerning_symptom", "type": "bool"}]
    inputs += [{"name": d, "type": "bool"} for d in distract]
    rules = [{"id": "concerning_urgent", "priority": 10, "when": {"var": "concerning_symptom"},
              "then": [{"var": "acuity", "value": "urgent"}]}]
    if not holds:  # missing data treated as reassuring -> defers care (the unsafe pattern)
        rules.append({"id": "unknown_defers", "priority": 50, "when": _and(["vitals_unknown"] + distract),
                      "then": [{"var": "acuity", "value": "self_care"}]})
    else:  # missing vitals treated as worst-case
        rules.append({"id": "unknown_worstcase", "priority": 50, "when": {"var": "vitals_unknown"},
                      "then": [{"var": "acuity", "value": "emergent"}]})
    return {"id": f"triagepartial-d{depth}-{'hold' if holds else 'viol'}-{seed:02d}", "domain": "triage_partial",
            "metadata": _meta("partial-context triage; missing critical data must not be reassuring",
                              "marking the vitals unknown never lowers the assigned acuity"),
            "ruleset": {"id": f"tmd-{depth}-{seed}", "kind": "decision", "inputs": inputs,
                        "outputs": [{"name": "acuity", "type": "enum", "domain": ACUITY}],
                        "rules": rules, "default": [{"var": "acuity", "value": "routine"}],
                        "conflict_resolution": "priority"},
            "property": {"id": "missing-data-not-reassuring", "kind": "monotonicity",
                         "monotonicity": {"perturbation": {"var": "vitals_unknown", "change": "set_true"},
                                          "monotone_var": "acuity", "direction": "nondecreasing"},
                         "intent": "setting vitals_unknown true never lowers acuity"}}


def medication_reenable(depth, seed, holds):
    """No rule chain re-enables a contraindicated drug that a safety guard disabled."""
    rng = random.Random(_seed("med_re", depth, seed, holds))
    conds = rng.sample(["anticoagulated", "ckd", "elderly", "peptic_ulcer", "heart_failure", "hepatic"], depth)
    inputs = [{"name": "anticoagulated", "type": "bool"}] + [{"name": c, "type": "bool"} for c in conds if c != "anticoagulated"]
    names = [v["name"] for v in inputs]
    rules = [{"id": "guard_suppress_nsaid", "priority": 90, "when": {"var": "anticoagulated"},
              "then": [{"var": "rec_nsaid", "value": False}]}]
    if not holds:  # higher-priority rule re-enables the contraindicated drug
        rules.append({"id": "enable_nsaid", "priority": 100, "when": _and(names),
                      "then": [{"var": "rec_nsaid", "value": True}]})
    else:
        rules.append({"id": "enable_nsaid", "priority": 80, "when": _and(names),
                      "then": [{"var": "rec_nsaid", "value": True}]})  # guard (90) dominates -> safe
    return {"id": f"medreenable-d{depth}-{'hold' if holds else 'viol'}-{seed:02d}", "domain": "medication",
            "metadata": _meta("medication safety; no rule re-enables a contraindication a guard disabled",
                              "no input recommends an NSAID for an anticoagulated patient"),
            "ruleset": {"id": f"mre-{depth}-{seed}", "kind": "decision", "inputs": inputs,
                        "outputs": [{"name": "rec_nsaid", "type": "bool"}], "rules": rules,
                        "default": [{"var": "rec_nsaid", "value": False}], "conflict_resolution": "priority"},
            "property": {"id": "no-contraindicated-nsaid", "kind": "invariant",
                         "formula": {"op": "not", "args": [{"op": "and", "args": [{"var": "anticoagulated"}, {"var": "rec_nsaid"}]}]},
                         "intent": "rec_nsaid is never true for an anticoagulated patient"}}


def workup_completeness(depth, seed, holds):
    """Omission: a sentinel presentation must include the mandatory workup element."""
    rng = random.Random(_seed("workup", depth, seed, holds))
    conds = rng.sample(["neonate", "fever", "lethargy", "poor_feeding", "irritable", "petechiae"], depth)
    inputs = [{"name": c, "type": "bool"} for c in conds]
    rules = [{"id": "order_sepsis_workup", "priority": 50, "when": _and(conds),
              "then": [{"var": "full_sepsis_workup", "value": True}]}]
    if not holds:  # a higher-priority rule cancels the mandatory workup (omission)
        rules.append({"id": "defer_workup", "priority": 90, "when": _and(conds),
                      "then": [{"var": "full_sepsis_workup", "value": False}]})
    return {"id": f"workup-d{depth}-{'hold' if holds else 'viol'}-{seed:02d}", "domain": "workup_completeness",
            "metadata": _meta("workup completeness; mandatory workup for a sentinel presentation is not omitted",
                              "a neonate-fever sentinel presentation must order the full sepsis workup"),
            "ruleset": {"id": f"wk-{depth}-{seed}", "kind": "decision", "inputs": inputs,
                        "outputs": [{"name": "full_sepsis_workup", "type": "bool"}], "rules": rules,
                        "default": [{"var": "full_sepsis_workup", "value": False}], "conflict_resolution": "priority"},
            "property": {"id": "mandatory-workup-not-omitted", "kind": "invariant",
                         "formula": {"op": "implies", "args": [_and(conds), {"var": "full_sepsis_workup"}]},
                         "intent": "when the sentinel antecedents hold, the mandatory workup is ordered"}}


def differential_breadth(depth, seed, holds):
    """Omission: red-flag features must keep the can't-miss differential in the output set."""
    rng = random.Random(_seed("ddx", depth, seed, holds))
    flags = rng.sample(["tearing_chest_pain", "pulse_deficit", "widened_mediastinum", "hypertension", "syncope"], depth)
    inputs = [{"name": f, "type": "bool"} for f in flags]
    rules = [{"id": "include_dissection", "priority": 50, "when": _and(flags),
              "then": [{"var": "ddx_aortic_dissection", "value": True}]}]
    if not holds:  # narrowing rule drops the can't-miss differential
        rules.append({"id": "narrow_to_acs", "priority": 90, "when": _and(flags),
                      "then": [{"var": "ddx_aortic_dissection", "value": False}]})
    return {"id": f"ddx-d{depth}-{'hold' if holds else 'viol'}-{seed:02d}", "domain": "differential_breadth",
            "metadata": _meta("differential breadth; a can't-miss differential is not omitted under red flags",
                              "with dissection red flags present, aortic dissection stays in the differential"),
            "ruleset": {"id": f"dx-{depth}-{seed}", "kind": "decision", "inputs": inputs,
                        "outputs": [{"name": "ddx_aortic_dissection", "type": "bool"}], "rules": rules,
                        "default": [{"var": "ddx_aortic_dissection", "value": False}], "conflict_resolution": "priority"},
            "property": {"id": "cant-miss-differential-not-omitted", "kind": "invariant",
                         "formula": {"op": "implies", "args": [_and(flags), {"var": "ddx_aortic_dissection"}]},
                         "intent": "when red-flag antecedents hold, the can't-miss differential is present"}}


# --------------------------------------------------------------------------- social/behavioral wedge

def mental_health_suppress(depth, seed, holds):
    """Never-suppressed: a self-harm flag must force escalation, never out-ranked by a generic rule."""
    rng = random.Random(_seed("mh", depth, seed, holds))
    generic = rng.sample(["food_need", "housing_need", "transport_need", "med_refill", "appt_reminder"], depth)
    inputs = [{"name": "self_harm_flag", "type": "bool"}] + [{"name": g, "type": "bool"} for g in generic]
    rules = [{"id": "escalate_self_harm", "priority": 50, "when": {"var": "self_harm_flag"},
              "then": [{"var": "escalate", "value": True}]}]
    if not holds:  # a generic task outranks and suppresses the escalation
        rules.append({"id": "generic_outranks", "priority": 100, "when": _and(generic),
                      "then": [{"var": "escalate", "value": False}]})
    else:
        rules.append({"id": "generic_action", "priority": 10, "when": _and(generic),
                      "then": [{"var": "escalate", "value": True}]})  # safety-critical kept top
    return {"id": f"mentalhealth-d{depth}-{'hold' if holds else 'viol'}-{seed:02d}", "domain": "mental_health",
            "metadata": _meta("mental health; a self-harm flag is never suppressed or out-ranked",
                              "a self-harm indicator must always escalate, never deprioritized by a generic task"),
            "ruleset": {"id": f"mh-{depth}-{seed}", "kind": "decision", "inputs": inputs,
                        "outputs": [{"name": "escalate", "type": "bool"}], "rules": rules,
                        "default": [{"var": "escalate", "value": False}], "conflict_resolution": "priority"},
            "property": {"id": "self-harm-always-escalates", "kind": "invariant",
                         "formula": {"op": "implies", "args": [{"var": "self_harm_flag"}, {"var": "escalate"}]},
                         "intent": "self_harm_flag true implies escalate true for every input"}}


def trust_preference(depth, seed, holds):
    """No silent override: a declined treatment is not recommended unless a conflict is flagged."""
    rng = random.Random(_seed("trust", depth, seed, holds))
    drivers = rng.sample(["guideline_indicated", "risk_high", "pcp_request", "quality_gap", "overdue"], depth)
    inputs = [{"name": "patient_declines_x", "type": "bool"}] + [{"name": d, "type": "bool"} for d in drivers]
    rules = [{"id": "suppress_on_decline", "priority": 90, "when": {"var": "patient_declines_x"},
              "then": [{"var": "recommend_x", "value": False}]}]
    if not holds:  # a guideline rule silently overrides the stated preference
        rules.append({"id": "guideline_override", "priority": 100, "when": _and(drivers),
                      "then": [{"var": "recommend_x", "value": True}]})
    else:
        rules.append({"id": "guideline_suggest", "priority": 50, "when": _and(drivers),
                      "then": [{"var": "recommend_x", "value": True}]})  # decline guard (90) dominates
    return {"id": f"trust-d{depth}-{'hold' if holds else 'viol'}-{seed:02d}", "domain": "trust_preference",
            "metadata": _meta("trust/preference; a declined treatment is never silently recommended",
                              "if the patient declines treatment x, the system does not recommend x"),
            "ruleset": {"id": f"tr-{depth}-{seed}", "kind": "decision", "inputs": inputs,
                        "outputs": [{"name": "recommend_x", "type": "bool"}], "rules": rules,
                        "default": [{"var": "recommend_x", "value": False}], "conflict_resolution": "priority"},
            "property": {"id": "declined-not-recommended", "kind": "invariant",
                         "formula": {"op": "not", "args": [{"op": "and", "args": [{"var": "patient_declines_x"}, {"var": "recommend_x"}]}]},
                         "intent": "recommend_x is never true when the patient declines x"}}


def substance_mx(depth, seed, holds):
    """Contraindicated co-prescription: OUD patient never co-recommended a contraindicated agent."""
    rng = random.Random(_seed("sud_mx", depth, seed, holds))
    conds = rng.sample(["chronic_pain", "anxiety", "insomnia", "post_surgical", "elderly"], depth)
    inputs = [{"name": "active_oud", "type": "bool"}] + [{"name": c, "type": "bool"} for c in conds]
    rules = [{"id": "rec_moud", "priority": 50, "when": {"var": "active_oud"}, "then": [{"var": "rec_moud", "value": True}]},
             {"id": "rec_benzo", "priority": 50, "when": _and([v["name"] for v in inputs]), "then": [{"var": "rec_benzo", "value": True}]}]
    if holds:  # guard suppresses the contraindicated benzo whenever MOUD context holds
        rules.append({"id": "guard_no_benzo_with_moud", "priority": 90, "when": {"var": "active_oud"},
                      "then": [{"var": "rec_benzo", "value": False}]})
    return {"id": f"substance-d{depth}-{'hold' if holds else 'viol'}-{seed:02d}", "domain": "substance_use",
            "metadata": _meta("substance use; a contraindicated sedative is not co-recommended with MOUD",
                              "a patient on MOUD for OUD is never co-recommended a benzodiazepine"),
            "ruleset": {"id": f"su-{depth}-{seed}", "kind": "decision", "inputs": inputs,
                        "outputs": [{"name": "rec_moud", "type": "bool"}, {"name": "rec_benzo", "type": "bool"}],
                        "rules": rules,
                        "default": [{"var": "rec_moud", "value": False}, {"var": "rec_benzo", "value": False}],
                        "conflict_resolution": "priority"},
            "property": {"id": "no-benzo-with-moud", "kind": "mutual_exclusion",
                         "mutual_exclusion": {"pairs": [[{"var": "rec_moud"}, {"var": "rec_benzo"}]]},
                         "intent": "no input recommends both MOUD and a benzodiazepine"}}


# --------------------------- longitudinal (transition systems, graded by episode depth)

def _obligation_ts(domain, length, seed, holds, name, intent, drop_event="purge"):
    """Generic 'obligation never dropped before resolution' over a chain of `length` encounters."""
    # state: documented, resolved, open, ticks(0..length)
    transitions = [
        {"id": "t_open", "event": "open", "update": [{"var": "documented", "expr": {"const": True}}, {"var": "open", "expr": {"const": True}}]},
        {"id": "t_resolve", "event": "resolve", "guard": {"var": "open"},
         "update": [{"var": "resolved", "expr": {"const": True}}, {"var": "open", "expr": {"const": False}}]},
        {"id": "t_touch", "event": "encounter",
         "update": [{"var": "ticks", "expr": {"op": "ite", "args": [{"op": "lt", "args": [{"var": "ticks"}, {"const": length}]},
                    {"op": "add", "args": [{"var": "ticks"}, {"const": 1}]}, {"var": "ticks"}]}}]},
    ]
    if not holds:  # faulty path drops the open obligation (only after `length` encounters) without resolution
        transitions.append({"id": "t_drop", "event": drop_event,
                            "guard": {"op": "ge", "args": [{"var": "ticks"}, {"const": length}]},
                            "update": [{"var": "open", "expr": {"const": False}}]})
    slug = domain.replace("_", "")
    return {"id": f"{slug}-len{length:02d}-{'hold' if holds else 'viol'}-{seed:02d}", "domain": domain,
            "metadata": _meta(name, intent),
            "ruleset": {"id": f"{slug}-{length}-{seed}", "kind": "transition_system",
                        "state_vars": [{"name": "documented", "type": "bool"}, {"name": "resolved", "type": "bool"},
                                       {"name": "open", "type": "bool"}, {"name": "ticks", "type": "int", "bounds": [0, length]}],
                        "events": [{"name": "open"}, {"name": "resolve"}, {"name": "encounter"}, {"name": drop_event}],
                        "init": [{"var": "documented", "value": False}, {"var": "resolved", "value": False},
                                 {"var": "open", "value": False}, {"var": "ticks", "value": 0}],
                        "transitions": transitions},
            "property": {"id": "obligation-not-dropped", "kind": "temporal",
                         "formula": {"op": "G", "args": [{"op": "implies", "args": [
                             {"op": "and", "args": [{"var": "documented"}, {"op": "not", "args": [{"var": "resolved"}]}]},
                             {"var": "open"}]}]},
                         "bound": length + 3,
                         "intent": "in every reachable state, a documented unresolved obligation is still open"}}


def sdoh_drop(length, seed, holds):
    return _obligation_ts("social_needs", length, seed, holds,
                          "social needs; a documented unmet need is not dropped before resolution over visits",
                          "a documented social need stays an open obligation across encounters until resolved")


def moud_continuity(length, seed, holds):
    return _obligation_ts("substance_use_moud", length, seed, holds,
                          "substance use; MOUD is not discontinued without taper/handoff over visits",
                          "once started, MOUD continuity is maintained across encounters unless properly resolved",
                          drop_event="discontinue")


def mh_persist(length, seed, holds):
    return _obligation_ts("mental_health_persist", length, seed, holds,
                          "mental health; an open self-harm escalation persists across visits until disposition",
                          "a self-harm escalation stays open across encounters until a clinician disposition",
                          drop_event="auto_close")


def trust_persist(length, seed, holds):
    return _obligation_ts("trust_preference_persist", length, seed, holds,
                          "trust/preference; a stated preference persists across visits until the patient rescinds",
                          "a documented patient preference persists across encounters until a patient-originated rescind",
                          drop_event="silent_reset")


# --------------------------------------------------------------------------- build

DECISION_GENS = [triage_missingdata, medication_reenable, workup_completeness, differential_breadth,
                 mental_health_suppress, trust_preference, substance_mx]
TRANSITION_GENS = [sdoh_drop, moud_continuity, mh_persist, trust_persist]


def build_all():
    out = []
    for gen in DECISION_GENS:
        for depth in DEC_DEPTHS:
            for seed in range(2):
                out.append(gen(depth, seed, holds=False))
            out.append(gen(depth, 100, holds=True))
    for gen in TRANSITION_GENS:
        for length in EP_DEPTHS:
            for seed in range(2):
                out.append(gen(length, seed, holds=False))
            out.append(gen(length, 100, holds=True))
    return out


def main(check_only):
    validator = Draft202012Validator(ITEM_SCHEMA)
    manifest, problems = [], 0
    if not check_only:
        (SUITE / "items").mkdir(parents=True, exist_ok=True)
        (SUITE / "answer_key").mkdir(parents=True, exist_ok=True)
    for raw in build_all():
        errs = list(validator.iter_errors(raw))
        if errs:
            problems += 1; print(f"SCHEMA FAIL {raw['id']}: {errs[0].message}"); continue
        item = Item.from_dict(raw)
        intended_viol = raw["id"].split("-")[-2] == "viol"
        truth = oracle(item)
        if (truth["ground_truth"] == "violated") != intended_viol:
            problems += 1; print(f"INTENT FAIL {raw['id']}: oracle={truth['ground_truth']} intended_viol={intended_viol}"); continue
        if truth["ground_truth"] == "violated" and not confirm_witness(item, truth["witness"]):
            problems += 1; print(f"REPLAY FAIL {raw['id']}"); continue
        if verify(item).status != truth["ground_truth"]:
            problems += 1; print(f"VERIFIER DISAGREE {raw['id']}"); continue
        depth_tok = raw["id"].split("-")[1]
        depth = int(depth_tok[1:]) if depth_tok.startswith("d") else int(depth_tok[3:])
        key = {"item": raw["id"], "ground_truth": truth["ground_truth"], "witness": truth["witness"],
               "seeded": intended_viol, "interaction_depth": depth if intended_viol else 0,
               "basis": "concrete_replay" if intended_viol else "manual_proof"}
        manifest.append({"id": raw["id"], "domain": raw["domain"], "kind": item.ruleset.kind,
                         "ground_truth": truth["ground_truth"], "interaction_depth": key["interaction_depth"]})
        if not check_only:
            (SUITE / "items" / f"{raw['id']}.json").write_text(json.dumps(raw, indent=2) + "\n")
            (SUITE / "answer_key" / f"{raw['id']}.json").write_text(json.dumps(key, indent=2) + "\n")
    if not check_only:
        (SUITE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    from collections import Counter
    dom = Counter(m["domain"] for m in manifest)
    nviol = sum(1 for m in manifest if m["ground_truth"] == "violated")
    print(f"built {len(manifest)} items ({nviol} violated, {len(manifest)-nviol} holds); {problems} problem(s)")
    print("by domain:", dict(dom))
    return 1 if problems else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true")
    raise SystemExit(main(ap.parse_args().check))
