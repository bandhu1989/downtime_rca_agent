import json, os
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from rca_engine import list_events,get_event_evidence,rank_hypotheses,similar_events
load_dotenv()
@tool
def list_recent_downtime_events(limit:int=20)->str:
    """List simulated downtime events and valid event IDs."""
    return json.dumps(list_events(limit),default=str)
@tool
def retrieve_multisource_evidence(event_id:str)->str:
    """Retrieve PLC alarms, MES context, historian measurements and maintenance work orders for an event."""
    return json.dumps(get_event_evidence(event_id),default=str)
@tool
def rank_root_cause_hypotheses(event_id:str)->str:
    """Rank possible causes from deterministic alarm, MES and historian rules. Scores are not probabilities."""
    return json.dumps(rank_hypotheses(event_id),default=str)
@tool
def find_similar_downtime_events(event_id:str,limit:int=5)->str:
    """Find recent events on the same machine or line with work-order actions."""
    return json.dumps(similar_events(event_id,limit),default=str)
SYSTEM_PROMPT='''You are a Downtime Investigator and Root Cause Intelligence specialist for battery manufacturing. Always retrieve evidence and rank hypotheses before recommending. Structure the response: (1) incident summary, (2) timeline, (3) evidence by PLC/MES/historian/maintenance, (4) ranked hypotheses with supporting and conflicting evidence, (5) safe diagnostic checks ordered by value, (6) confidence label and reason, (7) data gaps, (8) suggested owner and next action. Do not call a hypothesis confirmed unless records prove it. Scores are rule weights, never probabilities. Distinguish correlation from causation. Do not invent data, limits or work orders. Never suggest bypassing safety interlocks. This is read-only; no machine commands. Simulated evidence does not prove real-world cause.'''
def build_agent():
    if not os.getenv('OPENAI_API_KEY'):raise RuntimeError('OPENAI_API_KEY missing. Create .env from .env.example.')
    llm=ChatOpenAI(model=os.getenv('OPENAI_MODEL','gpt-4.1-mini'),temperature=0)
    return create_agent(model=llm,tools=[list_recent_downtime_events,retrieve_multisource_evidence,rank_root_cause_hypotheses,find_similar_downtime_events],system_prompt=SYSTEM_PROMPT)
def investigate(question:str)->str:
    result=build_agent().invoke({'messages':[{'role':'user','content':question}]})
    return result['messages'][-1].content
