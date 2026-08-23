import copy
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from instagram_automation.formats import (FormatValidationError, validate_answer_payload,
                                           validate_format_master, validate_quiz_schedule,
                                           validate_schedule_manifests)
from instagram_automation.answer_renderer import validate_production_answer


def base(fmt):
    return {"content_id":"ENG-900001","format":fmt,"difficulty":"L2","learning_point":"test point",
            "question":"Test ___ here.","correct_answer":"right","publish_at":"2026-08-24T07:00:00+09:00",
            "english_correctness":True,"unique_answer":True}


def error_hunt():
    x=base("error_hunt"); x.update(question="4つの英文、何個間違ってる？",correct_answer="1個",answer_mode="count")
    x["sentences"]=[{"sentence":s,"verdict":v,"corrected_sentence":c,"grammar_rule":"rule","reason_ja":"短い理由"} for s,v,c in
                    [("I enjoy cooking.","CORRECT","I enjoy cooking."),("She discussed about it.","INCORRECT","She discussed it."),("We entered the room.","CORRECT","We entered the room."),("He replied to me.","CORRECT","He replied to me.")]]
    x["displayed_answer"]="1個"; x["answer_sentences"]=[{"verdict":r["verdict"],"corrected_sentence":r["corrected_sentence"],"reason_ja":r["reason_ja"]} for r in x["sentences"]]
    return x


def pattern():
    x=base("pattern"); x.update(examples=["buy → bought","teach → taught"],target="think → ___",choices=["thought","thinked"],correct_answer="thought",pattern_rule="不規則過去形",examples_learning_point="test point",target_learning_point="test point")
    return x


def save_list():
    x=base("save_list"); rows=[{"english":f"term{i}","japanese":f"意味{i}"} for i in range(4)]
    x.update(question="基本表現",list_items=rows,target_item={"prompt":"term ___","completed":"term5","japanese":"意味5","list_theme":"基本表現"},list_theme="基本表現",choices=["right","wrong"],complete_list=rows+[{"english":"term5","japanese":"意味5"}])
    return x


def difference():
    x=base("difference"); x.update(choices=["wrong","right"],choice_explanations={"wrong":"誤答の用法","right":"正答の用法"},completed_sentence="Test right here.")
    return x


def standard(fmt="text"):
    x=base(fmt); x.update(choices=["wrong","right"], explanation="短い説明です。",
        completed_sentence="Test right here.", japanese_translation="短い日本語訳です。",
        instagram_caption="caption", threads_parent_text="hook",
        threads_answer_text="✅ 正解は B. right\n\n短い説明です。",threads_reply_explanation="短い説明です。",
        visual_required=fmt=="visual", question_guide_ja="入るのはどっち？")
    if fmt=="visual":
        x.update(question_guide_ja=None,visual_semantic_consistency=True,
                 visual_answer_uniqueness=True,visual_only_solvable=False,
                 visual_semantics={"subject_gender":"verified","subject_count":"verified",
                 "action":"verified","direction":"verified","object":"verified",
                 "state":"verified","location":"verified","completed_sentence":"Test right here."})
    return x


class ProductionFormatTests(unittest.TestCase):
    def test_valid_cases(self):
        for value in (standard(),standard("visual"),error_hunt(),pattern(),save_list(),difference()): validate_format_master(value)
    def test_text_and_visual_contracts_fail_closed(self):
        x=standard(); x["japanese_translation"]=""
        with self.assertRaises(FormatValidationError): validate_format_master(x)
        x=standard("visual"); x["visual_answer_uniqueness"]=False
        with self.assertRaises(FormatValidationError): validate_format_master(x)
    def test_error_hunt_correct_sentence_cannot_be_changed(self):
        x=error_hunt(); x["sentences"][0]["corrected_sentence"]="changed"
        with self.assertRaises(FormatValidationError): validate_format_master(x)
    def test_error_hunt_count_mismatch(self):
        x=error_hunt(); x["displayed_answer"]="2個"
        with self.assertRaises(FormatValidationError): validate_format_master(x)
    def test_error_hunt_missing_correction(self):
        x=error_hunt(); x["sentences"][1]["corrected_sentence"]=x["sentences"][1]["sentence"]
        with self.assertRaises(FormatValidationError): validate_format_master(x)
    def test_pattern_answer_and_rule_are_required(self):
        for mutate in (lambda x:x.update(correct_answer="missing"),lambda x:x.pop("pattern_rule")):
            x=pattern(); mutate(x)
            with self.assertRaises(FormatValidationError): validate_format_master(x)
    def test_save_list_requires_japanese_and_matching_theme(self):
        for mutate in (lambda x:x["list_items"][0].update(japanese=""),lambda x:x["target_item"].update(list_theme="別テーマ")):
            x=save_list(); mutate(x)
            with self.assertRaises(FormatValidationError): validate_format_master(x)
    def test_difference_requires_every_explanation_and_unique_answer(self):
        x=difference(); x["choice_explanations"].pop("wrong")
        with self.assertRaises(FormatValidationError): validate_format_master(x)
        x=difference(); x["choices"]=["right","right"]
        with self.assertRaises(FormatValidationError): validate_format_master(x)
    def test_answer_payloads_are_format_specific(self):
        for x,payload in [(error_hunt(),{"format":"error_hunt","correct_answer":"1個","answer_sentences":error_hunt()["answer_sentences"]}),
                          (pattern(),{"format":"pattern","correct_answer":"thought","pattern_rule":"不規則過去形","examples":["buy → bought","teach → taught"]}),
                          (save_list(),{"format":"save_list","correct_answer":"right","complete_list":save_list()["complete_list"]}),
                          (difference(),{"format":"difference","correct_answer":"right","choice_explanations":difference()["choice_explanations"]})]:
            validate_answer_payload(x,payload)
    def test_answer_image_contract_is_enforced(self):
        x=difference(); x["answer_payload"]={"format":"difference","correct_answer":"right","choice_explanations":x["choice_explanations"]}
        with tempfile.TemporaryDirectory() as directory:
            valid=Path(directory)/"answer.png"
            Image.new("RGB",(1080,1350),"white").save(valid)
            validate_production_answer(x,valid)
            invalid=Path(directory)/"small.png"
            Image.new("RGB",(100,100),"white").save(invalid)
            with self.assertRaises(ValueError): validate_production_answer(x,invalid)
    def test_schedule_uses_date_range_and_daily_slots_not_fixed_legacy_count(self):
        slots=["07:00","09:30"]
        items=[{"content_id":f"ENG-9{i:05d}","publish_at":f"2026-08-{day:02d}T{slot}:00+09:00","status":"pending"}
               for i,(day,slot) in enumerate((d,s) for d in (24,25) for s in slots)]
        validate_quiz_schedule(items,"2026-08-24","2026-08-25",slots)
        with self.assertRaises(FormatValidationError): validate_quiz_schedule(items[:-1],"2026-08-24","2026-08-25",slots)
    def test_old_and_new_schedule_manifests_can_coexist(self):
        slots=["07:00"]
        old={"start_date":"2026-08-24","end_date":"2026-08-24","items":[{"content_id":"ENG-900001","publish_at":"2026-08-24T07:00:00+09:00","status":"posted","content_type":"quiz"}]}
        new={"start_date":"2026-08-25","end_date":"2026-08-25","items":[{"content_id":"ENG-900002","publish_at":"2026-08-25T07:00:00+09:00","status":"pending","content_type":"quiz"}]}
        self.assertEqual(len(validate_schedule_manifests([old,new],slots)),2)

if __name__ == "__main__": unittest.main()
