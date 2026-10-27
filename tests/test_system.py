"""Pengujian unit sistem pakar: CF, forward/backward chaining, validasi KB, rekomendasi, reporting."""
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from expert.certainty import cf_combine, cf_combine_many, cf_conclusion, cf_from_mb_md
from expert.consultation import build_result, set_phase, validate_input
from expert.explanation import explain_how, explain_why
from expert.inference import InferenceEngine, NeedFact
from expert.knowledge_base import KnowledgeBase, KnowledgeBaseError
from expert.models import Rule
from expert.reporting import compute_stats, filter_history, result_to_pdf, result_to_text, save_consultation, load_history
from expert.working_memory import WorkingMemory

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def kb(tmp_path):
    p = tmp_path / "kb.json"
    shutil.copy(os.path.join(BASE, "data", "knowledge_base.default.json"), p)
    shutil.copy(os.path.join(BASE, "data", "knowledge_base.default.json"), tmp_path / "knowledge_base.default.json")
    return KnowledgeBase(str(p))


def run_forward(kb, facts, fase="vegetatif"):
    wm = WorkingMemory()
    for k, v in facts.items():
        wm.set_user_fact(k, v)
    set_phase(wm, fase)
    return wm, InferenceEngine(kb).forward_chain(wm)


def test_cf_formulas():
    assert cf_combine(0.6, 0.5) == pytest.approx(0.8)
    assert cf_combine(-0.6, -0.5) == pytest.approx(-0.8)
    assert cf_combine(0.8, -0.4) == pytest.approx(0.4 / 0.6)
    assert cf_conclusion(0.8, [0.9, 0.5]) == pytest.approx(0.4)
    assert cf_from_mb_md(0.9, 0.2) == pytest.approx(0.7)
    assert cf_combine_many([0.5, 0.5, 0.5]) == pytest.approx(0.875)
    with pytest.raises(ValueError):
        cf_from_mb_md(1.2, 0)


def test_tc1_defisiensi_N_vegetatif(kb):
    wm, _ = run_forward(kb, {"G01": 0.8, "G02": 0.8})
    # R01: .7*.8=.56 ; R02: .85*.8=.68 ; gabungan = .56+.68*.44
    assert wm.get("def_N") == pytest.approx(0.56 + 0.68 * 0.44)
    assert wm.get("saran_N_vegetatif") > 0.5 and wm.get("saran_N_generatif") == 0


def test_tc2_kalium_generatif(kb):
    wm, _ = run_forward(kb, {"G07": 1.0, "G08": 0.8}, "generatif")
    assert wm.get("def_K") > 0.8 and wm.get("saran_K_generatif") > 0.7


def test_tc3_kelebihan_N_dan_busuk_ujung(kb):
    wm, _ = run_forward(kb, {"G14": 1.0, "G10": 0.8}, "generatif")
    assert wm.get("exc_N") > 0.8 and wm.get("def_Ca") > 0.5
    assert wm.get("saran_kurangi_N_atur_air") > 0.4  # rantai 3 level


def test_tc4_tanpa_diagnosis(kb):
    wm, _ = run_forward(kb, {"G09": 0.4})
    assert wm.inferred == {}


def test_threshold_blocks_weak_evidence(kb):
    wm, _ = run_forward(kb, {"G03": 0.3})  # .5*.3 = .15 -> di bawah ambang saat dipakai sebagai premis saran
    assert wm.get("def_N") == pytest.approx(0.15)
    assert wm.get("saran_N_vegetatif") == 0


def test_backward_asks_then_proves(kb):
    wm = WorkingMemory()
    set_phase(wm, "vegetatif")
    eng = InferenceEngine(kb)
    with pytest.raises(NeedFact) as e:
        eng.backward_chain(["def_N"], wm)
    assert e.value.fact == "G01" and e.value.rule_id == "R01"
    assert "Daun tua" in explain_why(kb, e.value)
    wm.set_user_fact("G01", 0.8)
    with pytest.raises(NeedFact) as e2:
        eng.backward_chain(["def_N"], wm)
    assert e2.value.fact == "G02"
    wm.set_user_fact("G02", 0.0)  # jawaban "tidak"
    with pytest.raises(NeedFact) as e3:
        eng.backward_chain(["def_N"], wm)
    assert e3.value.fact == "G03" and e3.value.rule_id == "R03"  # R03 tetap diuji
    wm.set_user_fact("G03", 0.0)
    with pytest.raises(NeedFact) as e4:
        eng.backward_chain(["def_N"], wm)
    assert e4.value.fact == "G12" and e4.value.rule_id == "R04"  # R04 = G01 AND G12
    wm.set_user_fact("G12", 0.0)
    with pytest.raises(NeedFact) as e5:
        eng.backward_chain(["def_N"], wm)
    assert e5.value.fact == "G09" and e5.value.rule_id == "R05"  # R05 = G01 AND G09
    wm.set_user_fact("G09", 0.0)
    eng.backward_chain(["def_N"], wm)
    assert wm.get("def_N") == pytest.approx(0.56)


def test_backward_short_circuits(kb):
    wm = WorkingMemory()
    set_phase(wm, "vegetatif")
    wm.set_user_fact("G10", 0.0)
    eng = InferenceEngine(kb)
    with pytest.raises(NeedFact) as e:
        eng.backward_chain(["def_Ca"], wm)
    assert e.value.fact == "G11"  # R10 gagal; R11 gagal di G10; R12 minta G11 (G10 tidak ditanya ulang)


def test_forward_backward_consistent(kb):
    facts = {"G13": 0.8, "G07": 0.6}
    wm_f, _ = run_forward(kb, facts)
    wm_b = WorkingMemory()
    set_phase(wm_b, "vegetatif")
    for k, v in facts.items():
        wm_b.set_user_fact(k, v)
    for g in ("G08", "G11", "G16"):  # jawaban "tidak" untuk pertanyaan lanjutan
        wm_b.set_user_fact(g, 0.0)
    InferenceEngine(kb).backward_chain(["def_Mg", "saran_Mg", "def_K"], wm_b)
    assert wm_b.get("def_Mg") == pytest.approx(wm_f.get("def_Mg"))
    assert wm_b.get("def_K") == pytest.approx(wm_f.get("def_K"))


def test_how_explanation(kb):
    wm, _ = run_forward(kb, {"G13": 0.8})
    text = "\n".join(explain_how(kb, wm, "def_Mg"))
    assert "R16" in text and "keyakinan Anda 80%" in text and "Bukti 1" in text and "min premis" in text


def test_validate_input(kb):
    errs, warns = validate_input(kb, {}, 0)
    assert len(errs) == 2
    _, warns = validate_input(kb, {"G01": 0.8, "G14": 0.8}, 100)
    assert warns


def test_rule_validation_and_crud(kb):
    bad = Rule("R99", ["G99"], "def_N", 0.0, "x", [])
    assert len(kb.validate_rule(bad)) >= 4
    dup = Rule("R01", ["G01"], "def_N", 0.5, "faktual", ["S1"])
    assert any("sudah dipakai" in e for e in kb.validate_rule(dup))
    ok = Rule("R32", ["G09", "G12"], "def_K", 0.55, "heuristik", ["S3"])
    assert kb.add_rule(ok) == []
    assert "R32" in KnowledgeBase(kb.path).rules  # tersimpan ke file
    ok.cf = 0.6
    assert kb.update_rule(ok) == [] and KnowledgeBase(kb.path).rules["R32"].cf == 0.6
    kb.delete_rule("R32")
    assert "R32" not in KnowledgeBase(kb.path).rules


def test_cycle_detection(kb):
    cyc = Rule("R98", ["saran_Ca"], "def_Ca", 0.5, "heuristik", ["S3"])
    assert any("siklus" in e for e in kb.validate_rule(cyc))


def test_corrupt_kb_raises(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{rusak")
    with pytest.raises(KnowledgeBaseError):
        KnowledgeBase(str(p))
    with pytest.raises(KnowledgeBaseError):
        KnowledgeBase(str(tmp_path / "tidak_ada.json"))


def test_recommendation_values(kb):
    wm, tr = run_forward(kb, {"G01": 1.0, "G02": 1.0})
    res = build_result(kb, wm, "forward", "vegetatif", 10000, tr)
    n = res["dosis"]["baris"][0]
    assert n["Susulan per aplikasi (kg hara/ha)"] == pytest.approx(150 / 3 * 1.25, abs=0.1)  # defisiensi N naik 25%
    assert n["Susulan (kg produk/ha)"] == pytest.approx(150 / 3 * 1.25 / 0.46, abs=0.1)
    wm0, tr0 = run_forward(kb, {"G09": 0.4}, "generatif")
    base = build_result(kb, wm0, "forward", "generatif", 10000, tr0)["dosis"]["baris"]
    assert base[0]["Susulan per aplikasi (kg hara/ha)"] == pytest.approx(50)   # N: 1/3 x 150
    assert base[1]["Pupuk dasar (kg hara/ha)"] == pytest.approx(150)            # P: seluruhnya pupuk dasar
    assert base[1]["Susulan per aplikasi (kg hara/ha)"] == pytest.approx(0)
    assert base[2]["Susulan per aplikasi (kg hara/ha)"] == pytest.approx(50)   # K: 1/3 x 150
    wm1, tr1 = run_forward(kb, {"G14": 1.0})
    exc = build_result(kb, wm1, "forward", "vegetatif", 10000, tr1)["dosis"]["baris"][0]
    assert exc["Susulan per aplikasi (kg hara/ha)"] == pytest.approx(25)       # kelebihan N: x0.5


def test_reporting(kb, tmp_path):
    wm, tr = run_forward(kb, {"G10": 0.8})
    res = build_result(kb, wm, "forward", "generatif", 500, tr)
    path = str(tmp_path / "h.json")
    save_consultation(path, res)
    save_consultation(path, res)
    hist = load_history(path)
    assert len(hist) == 2
    st = compute_stats(hist)
    assert st["total"] == 2 and st["aturan"]["R13"] == 2
    assert len(filter_history(hist, "def_Ca", 0.5)) == 2 and filter_history(hist, "def_K", 0.0) == []
    assert "Kalsium" in result_to_text(kb, res)
    assert result_to_pdf(kb, res)[:4] == b"%PDF"
    assert load_history(str(tmp_path / "none.json")) == []
