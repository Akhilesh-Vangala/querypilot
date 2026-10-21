"""Malformed and ambiguous model envelopes exhaust bounded corrections safely."""
import json
import pytest
from app.agents.analytics.llm import parse_action
from app.agents.analytics.workflow import AnalyticsWorkflow

@pytest.mark.parametrize("raw",[None,[],42,'{"tool":"list_tables","tool":"run_sql","args":{}}','{"tool":"preview","args":{"name":"fact_claims","limit":1,"limit":20}}','{"tool":"preview","args":{"limit":NaN}}','x'*64001])
def test_ambiguous_nontext_and_oversized_actions_are_rejected(raw):
 with pytest.raises(ValueError):parse_action(raw)

@pytest.mark.parametrize("raw",[None,[],42,'{"tool":"list_tables","tool":"run_sql","args":{}}','x'*64001])
def test_real_graph_returns_bounded_refusal_without_executing_query(db_session,raw):
 class BadModel:
  mode="test-only"
  calls=0
  def complete(self,messages):self.calls+=1;return raw
 model=BadModel();workflow=AnalyticsWorkflow(db_session,llm=model)
 result=workflow.run("Inspect this metric")
 assert result["refused"] and result["rows"]==[]
 assert model.calls==3 and result["attempts"]==0

def test_complete_valid_transcript_is_preserved_above_old_truncation_limit(db_session):
 raw=" "*25000+json.dumps({"tool":"list_tables","args":{}})
 class TranscriptModel:
  calls=0
  def complete(self,messages):
   self.calls+=1
   if self.calls==1:return raw
   assert messages[-2]["content"]==raw
   return json.dumps({"final":{"answer":"Choose a metric","sql":"","chart":"table","refused":False}})
 model=TranscriptModel();result=AnalyticsWorkflow(db_session,llm=model).run("Inspect the schema")
 assert model.calls==2 and result["status"]=="needs_clarification"

@pytest.mark.parametrize("arguments",['{"name":"dim_provider","name":"users"}','{"limit":NaN}', 'x'*64001])
def test_sdk_rejects_ambiguous_raw_arguments_before_dict_conversion(arguments):
 import httpx
 from openai import OpenAI
 from app.agents.analytics.llm import OpenAILLM
 calls=[]
 def transport(req):
  calls.append(req)
  return httpx.Response(200,json={"id":"resp_test","object":"response","created_at":1,"status":"completed","model":"gpt-4o-mini","output":[{"type":"function_call","id":"fc_test","call_id":"call_test","name":"describe_table","arguments":arguments,"status":"completed"}],"usage":{"input_tokens":120,"output_tokens":30,"total_tokens":150}})
 client=OpenAI(api_key="transport-test-only",max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(transport)))
 adapter=OpenAILLM("transport-test-only","gpt-4o-mini",client)
 try:
  with pytest.raises(ValueError):adapter.complete([{"role":"user","content":"claims"}])
  assert len(calls)==1 and adapter.history==[]
  assert adapter.usage=={"input_tokens":120,"output_tokens":30}
 finally:adapter.close()

def test_sdk_missing_usage_does_not_become_a_zero_token_call():
 import httpx
 from openai import OpenAI
 from app.agents.analytics.llm import OpenAILLM
 calls=[]
 def transport(req):
  calls.append(req)
  return httpx.Response(200,json={"id":"resp_test","object":"response","created_at":1,"status":"completed","model":"gpt-4o-mini","output":[],"usage":None})
 client=OpenAI(api_key="transport-test-only",max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(transport)))
 adapter=OpenAILLM("transport-test-only","gpt-4o-mini",client)
 try:
  with pytest.raises(RuntimeError,match="usage"):adapter.complete([{"role":"user","content":"claims"}])
  assert len(calls)==1 and adapter.failure_billing_unknown is True
  with pytest.raises(RuntimeError,match="reconciliation"):adapter.complete([{"role":"user","content":"claims"}])
  assert len(calls)==1
 finally:adapter.close()
