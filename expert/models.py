"""Struktur data dasar: Rule."""
from dataclasses import dataclass, field, asdict


@dataclass
class Rule:
    """Aturan IF-THEN dengan Certainty Factor.

    antecedents : daftar id fakta/kesimpulan yang digabung dengan AND.
    consequent  : id kesimpulan.
    kind        : 'faktual' (bersumber langsung literatur) atau 'heuristik' (pertimbangan pakar/perancang).
    sources     : daftar id sumber pada knowledge base.
    """
    id: str
    antecedents: list
    consequent: str
    cf: float
    kind: str = "heuristik"
    sources: list = field(default_factory=list)
    note: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Rule":
        return cls(
            id=d["id"], antecedents=list(d["antecedents"]), consequent=d["consequent"],
            cf=float(d["cf"]), kind=d.get("kind", "heuristik"),
            sources=list(d.get("sources", [])), note=d.get("note", ""),
        )

    def to_dict(self) -> dict:
        return asdict(self)
