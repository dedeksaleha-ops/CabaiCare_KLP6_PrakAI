"""Knowledge Base: pemuatan, penyimpanan, validasi dan CRUD aturan."""
import json
import os
import re
import shutil
import tempfile

from .models import Rule


class KnowledgeBaseError(Exception):
    """Kesalahan pemuatan/penyimpanan knowledge base."""


class KnowledgeBase:
    """Knowledge base berbasis file JSON."""

    ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{1,15}$")

    def __init__(self, path: str):
        self.path = path
        self._mtime = 0.0
        self.load()

    # ------------------------------------------------------------------ I/O
    def load(self):
        """Muat knowledge base dari file JSON."""
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            self.meta = data["meta"]
            self.sources = data["sources"]
            self.facts = data["facts"]
            self.conclusions = data["conclusions"]
            self.conflicts = data.get("conflicts", [])
            self.dose = data["dose"]
            self.rules = {r["id"]: Rule.from_dict(r) for r in data["rules"]}
            self._mtime = os.path.getmtime(self.path)
        except FileNotFoundError as exc:
            raise KnowledgeBaseError(f"File knowledge base tidak ditemukan: {self.path}") from exc
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise KnowledgeBaseError(f"Format knowledge base tidak valid: {exc}") from exc

    def reload_if_changed(self):
        if os.path.exists(self.path) and os.path.getmtime(self.path) != self._mtime:
            self.load()

    def save(self):
        """Simpan secara atomik (tulis file sementara lalu ganti)."""
        data = {"meta": self.meta, "sources": self.sources, "facts": self.facts,
                "conclusions": self.conclusions, "conflicts": self.conflicts,
                "rules": [r.to_dict() for r in self.rules.values()], "dose": self.dose}
        directory = os.path.dirname(os.path.abspath(self.path))
        fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except OSError as exc:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise KnowledgeBaseError(f"Gagal menyimpan knowledge base: {exc}") from exc
        self._mtime = os.path.getmtime(self.path)

    def restore_default(self):
        """Kembalikan knowledge base ke versi awal."""
        default = os.path.join(os.path.dirname(os.path.abspath(self.path)), "knowledge_base.default.json")
        if not os.path.exists(default):
            raise KnowledgeBaseError("File knowledge_base.default.json tidak ditemukan")
        shutil.copyfile(default, self.path)
        self.load()

    # --------------------------------------------------------------- queries
    def is_askable(self, fid: str) -> bool:
        return fid in self.facts and self.facts[fid].get("askable", True)

    def name_of(self, fid: str) -> str:
        if fid in self.facts:
            return self.facts[fid]["name"]
        if fid in self.conclusions:
            return self.conclusions[fid]["name"]
        return fid

    def rules_for(self, goal: str) -> list:
        return [r for r in self.rules.values() if r.consequent == goal]

    def rules_using(self, fid: str) -> list:
        return [r for r in self.rules.values() if fid in r.antecedents]

    def conclusions_of_type(self, tipe: str) -> dict:
        return {k: v for k, v in self.conclusions.items() if v.get("tipe") == tipe}

    def rule_text(self, rule: Rule, with_names: bool = False) -> str:
        label = (lambda x: f"{x} ({self.name_of(x)})") if with_names else (lambda x: x)
        ante = " AND ".join(label(a) for a in rule.antecedents)
        return f"{rule.id}: IF {ante} THEN {label(rule.consequent)} (CF: {rule.cf:.2f})"

    def rule_sentence(self, rule: Rule) -> str:
        """Aturan dalam kalimat biasa."""
        ante = " dan ".join(f"\"{self.name_of(a)}\"" for a in rule.antecedents)
        return f"Jika {ante}, maka {self.name_of(rule.consequent)}"

    def why_text(self, fid: str) -> str:
        """Alasan gejala ditanyakan: aturan-aturan yang memakainya."""
        used = self.rules_using(fid)
        if not used:
            return "Fakta ini belum dipakai aturan mana pun."
        parts = [f"{r.id} (menguji {self.name_of(r.consequent)})" for r in used]
        return "Dipakai oleh: " + "; ".join(parts)

    def search_facts(self, query: str) -> list:
        q = query.strip().lower()
        return [(fid, f) for fid, f in self.facts.items() if f.get("askable", True) and q in f["name"].lower()]

    # ------------------------------------------------------------ validation
    @staticmethod
    def _levels(rules: dict, askable: set):
        """Hitung level tiap kesimpulan; kembalikan (levels, ada_siklus)."""
        by_goal = {}
        for r in rules.values():
            by_goal.setdefault(r.consequent, []).append(r)
        levels, visiting = {}, set()

        def level(node):
            if node in levels:
                return levels[node]
            if node not in by_goal:
                return 0
            if node in visiting:
                raise RecursionError(node)
            visiting.add(node)
            lv = 1 + max(level(a) for r in by_goal[node] for a in r.antecedents)
            visiting.discard(node)
            levels[node] = lv
            return lv

        try:
            for g in by_goal:
                level(g)
        except RecursionError:
            return levels, True
        return levels, False

    def has_cycle(self, rules: dict = None) -> bool:
        return self._levels(rules if rules is not None else self.rules, set())[1]

    def ordered_rules(self) -> list:
        """Urutkan aturan menurut level (bukti dasar diproses lebih dulu)."""
        levels, cyc = self._levels(self.rules, set())
        if cyc:
            raise KnowledgeBaseError("Terdapat siklus pada aturan")
        return sorted(self.rules.values(), key=lambda r: (levels.get(r.consequent, 1), r.id))

    def validate_rule(self, rule: Rule, is_new: bool = True) -> list:
        """Kembalikan daftar pesan kesalahan (kosong jika valid)."""
        errors = []
        if not self.ID_PATTERN.match(rule.id or ""):
            errors.append("ID aturan harus diawali huruf, 2-16 karakter huruf/angka/underscore (contoh: R28).")
        elif is_new and rule.id in self.rules:
            errors.append(f"ID {rule.id} sudah dipakai.")
        if not rule.antecedents:
            errors.append("Antecedent (IF) minimal satu.")
        if len(set(rule.antecedents)) != len(rule.antecedents):
            errors.append("Antecedent tidak boleh duplikat.")
        known = set(self.facts) | set(self.conclusions)
        for a in rule.antecedents:
            if a not in known:
                errors.append(f"Antecedent '{a}' tidak dikenal.")
        if rule.consequent not in self.conclusions:
            errors.append("Consequent (THEN) harus berupa kesimpulan yang terdaftar.")
        if rule.consequent in rule.antecedents:
            errors.append("Consequent tidak boleh sama dengan antecedent.")
        if not (-1.0 <= rule.cf <= 1.0) or rule.cf == 0:
            errors.append("CF aturan harus di antara -1.0 dan 1.0 dan tidak boleh 0.")
        if rule.kind not in ("faktual", "heuristik"):
            errors.append("Jenis aturan harus 'faktual' atau 'heuristik'.")
        if not rule.sources:
            errors.append("Sumber pengetahuan wajib diisi (minimal satu).")
        for s in rule.sources:
            if s not in self.sources:
                errors.append(f"Sumber '{s}' tidak terdaftar.")
        if not errors:
            trial = dict(self.rules)
            trial[rule.id] = rule
            if self.has_cycle(trial):
                errors.append("Aturan ini menimbulkan siklus penalaran.")
        return errors

    # ------------------------------------------------------------------ CRUD
    def add_rule(self, rule: Rule) -> list:
        errors = self.validate_rule(rule, is_new=True)
        if not errors:
            self.rules[rule.id] = rule
            self.save()
        return errors

    def update_rule(self, rule: Rule) -> list:
        if rule.id not in self.rules:
            return [f"Aturan {rule.id} tidak ditemukan."]
        errors = self.validate_rule(rule, is_new=False)
        if not errors:
            self.rules[rule.id] = rule
            self.save()
        return errors

    def delete_rule(self, rule_id: str) -> list:
        """Hapus aturan; kembalikan peringatan (bukan error) bila ada kesimpulan yang kehilangan dasar."""
        if rule_id not in self.rules:
            return [f"Aturan {rule_id} tidak ditemukan."]
        goal = self.rules[rule_id].consequent
        del self.rules[rule_id]
        self.save()
        warnings = []
        if not self.rules_for(goal) and self.rules_using(goal):
            warnings.append(f"Kesimpulan '{goal}' tidak lagi memiliki aturan, padahal dipakai aturan lain.")
        return warnings
