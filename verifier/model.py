"""Load and represent benchmark items.

A benchmark item is a rule set, a property, and metadata, validating against
benchmark/schema/benchmark.schema.json. This module loads items into light dataclasses
and provides typing helpers shared by the concrete executor and the SMT compiler.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Var:
    name: str
    type: str  # bool | enum | int
    domain: list[str] | None = None  # enum labels, ordered
    bounds: tuple[int, int] | None = None  # int inclusive [min, max]

    @staticmethod
    def from_dict(d: dict) -> "Var":
        return Var(
            name=d["name"],
            type=d["type"],
            domain=list(d["domain"]) if d.get("domain") is not None else None,
            bounds=tuple(d["bounds"]) if d.get("bounds") is not None else None,
        )

    def cardinality(self) -> int:
        if self.type == "bool":
            return 2
        if self.type == "enum":
            return len(self.domain)
        lo, hi = self.bounds
        return hi - lo + 1

    def values(self) -> list:
        """All concrete values, for enumeration. Enums as labels, ints as ints."""
        if self.type == "bool":
            return [False, True]
        if self.type == "enum":
            return list(self.domain)
        lo, hi = self.bounds
        return list(range(lo, hi + 1))


@dataclass
class Rule:
    id: str
    when: dict
    then: list[dict]
    priority: int = 0


@dataclass
class DecisionRuleset:
    id: str
    kind: str
    inputs: list[Var]
    outputs: list[Var]
    rules: list[Rule]
    default: list[dict]
    conflict_resolution: str

    @staticmethod
    def from_dict(d: dict) -> "DecisionRuleset":
        return DecisionRuleset(
            id=d["id"],
            kind=d["kind"],
            inputs=[Var.from_dict(v) for v in d["inputs"]],
            outputs=[Var.from_dict(v) for v in d["outputs"]],
            rules=[
                Rule(id=r["id"], when=r["when"], then=r["then"], priority=r.get("priority", 0))
                for r in d["rules"]
            ],
            default=d["default"],
            conflict_resolution=d["conflict_resolution"],
        )

    def input_space(self) -> int:
        space = 1
        for v in self.inputs:
            space *= v.cardinality()
        return space


@dataclass
class Transition:
    id: str
    event: str
    update: list[dict]
    guard: dict | None = None
    emits: list[dict] = field(default_factory=list)


@dataclass
class Event:
    name: str
    params: list[Var] = field(default_factory=list)


@dataclass
class TransitionSystem:
    id: str
    kind: str
    state_vars: list[Var]
    events: list[Event]
    init: list[dict]
    transitions: list[Transition]

    @staticmethod
    def from_dict(d: dict) -> "TransitionSystem":
        return TransitionSystem(
            id=d["id"],
            kind=d["kind"],
            state_vars=[Var.from_dict(v) for v in d["state_vars"]],
            events=[
                Event(name=e["name"], params=[Var.from_dict(p) for p in e.get("params", [])])
                for e in d["events"]
            ],
            init=d["init"],
            transitions=[
                Transition(
                    id=t["id"],
                    event=t["event"],
                    update=t["update"],
                    guard=t.get("guard"),
                    emits=t.get("emits", []),
                )
                for t in d["transitions"]
            ],
        )


@dataclass
class Property:
    id: str
    kind: str
    formula: dict | None = None
    mutual_exclusion: dict | None = None
    monotonicity: dict | None = None
    bound: int | None = None
    intent: str | None = None

    @staticmethod
    def from_dict(d: dict) -> "Property":
        return Property(
            id=d["id"],
            kind=d["kind"],
            formula=d.get("formula"),
            mutual_exclusion=d.get("mutual_exclusion"),
            monotonicity=d.get("monotonicity"),
            bound=d.get("bound"),
            intent=d.get("intent"),
        )


@dataclass
class Item:
    id: str
    domain: str
    ruleset: DecisionRuleset | TransitionSystem
    property: Property
    metadata: dict

    @property
    def is_decision(self) -> bool:
        return isinstance(self.ruleset, DecisionRuleset)

    @staticmethod
    def from_dict(d: dict) -> "Item":
        rs = d["ruleset"]
        ruleset = (
            DecisionRuleset.from_dict(rs)
            if rs.get("kind") == "decision"
            else TransitionSystem.from_dict(rs)
        )
        return Item(
            id=d["id"],
            domain=d["domain"],
            ruleset=ruleset,
            property=Property.from_dict(d["property"]),
            metadata=d.get("metadata", {}),
        )

    @staticmethod
    def load(path: str | Path) -> "Item":
        return Item.from_dict(json.loads(Path(path).read_text()))


def typing_of(vars_: list[Var]) -> dict[str, Var]:
    return {v.name: v for v in vars_}
