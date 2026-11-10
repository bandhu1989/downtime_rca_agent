from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd

DATA = Path('data'); DATA.mkdir(exist_ok=True)
DB = DATA / 'plant.db'
rng = np.random.default_rng(2026)
scenarios = [
 ('MOTOR_OVERLOAD','Assembly','Assembly Conveyor','Mechanical breakdown',18,'Conveyor jam during transfer'),
 ('BEARING_VIBRATION','Assembly','Welding Station','Mechanical breakdown',24,'Abnormal vibration reported'),
 ('SENSOR_MISREAD','Finishing','Final Tester','Minor stoppage',12,'Part-present signal intermittent'),
 ('MATERIAL_SHORTAGE','Assembly','Assembly Conveyor','Material shortage',20,'Line starved for battery casing'),
 ('RECTIFIER_OVERTEMP','Formation','Formation Rectifier','Electrical fault',28,'Rectifier thermal trip'),
 ('MOTOR_OVERLOAD','Finishing','Filling Machine','Mechanical breakdown',16,'Drive overload after product jam'),
 ('SENSOR_MISREAD','Assembly','Welding Station','Minor stoppage',10,'Fixture sensor did not confirm'),
 ('BEARING_VIBRATION','Finishing','Filling Machine','Mechanical breakdown',22,'Vibration alarm preceded stoppage'),
 ('MATERIAL_SHORTAGE','Finishing','Final Tester','Material shortage',15,'Feed buffer depleted'),
 ('RECTIFIER_OVERTEMP','Formation','Charging Circuit','Electrical fault',25,'High temperature on charging circuit'),
 ('MOTOR_OVERLOAD','Assembly','Welding Station','Mechanical breakdown',19,'Motor current increased before stop'),
 ('SENSOR_MISREAD','Finishing','Final Tester','Minor stoppage',11,'Photoeye signal chatter'),
 ('MATERIAL_SHORTAGE','Formation','Formation Rectifier','Material shortage',17,'Upstream transfer delay'),
 ('RECTIFIER_OVERTEMP','Formation','Formation Rectifier','Electrical fault',26,'Cooling airflow suspected low'),
 ('BEARING_VIBRATION','Assembly','Assembly Conveyor','Mechanical breakdown',21,'Bearing noise and vibration'),
 ('MOTOR_OVERLOAD','Finishing','Filling Machine','Mechanical breakdown',14,'Motor overload after short jam'),
 ('SENSOR_MISREAD','Assembly','Assembly Conveyor','Minor stoppage',13,'Sensor toggling without part movement'),
 ('MATERIAL_SHORTAGE','Formation','Charging Circuit','Material shortage',18,'Material queue below minimum')]
alarm_map = {
 'MOTOR_OVERLOAD':('PLC_A102','Drive motor overload trip','HIGH'),
 'BEARING_VIBRATION':('PLC_M241','Vibration above warning threshold','MEDIUM'),
 'SENSOR_MISREAD':('PLC_S017','Photoeye / part-present signal unstable','MEDIUM'),
 'MATERIAL_SHORTAGE':('PLC_P009','Infeed buffer low / line starved','MEDIUM'),
 'RECTIFIER_OVERTEMP':('PLC_E330','Rectifier temperature high trip','HIGH')}
maint_map = {'MOTOR_OVERLOAD':('MTR-OVER','Inspect drive load, remove jam, check motor and gearbox'),
 'BEARING_VIBRATION':('MECH-VIB','Inspect bearing lubrication, alignment and mechanical looseness'),
 'SENSOR_MISREAD':('SENS-CHK','Clean and align photoeye; inspect cable and bracket'),
 'MATERIAL_SHORTAGE':('MAT-FEED','Check upstream replenishment, buffer logic and material call-off'),
 'RECTIFIER_OVERTEMP':('RECT-TEMP','Inspect cooling fan/filter, airflow and rectifier load')}

def make_data():
    records = {k: [] for k in ['downtime_events','plc_alarms','historian_signals','mes_context','maintenance_work_orders']}
    base = pd.Timestamp('2026-10-01 06:00:00')
    for i, (cause,line,machine,category,duration,note) in enumerate(scenarios, 1):
        eid=f'DT-{i:04d}'; start=base+pd.Timedelta(hours=(i-1)*7+(i%3)); end=start+pd.Timedelta(minutes=duration)
        records['downtime_events'].append(dict(event_id=eid,start_time=start,end_time=end,line=line,machine=machine,shift=['A','B','C'][(i-1)%3],duration_min=duration,reported_category=category,operator_note=note))
        ac,at,sev=alarm_map[cause]
        records['plc_alarms'].append(dict(event_id=eid,timestamp=start-pd.Timedelta(seconds=30),alarm_code=ac,alarm_text=at,severity=sev))
        fc,action=maint_map[cause]
        records['maintenance_work_orders'].append(dict(event_id=eid,work_order_id=f'WO-{i:04d}',created_at=end+pd.Timedelta(minutes=5),failure_code=fc,technician_note=note,action_taken=action))
        records['mes_context'].append(dict(event_id=eid,production_order=f'PO-{60000+i}',product=['12V-45Ah','12V-60Ah','12V-75Ah'][(i-1)%3],planned_rate_units_hr=int(rng.integers(70,121)),actual_rate_units_hr=int(rng.integers(45,91)),good_units=int(rng.integers(80,240)),reject_units=int(rng.integers(0,8)),material_status='SHORTAGE' if cause=='MATERIAL_SHORTAGE' else 'AVAILABLE',recipe_or_model=f'BAT-{(i%4)+1:02d}'))
        for off in [-10,-5,0,5,10]:
            ts=start+pd.Timedelta(minutes=off)
            vals={'motor_current':12+rng.normal(0,1),'vibration_mm_s':2.5+rng.normal(0,.3),'bearing_temp_c':48+rng.normal(0,2),'rectifier_temp_c':52+rng.normal(0,2),'buffer_level_pct':70+rng.normal(0,5),'photoeye_transitions_min':12+rng.normal(0,2)}
            if cause=='MOTOR_OVERLOAD' and off>=-5: vals['motor_current']=26+rng.normal(0,1)
            if cause=='BEARING_VIBRATION' and off>=-5: vals['vibration_mm_s']=9.5+rng.normal(0,.5); vals['bearing_temp_c']=72+rng.normal(0,2)
            if cause=='SENSOR_MISREAD' and off>=-5: vals['photoeye_transitions_min']=48+rng.normal(0,3)
            if cause=='MATERIAL_SHORTAGE' and off>=-5: vals['buffer_level_pct']=8+rng.normal(0,3)
            if cause=='RECTIFIER_OVERTEMP' and off>=-5: vals['rectifier_temp_c']=91+rng.normal(0,2)
            units={'motor_current':'A','vibration_mm_s':'mm/s','bearing_temp_c':'degC','rectifier_temp_c':'degC','buffer_level_pct':'%','photoeye_transitions_min':'transitions/min'}
            for signal,value in vals.items(): records['historian_signals'].append(dict(event_id=eid,timestamp=ts,signal=signal,value=round(float(value),2),unit=units[signal]))
    if DB.exists(): DB.unlink()
    with sqlite3.connect(DB) as conn:
        for name, rows in records.items():
            df=pd.DataFrame(rows); df.to_csv(DATA/f'{name}.csv',index=False); df.to_sql(name,conn,index=False)
            print(f'{name}: {len(df)} rows')
    print(f'SQLite database created: {DB}')

if __name__=='__main__': make_data()
