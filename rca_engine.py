from pathlib import Path
import json, sqlite3
import pandas as pd
DB=Path('data/plant.db')
def conn():
    if not DB.exists(): raise FileNotFoundError('Run: python generate_data.py')
    return sqlite3.connect(DB)
def list_events(limit=50):
    with conn() as c:
        d=pd.read_sql_query('SELECT event_id,start_time,line,machine,shift,duration_min,reported_category,operator_note FROM downtime_events ORDER BY start_time DESC LIMIT ?',c,params=(int(limit),))
    return d.to_dict('records')
def get_event_evidence(event_id):
    with conn() as c:
        e=pd.read_sql_query('SELECT * FROM downtime_events WHERE event_id=?',c,params=(event_id,))
        if e.empty: return {'error':f'Unknown event ID {event_id}','valid_event_ids':list_events()}
        def q(table,order=''):
            return pd.read_sql_query(f'SELECT * FROM {table} WHERE event_id=? {order}',c,params=(event_id,)).to_dict('records')
        out={'event':e.iloc[0].to_dict(),'plc_alarms':q('plc_alarms','ORDER BY timestamp'),'mes_context':q('mes_context'),'historian_signals':q('historian_signals','ORDER BY timestamp,signal'),'maintenance_work_orders':q('maintenance_work_orders','ORDER BY created_at')}
    return json.loads(json.dumps(out,default=str))
def rank_hypotheses(event_id):
    ev=get_event_evidence(event_id)
    if 'error' in ev:return ev
    causes={k:{'score':0,'evidence':[]} for k in ['MOTOR_OVERLOAD','BEARING_VIBRATION','SENSOR_MISREAD','MATERIAL_SHORTAGE','RECTIFIER_OVERTEMP']}
    alarm=' '.join(str(a.get('alarm_code',''))+' '+str(a.get('alarm_text','')) for a in ev['plc_alarms']).lower()
    rules=[('MOTOR_OVERLOAD',['a102','motor overload'],4),('BEARING_VIBRATION',['m241','vibration'],4),('SENSOR_MISREAD',['s017','photoeye'],4),('MATERIAL_SHORTAGE',['p009','buffer low','line starved'],4),('RECTIFIER_OVERTEMP',['e330','rectifier temperature'],4)]
    for cause,terms,pts in rules:
        if any(t in alarm for t in terms):causes[cause]['score']+=pts;causes[cause]['evidence'].append('PLC alarm signature matches hypothesis.')
    mes=ev['mes_context'][0] if ev['mes_context'] else {}
    if mes.get('material_status')=='SHORTAGE':causes['MATERIAL_SHORTAGE']['score']+=4;causes['MATERIAL_SHORTAGE']['evidence'].append('MES reports material status SHORTAGE.')
    h=pd.DataFrame(ev['historian_signals'])
    checks=[('motor_current','MOTOR_OVERLOAD',22,'Motor current reached at least 22 A.'),('vibration_mm_s','BEARING_VIBRATION',7,'Vibration reached at least 7 mm/s.'),('photoeye_transitions_min','SENSOR_MISREAD',35,'Photoeye transition rate exceeded 35/min.'),('buffer_level_pct','MATERIAL_SHORTAGE',15,'Buffer level fell to 15% or lower.'),('rectifier_temp_c','RECTIFIER_OVERTEMP',85,'Rectifier temperature reached at least 85°C.')]
    for sig,cause,threshold,label in checks:
        vals=pd.to_numeric(h.loc[h.signal==sig,'value'],errors='coerce') if not h.empty else pd.Series(dtype=float)
        if not vals.empty and vals.max()>=threshold:causes[cause]['score']+=3;causes[cause]['evidence'].append(label)
    wo=ev['maintenance_work_orders'][0] if ev['maintenance_work_orders'] else {}
    cmap={'MTR-OVER':'MOTOR_OVERLOAD','MECH-VIB':'BEARING_VIBRATION','SENS-CHK':'SENSOR_MISREAD','MAT-FEED':'MATERIAL_SHORTAGE','RECT-TEMP':'RECTIFIER_OVERTEMP'}
    if wo.get('failure_code') in cmap:
        c=cmap[wo['failure_code']];causes[c]['score']+=1;causes[c]['evidence'].append('Work-order code is consistent; corroboration only, not independent proof.')
    ranked=sorted([{'hypothesis':k,'score':v['score'],'evidence':v['evidence']} for k,v in causes.items()],key=lambda x:x['score'],reverse=True)
    return {'event_id':event_id,'ranked_hypotheses':ranked,'interpretation_note':'Scores are rule-based evidence weights, not calibrated probabilities. Validate with plant SMEs.'}
def similar_events(event_id,limit=5):
    ev=get_event_evidence(event_id)
    if 'error' in ev:return ev
    e=ev['event']
    with conn() as c:
        d=pd.read_sql_query('''SELECT d.event_id,d.start_time,d.line,d.machine,d.duration_min,d.reported_category,w.failure_code,w.action_taken FROM downtime_events d LEFT JOIN maintenance_work_orders w ON d.event_id=w.event_id WHERE d.event_id<>? AND (d.machine=? OR d.line=?) ORDER BY d.start_time DESC LIMIT ?''',c,params=(event_id,e['machine'],e['line'],int(limit)))
    return d.to_dict('records')
