# Downtime Investigator & Root Cause Intelligence Agent

Local VS Code PoC for battery manufacturing. It simulates PLC alarms, MES context, historian time series, downtime events and maintenance work orders. Feeds are written to CSV and SQLite, then analyzed by auditable rules and an optional LangChain tool-calling agent.

## What is simulated
- `downtime_events.csv`: event timestamps, line, machine, duration and operator note
- `plc_alarms.csv`: alarm code, timestamp and severity
- `mes_context.csv`: order, product, rate, rejects and material status
- `historian_signals.csv`: signal values before/during/after event
- `maintenance_work_orders.csv`: failure code, technician note and action
- `plant.db`: SQLite database with the same five tables

All data is synthetic. It demonstrates the investigation workflow, not validated root causes or savings. Rule scores are evidence weights, not probabilities. No PLC write path is included.

## 1. Setup (Windows PowerShell)
Open this folder in VS Code, then Terminal > New Terminal:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```
If PowerShell blocks activation, use Command Prompt and run `.venv\Scripts\activate.bat`.

## 2. Generate simulated data
```powershell
python generate_data.py
```
Expected: 18 incidents, 18 PLC alarms, 540 historian rows (18 events × 6 signals × 5 time points), 18 MES rows and 18 work orders, plus CSV files and `data/plant.db`.

## 3. Configure LLM access
Copy `.env.example` to `.env` and set your key and a model available to your API account:
```text
OPENAI_API_KEY=your_actual_key
OPENAI_MODEL=gpt-4.1-mini
```
API billing is separate from ChatGPT subscription. Never commit `.env` or expose the key.

## 4. Launch dashboard
```powershell
streamlit run app.py
```
Open the localhost URL printed in the terminal, usually `http://localhost:8501`. Evidence and deterministic ranking tabs work without an API key; the LangChain investigation tab needs the key.

## 5. Try these events
| Event | Simulated signature | Expected evidence |
|---|---|---|
| DT-0001 | Motor overload | PLC_A102; current rises above 22 A |
| DT-0002 | Bearing vibration | PLC_M241; vibration rises above 7 mm/s |
| DT-0003 | Sensor misread | PLC_S017; photoeye transitions spike |
| DT-0004 | Material shortage | MES shortage; buffer level falls |
| DT-0005 | Rectifier overtemperature | PLC_E330; temperature rises above 85°C |

Example prompt: `Investigate DT-0005. Build a timeline, rank hypotheses, show evidence by source, list data gaps, and recommend safe next checks.`

## 6. Architecture
1. `generate_data.py` creates synthetic feed records.
2. SQLite represents a small SQL data layer; CSVs are easy to inspect.
3. `rca_engine.py` retrieves evidence and ranks hypotheses with deterministic rules.
4. `agent.py` exposes tools to LangChain's agent loop; the LLM assembles a structured investigation from tool outputs.
5. `app.py` presents event evidence, signal trends and investigation results.

## 7. Next steps toward a plant pilot
1. Align event-time windows, clock synchronization and timezone rules.
2. Replace simulator with approved, read-only MES SQL views, historian exports/APIs and SCADA alarm exports.
3. Confirm signal thresholds with Controls/Maintenance; never assume the demo thresholds are real machine limits.
4. Capture confirmed causes and corrective-action outcomes to build a labelled evaluation set.
5. Evaluate top-1/top-3 cause accuracy, evidence completeness, false positives and investigation time saved.
6. Add identity/access controls, audit logs, secrets management and OT security review before deployment.

## Troubleshooting
- Missing DB: run `python generate_data.py`.
- Missing API key: create `.env` from `.env.example`.
- Agent/API error: check package installation, key, billing and model access.
- For future repeatability, pin versions after testing in your environment.
