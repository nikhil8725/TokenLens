from __future__ import annotations
from token_lens._session import Session
from .conftest import make_record, make_usage


def test_add_call_increments_calls():
    s = Session()
    s.add_call(make_record())
    assert len(s.calls) == 1


def test_total_tokens_sums_usage():
    s = Session()
    r = make_record(usage=make_usage(prompt=100, completion=50))
    s.add_call(r)
    assert s.total_tokens() == 150


def test_system_prompt_tracked():
    s = Session()
    msgs = [{"role": "system", "content": "You are a chef."}]
    s.add_call(make_record(messages=msgs + [{"role": "user", "content": "hi"}]))
    assert "You are a chef." in s._system_prompts


def test_duplicate_hash_counted():
    s = Session()
    msgs = [{"role": "user", "content": "same prompt"}]
    r1 = make_record(messages=msgs)
    r2 = make_record(messages=msgs)
    s.add_call(r1)
    s.add_call(r2)
    assert max(s._prompt_hashes.values()) == 2


def test_calls_by_model():
    s = Session()
    s.add_call(make_record(model="gpt-4o-mini"))
    s.add_call(make_record(model="gpt-4o"))
    s.add_call(make_record(model="gpt-4o-mini"))
    by_model = s.calls_by_model()
    assert len(by_model["gpt-4o-mini"]) == 2
    assert len(by_model["gpt-4o"]) == 1
