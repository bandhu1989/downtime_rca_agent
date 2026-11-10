import os
import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from generate_data import make_data
from rca_engine import list_events,get_event_evidence,rank_hypotheses,similar_events
load_dotenv()
st.set_page_config(page_title='Downtime Investigator',page_icon='🔎',layout='wide')
st.title('🔎 Downtime Investigator & Root Cause Intelligence')
st.caption('Battery manufacturing | Synthetic multi-source feeds | Read-only decision support')
if not os.path.exists('data/plant.db'):make_data()
events=pd.DataFrame(list_events(100))
with st.sidebar:
    st.header('Investigation selector'); selected=st.selectbox('Downtime event',events.event_id.tolist())
    st.caption('All values are synthetic. Do not use for real operational decisions.')
ev=get_event_evidence(selected); event=ev['event']
a,b,c,d=st.columns(4); a.metric('Event',event['event_id']); b.metric('Duration',f"{event['duration_min']} min"); c.metric('Line',event['line']); d.metric('Machine',event['machine'])
t1,t2,t3,t4=st.tabs(['Evidence overview','Root-cause hypotheses','Similar events','AI investigator'])
with t1:
    st.write(f"**Start:** {event['start_time']} | **Shift:** {event['shift']} | **Reported category:** {event['reported_category']}")
    st.write(f"**Operator note:** {event['operator_note']}")
    left,right=st.columns(2)
    with left:
        st.markdown('#### PLC alarms'); st.dataframe(pd.DataFrame(ev['plc_alarms']),use_container_width=True)
        st.markdown('#### MES context'); st.dataframe(pd.DataFrame(ev['mes_context']),use_container_width=True)
    with right:
        st.markdown('#### Maintenance work orders'); st.dataframe(pd.DataFrame(ev['maintenance_work_orders']),use_container_width=True)
        st.markdown('#### Historian signals')
        h=pd.DataFrame(ev['historian_signals'])
        st.plotly_chart(px.line(h,x='timestamp',y='value',color='signal',markers=True,title='Signals around event'),use_container_width=True)
        st.dataframe(h,use_container_width=True)
with t2:
    result=rank_hypotheses(selected); st.info(result['interpretation_note']); df=pd.DataFrame(result['ranked_hypotheses']); st.dataframe(df,use_container_width=True)
    st.write('**Leading hypothesis:**',df.iloc[0]['hypothesis'])
    for item in df.iloc[0]['evidence']:st.write('- '+item)
with t3:
    st.dataframe(pd.DataFrame(similar_events(selected)),use_container_width=True)
with t4:
    st.write('Example: Investigate DT-0005. Explain the evidence, competing hypotheses, data gaps and safe next checks.')
    q=st.text_area('Investigation question',value=f'Investigate {selected}. Explain evidence, competing hypotheses, data gaps, confidence and next checks.')
    if st.button('Run AI investigation',type='primary'):
        if not os.getenv('OPENAI_API_KEY'):st.error('Add OPENAI_API_KEY to .env. Deterministic evidence tabs work without an API key.')
        else:
            with st.spinner('Investigating...'):
                try:
                    from agent import investigate
                    st.markdown(investigate(q))
                except Exception as ex:st.error(f'Agent call failed: {ex}')
st.divider(); st.caption('PoC safeguards: simulated data • evidence weights are not probabilities • no PLC write-back • human approval required.')
