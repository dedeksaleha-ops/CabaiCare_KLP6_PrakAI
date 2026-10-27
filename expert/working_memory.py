"""Working Memory: menyimpan fakta input pengguna dan hasil inferensi sementara."""
from .certainty import cf_combine


class WorkingMemory:
    """Memori kerja berbasis dictionary.

    user_facts  : fakta dari pengguna {id: CF}
    inferred    : fakta hasil inferensi {id: CF gabungan}
    derivations : jejak asal tiap fakta inferensi (untuk fasilitas HOW)
    fired       : urutan id aturan yang dipakai
    answered    : id fakta yang sudah ditanyakan (termasuk jawaban 'tidak')
    history     : log perubahan memori (update dinamis)
    """

    def __init__(self):
        self.user_facts = {}
        self.inferred = {}
        self.derivations = {}
        self.fired = []
        self.answered = set()
        self.proved = {}
        self.history = []

    def _log(self, op, fid, old, new, by):
        self.history.append({"no": len(self.history) + 1, "op": op, "fact": fid,
                             "old": old, "new": new, "by": by})

    def set_user_fact(self, fid: str, cf: float):
        """Simpan jawaban pengguna. cf <= 0 berarti 'tidak ada' (tetap dicatat sudah dijawab)."""
        old = self.user_facts.get(fid)
        self.answered.add(fid)
        if cf > 0:
            self.user_facts[fid] = cf
            self._log("INPUT", fid, old, cf, "pengguna")
        else:
            self.user_facts.pop(fid, None)
            self._log("INPUT", fid, old, 0.0, "pengguna")

    def get(self, fid: str) -> float:
        if fid in self.user_facts:
            return self.user_facts[fid]
        return self.inferred.get(fid, 0.0)

    def known(self, fid: str) -> bool:
        return fid in self.user_facts or fid in self.inferred

    def add_inferred(self, fid: str, contrib: float, rule_id: str, detail: dict):
        """Tambahkan kontribusi suatu aturan; digabung dengan CF sebelumnya bila ada."""
        old = self.inferred.get(fid)
        new = contrib if old is None else cf_combine(old, contrib)
        self.inferred[fid] = new
        self.derivations.setdefault(fid, []).append({"rule": rule_id, "contrib": contrib, **detail})
        if rule_id not in self.fired:
            self.fired.append(rule_id)
        self._log("INFER", fid, old, new, rule_id)

    def reset_inferred(self):
        """Hapus hasil inferensi (fakta pengguna dipertahankan) sebelum inferensi ulang."""
        self.inferred.clear()
        self.derivations.clear()
        self.fired.clear()
        self.proved.clear()

    def snapshot(self) -> dict:
        return {"user": dict(self.user_facts), "inferred": dict(self.inferred), "fired": list(self.fired)}
