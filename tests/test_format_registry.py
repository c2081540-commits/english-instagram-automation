import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from instagram_automation.formats import (CANONICAL_FORMATS, COMMON_SYNC_FIELDS,
    FORMAT_REGISTRY, FormatDefinition, FormatValidationError, validate_format_master)
from instagram_automation.validation import (ValidationError, validate,
    validate_current_production, validate_historical)

EXPECTED = {"text": True, "visual": True, "difference": True, "pattern": True,
            "error_hunt": False, "save_list": True}


def base(fmt):
    return {"content_id":"ENG-900001","format":fmt,"difficulty":"L2","learning_point":"point",
            "question":"Test ___ now.","correct_answer":"right",
            "publish_at":"2026-08-24T07:00:00+09:00","english_correctness":True,"unique_answer":True}


def fixtures():
    text=base("text"); text.update(choices=["wrong","right"],explanation="説明",completed_sentence="Test right now.",
        japanese_translation="訳",threads_reply_explanation="説明",instagram_caption="caption",
        threads_parent_text="hook",threads_answer_text="answer",visual_required=False,question_guide_ja="入るのはどっち？")
    visual=copy.deepcopy(text); visual.update(format="visual",visual_required=True,question_guide_ja=None,
        visual_semantic_consistency=True,visual_answer_uniqueness=True,visual_only_solvable=False,
        visual_semantics={"subject_gender":"verified","subject_count":"verified","action":"verified",
        "direction":"verified","object":"verified","state":"verified","location":"verified",
        "completed_sentence":"Test right now."})
    difference=base("difference"); difference.update(choices=["wrong","right"],
        choice_explanations={"wrong":"誤答","right":"正答"},completed_sentence="Test right now.")
    pattern=base("pattern"); pattern.update(examples=["buy → bought","teach → taught"],target="think → ___",
        choices=["thought","thinked"],correct_answer="thought",pattern_rule="不規則過去形",
        examples_learning_point="point",target_learning_point="point")
    error=base("error_hunt"); error.update(question="4つの英文、何個間違ってる？",correct_answer="1個",answer_mode="count")
    error["sentences"]=[{"sentence":s,"verdict":v,"corrected_sentence":c,"grammar_rule":"rule","reason_ja":"理由"}
        for s,v,c in (("A.","CORRECT","A."),("B.","INCORRECT","B fixed."),("C.","CORRECT","C."),("D.","CORRECT","D."))]
    error["displayed_answer"]="1個"; error["answer_sentences"]=[{"verdict":r["verdict"],"corrected_sentence":r["corrected_sentence"],"reason_ja":r["reason_ja"]} for r in error["sentences"]]
    save=base("save_list"); rows=[{"english":f"term{i}","japanese":f"意味{i}"} for i in range(4)]
    save.update(question="基本表現",list_items=rows,list_theme="基本表現",
        target_item={"prompt":"term ___","completed":"term5","japanese":"意味5","list_theme":"基本表現"},
        choices=["right","wrong"],complete_list=rows+[{"english":"term5","japanese":"意味5"}])
    return {x["format"]:x for x in (text,visual,difference,pattern,error,save)}


class FormatRegistryTests(unittest.TestCase):
    def test_registry_conformance(self):
        self.assertEqual(tuple(FORMAT_REGISTRY), CANONICAL_FORMATS)
        self.assertEqual(set(FORMAT_REGISTRY), set(EXPECTED))
        self.assertEqual(len({d.name for d in FORMAT_REGISTRY.values()}), 6)
        for key, definition in FORMAT_REGISTRY.items():
            self.assertIsInstance(definition, FormatDefinition)
            self.assertEqual(key, definition.name)
            self.assertTrue(callable(definition.master_validator))
            self.assertEqual(definition.uses_choices, EXPECTED[key])
            self.assertTrue(definition.sync_fields)
        self.assertTrue(COMMON_SYNC_FIELDS)

    def test_six_format_contract_snapshots(self):
        for fmt, record in fixtures().items():
            with self.subTest(format=fmt):
                validate_format_master(record)
                missing=copy.deepcopy(record); missing.pop("learning_point")
                with self.assertRaises(FormatValidationError): validate_format_master(missing)

    def test_current_and_historical_entry_points_fail_closed(self):
        valid=fixtures()["text"]
        validate_current_production(valid)
        for bad in (dict(valid, format="Text"), dict(valid, format="unknown_format")):
            with self.assertRaises(ValidationError): validate_current_production(bad)
            with self.assertRaises(ValidationError): validate(bad)
        missing=dict(valid); missing.pop("format")
        with self.assertRaises(ValidationError): validate_current_production(missing)
        historical=json.loads((ROOT/"data/master/ENG-000001.json").read_text())
        validate_historical(historical)
        with self.assertRaises(ValidationError): validate_historical(dict(historical,format="unknown_format"))
        invalid=copy.deepcopy(valid); invalid.pop("choices")
        with self.assertRaises(ValidationError): validate_current_production(invalid)

    def test_cross_repo_registry_contract_when_workspace_sibling_exists(self):
        sibling=ROOT.parent/"english-threads-automation/src/threads_automation/formats.py"
        if not sibling.is_file():
            self.assertEqual(set(FORMAT_REGISTRY), set(EXPECTED))
            return
        spec=importlib.util.spec_from_file_location("threads_registry_contract", sibling)
        module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module)
        self.assertEqual(COMMON_SYNC_FIELDS,module.COMMON_SYNC_FIELDS)
        self.assertEqual({k:(v.uses_choices,v.sync_fields) for k,v in FORMAT_REGISTRY.items()},
                         {k:(v.uses_choices,v.sync_fields) for k,v in module.FORMAT_REGISTRY.items()})


if __name__ == "__main__": unittest.main()
