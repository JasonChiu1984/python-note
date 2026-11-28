from pathlib import Path
import runpy

import pytest


S = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                       "extensions/python_soap_communication_tutorial/example.py"))
APP = S["APP"]
parse = S["parse_response"]
wrap = S["envelope"]
RESULT = f'<b:GetPointResponse xmlns:b="{APP}"><b:value unit="degC">{{}}</b:value></b:GetPointResponse>'
FAULT = ('<soap:Fault><soap:Code><soap:Value>soap:Sender</soap:Value></soap:Code>'
         '<soap:Reason><soap:Text xml:lang="en">Unknown point</soap:Text></soap:Reason></soap:Fault>')


def test_small_demo_keeps_finite_reading_and_both_faults():
    assert parse(wrap("1.1", RESULT.format("22.5"))) == ("OK", 22.5, "degC")
    assert parse(wrap("1.2", FAULT)) == ("Fault", "soap:Sender", "Unknown point")
    assert parse(wrap("1.1", "<soap:Fault><faultcode>soap:Client</faultcode>"
                       "<faultstring>Unknown point</faultstring></soap:Fault>")) == (
                           "Fault", "soap:Client", "Unknown point")


@pytest.mark.parametrize("value", ["not a number", "NaN", "INF", ""])
def test_invalid_business_reading_is_never_success(value):
    assert parse(wrap("1.2", RESULT.format(value)))[0] == "錯誤"


def test_fault_must_be_only_body_child_and_have_display_fields():
    assert parse(wrap("1.2", FAULT + RESULT.format("22.5")))[0] == "錯誤"
    short = "<soap:Fault><soap:Code><soap:Value>soap:Sender</soap:Value></soap:Code></soap:Fault>"
    assert parse(wrap("1.2", short))[0] == "錯誤"
