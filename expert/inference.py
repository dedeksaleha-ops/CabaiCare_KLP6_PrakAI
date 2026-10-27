"""Inference Engine: Forward Chaining dan Backward Chaining dengan Certainty Factor."""
from .certainty import cf_conclusion
from .working_memory import WorkingMemory


class NeedFact(Exception):
    """Dilempar backward chaining saat sebuah fakta harus ditanyakan ke pengguna."""

    def __init__(self, fact, rule_id, stack):
        super().__init__(fact)
        self.fact = fact          # id fakta yang ditanyakan
        self.rule_id = rule_id    # aturan yang sedang diuji
        self.stack = stack        # rantai (hipotesis, aturan) menuju pertanyaan ini


class InferenceEngine:
    """Mesin inferensi. threshold: CF minimum agar sebuah premis dianggap terpenuhi."""

    def __init__(self, kb, threshold: float = 0.2):
        self.kb = kb
        self.threshold = threshold

    # --------------------------------------------------------------- forward
    def forward_chain(self, wm: WorkingMemory) -> list:
        """Data-driven: dari fakta di working memory, jalankan aturan berurutan per level.

        Pengurutan per level menjamin CF antecedent hasil inferensi sudah lengkap
        (semua bukti sudah digabung) sebelum dipakai aturan level berikutnya.
        """
        wm.reset_inferred()
        trace = []
        step = 1
        for fid, cf in wm.user_facts.items():
            trace.append({"step": step, "type": "FAKTA", "rule": None,
                          "text": f"Fakta awal: {self.kb.name_of(fid)} (keyakinan Anda {cf:.2f})"})
            step += 1
        for rule in self.kb.ordered_rules():
            cfs = [wm.get(a) for a in rule.antecedents]
            if any(c < self.threshold for c in cfs):
                continue
            contrib = cf_conclusion(rule.cf, cfs)
            before = wm.inferred.get(rule.consequent)
            wm.add_inferred(rule.consequent, contrib, rule.id,
                            {"cf_rule": rule.cf, "premises": dict(zip(rule.antecedents, cfs)), "cf_min": min(cfs)})
            after = wm.inferred[rule.consequent]
            text = (f"Aturan {rule.id} terpenuhi. {self.kb.rule_sentence(rule)}. "
                    f"Hitung: CF aturan {rule.cf:.2f} x min premis {min(cfs):.2f} = {contrib:.2f}")
            if before is not None:
                text += f". Digabung dengan bukti sebelumnya ({before:.2f}) menjadi {after:.2f}"
            trace.append({"step": step, "type": "ATURAN", "rule": rule.id, "text": text})
            step += 1
        return trace

    # -------------------------------------------------------------- backward
    def backward_chain(self, goals: list, wm: WorkingMemory) -> list:
        """Goal-driven: buktikan hipotesis mundur. Melempar NeedFact bila perlu bertanya."""
        wm.reset_inferred()
        trace = []
        for g in goals:
            self._prove(g, wm, [], trace, None)
        return trace

    def _prove(self, goal, wm, stack, trace, ctx_rule):
        if goal in wm.proved:
            return wm.proved[goal]
        if self.kb.is_askable(goal):
            if wm.known(goal):
                cf = wm.get(goal)
            elif goal in wm.answered:
                cf = 0.0
            else:
                raise NeedFact(goal, ctx_rule.id if ctx_rule else None, list(stack))
            wm.proved[goal] = cf
            return cf
        trace.append({"step": len(trace) + 1, "type": "GOAL", "rule": None,
                      "text": f"Membuktikan: {self.kb.name_of(goal)}"})
        for rule in self.kb.rules_for(goal):
            cfs, failed = [], None
            for a in rule.antecedents:
                c = self._prove(a, wm, stack + [(goal, rule.id)], trace, rule)
                if c < self.threshold:
                    failed = a
                    break
                cfs.append(c)
            if failed:
                trace.append({"step": len(trace) + 1, "type": "GAGAL", "rule": rule.id,
                              "text": f"Aturan {rule.id} tidak terpenuhi: \"{self.kb.name_of(failed)}\" tidak terbukti"})
                continue
            contrib = cf_conclusion(rule.cf, cfs)
            before = wm.inferred.get(goal)
            wm.add_inferred(goal, contrib, rule.id,
                            {"cf_rule": rule.cf, "premises": dict(zip(rule.antecedents, cfs)), "cf_min": min(cfs)})
            text = (f"Aturan {rule.id} terpenuhi. {self.kb.rule_sentence(rule)}. "
                    f"Hitung: CF aturan {rule.cf:.2f} x min premis {min(cfs):.2f} = {contrib:.2f}")
            if before is not None:
                text += f". Digabung dengan bukti sebelumnya ({before:.2f}) menjadi {wm.inferred[goal]:.2f}"
            trace.append({"step": len(trace) + 1, "type": "ATURAN", "rule": rule.id, "text": text})
        cf = wm.get(goal)
        wm.proved[goal] = cf
        return cf
