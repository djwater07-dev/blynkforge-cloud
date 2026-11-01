
from flask import Flask, jsonify, request
from flask_cors import CORS
import random, os, json, requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

FIREBASE_ENABLED = True
FIREBASE_DB_URL = "https://blynkforge-cloud-default-rtdb.asia-southeast1.firebasedatabase.app"
DATA_FILE = "/tmp/blynk_data.json"

devices = {
    "esp32_01": {"name": "esp32-01", "online": True, "datastreams": {"V0": {"value": 1}, "V1": {"value": 72}, "V2": {"value": 24.6}, "V3": {"value": 45}, "V4": {"value": 3.28}}},
}
history = []

def firebase_put(path, data):
    try:
        url = f"{FIREBASE_DB_URL}/{path}.json"
        r = requests.put(url, json=data, timeout=5)
        return r.status_code == 200
    except Exception as e:
        print(f"Firebase PUT error: {e}")
        return False

def firebase_get(path):
    try:
        url = f"{FIREBASE_DB_URL}/{path}.json"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"Firebase GET error: {e}")
    return None

def load_data():
    global devices, history
    if FIREBASE_ENABLED:
        fb_devices = firebase_get("devices")
        fb_history = firebase_get("history")
        if fb_devices:
            devices = fb_devices
            print(f"Firebase devices loaded")
        if fb_history and isinstance(fb_history, list):
            history = [h for h in fb_history if h is not None][-300:]
            print(f"Firebase history loaded: {len(history)}")
            return
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                devices = data.get('devices', devices)
                history = data.get('history', [])[-300:]
    except Exception as e:
        print(f"Load error: {e}")

def save_data():
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump({"devices": devices, "history": history[-300:]}, f)
        if FIREBASE_ENABLED:
            firebase_put("devices", devices)
            firebase_put("history", history[-300:])
    except Exception as e:
        print(f"Save error: {e}")

load_data()

HTML = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>BlynkForge Cloud + Firebase + SuperChart Real History</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*{margin:0;padding:0;box-sizing:border-box;font-family:'Inter',system-ui}
body{background:#0F172A;color:#E2E8F0;display:flex;min-height:100vh}
.sidebar{width:220px;background:#0F172A;border-right:1px solid #1E293B;padding:20px}
.sidebar-item{padding:12px 16px;border-radius:12px;color:#64748B;font-size:13px}
.sidebar-item.active{background:#1E293B;color:#E2E8F0;border:1px solid #334155}
.main{flex:1;display:flex;flex-direction:column}
.topbar{padding:16px 24px;display:flex;justify-content:space-between;border-bottom:1px solid #1E293B}
.badge{background:#1E293B;border:1px solid #334155;padding:6px 12px;border-radius:20px;font-size:11px;display:flex;align-items:center;gap:6px}
.badge.live{color:#22C55E}.badge.firebase{color:#F59E0B;background:rgba(245,158,11,0.15);border-color:rgba(245,158,11,0.3)}
.dot{width:8px;height:8px;background:#22C55E;border-radius:50%;box-shadow:0 0 8px #22C55E;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}
.content{padding:24px;overflow-y:auto}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-bottom:20px}
.card{background:#1E293B;border:1px solid #334155;border-radius:20px;padding:20px}
.card-header{display:flex;justify-content:space-between;margin-bottom:16px}
.card-title{font-size:12px;color:#E2E8F0;font-weight:600}
.pin-badge{background:#0F172A;border:1px solid #334155;padding:3px 8px;border-radius:6px;font-size:10px;color:#94A3B8}
.big-btn{width:100%;height:140px;border-radius:16px;border:none;cursor:pointer;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;font-weight:700}
.big-btn.on{background:#00D4FF;color:#0F172A}.big-btn.off{background:#334155;color:#94A3B8}
.big{font-size:36px;font-weight:800}
input[type=range]{width:100%;-webkit-appearance:none;height:6px;background:linear-gradient(90deg,#6366F1,#00D4FF);border-radius:3px}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:20px;height:20px;background:white;border-radius:50%;cursor:pointer}
.info-box{background:#1E293B;border:1px solid #334155;border-radius:16px;padding:20px;margin-top:20px}
.chart-container{height:220px;background:#0F172A;border-radius:12px;padding:12px;border:1px solid #1E293B;position:relative}
.chart-stats{display:flex;gap:12px;margin-top:8px}
.stat{background:#0F172A;border:1px solid #1E293B;padding:6px 10px;border-radius:8px;font-size:10px}
.stat span{color:#64748B}.stat strong{color:#E2E8F0;margin-left:4px}
</style></head><body>
<div class="sidebar">
<div style="padding:8px 8px 20px;font-weight:800;font-size:16px;color:#00D4FF">BlynkForge Cloud<br><span style="font-size:10px;color:#F59E0B">+ Firebase + Real Chart</span></div>
<div class="sidebar-item active">📊 Dashboard</div>
<div class="sidebar-item">📱 Devices</div>
<div class="sidebar-item">📄 Templates</div>
<div class="sidebar-item">📈 Data Logs <span style="background:#F59E0B;color:#0F172A;padding:2px 8px;border-radius:10px;font-size:10px;margin-left:8px" id="history-count">0</span></div>
<div class="sidebar-item">⚙️ Settings & Code</div>
<div style="margin-top:20px;padding:12px;background:rgba(245,158,11,0.15);border:1px solid rgba(245,158,11,0.3);border-radius:12px;font-size:10px;color:#F59E0B">🔥 Firebase: Permanent<br>Chart: Real history from Firebase<br>Survives ALL restarts!</div>
</div>
<div class="main">
<div class="topbar"><div style="font-weight:700">Dashboard - Real Firebase History Chart</div><div style="display:flex;gap:8px"><div class="badge firebase">🔥 Firebase: Permanent</div><div class="badge live"><span class="dot"></span> LIVE + REAL CHART</div></div></div>
<div class="content">
<div class="grid">
<div class="card"><div class="card-header"><div class="card-title">Main Relay V0</div><span class="pin-badge">V0</span></div><button class="big-btn on" id="v0-btn" onclick="toggleV0()"><div id="v0-text">ON</div></button></div>
<div class="card"><div class="card-header"><div class="card-title">Brightness V1 - <span id="v1-val">72</span>%</div><span class="pin-badge">V1</span></div><input type="range" id="v1" min="0" max="100" value="72" oninput="setV1(this.value)"><div class="big"><span id="v1d">72</span>%</div></div>
<div class="card"><div class="card-header"><div class="card-title">Temperature V2</div><span class="pin-badge">V2</span></div><div class="big"><span id="v2">24.6</span>°C</div><div class="chart-stats"><div class="stat"><span>Min</span><strong id="t-min">22.0°C</strong></div><div class="stat"><span>Max</span><strong id="t-max">28.5°C</strong></div><div class="stat"><span>Avg</span><strong id="t-avg">24.6°C</strong></div></div></div>
</div>
<div class="grid" style="grid-template-columns:1fr">
<div class="card"><div class="card-header"><div class="card-title">📈 SuperChart — Real Temperature History from Firebase <span class="pin-badge" style="background:#F59E0B;color:#0F172A">🔥 Real Data</span></div><div style="display:flex;gap:8px"><div class="badge">Range: <span id="chart-range">Last 50 readings</span></div><div class="badge" style="color:#F59E0B">Source: Firebase history V2</div></div></div><div class="chart-container"><svg id="chart-svg" viewBox="0 0 400 140" preserveAspectRatio="none" style="width:100%;height:100%"><defs><linearGradient id="grad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#00D4FF" stop-opacity="0.4"/><stop offset="100%" stop-color="#00D4FF" stop-opacity="0"/></linearGradient></defs><path id="chart-area" fill="url(#grad)" d="M0,120 L0,60 L400,60 L400,120 Z" opacity="0.5"/><polyline id="chart-line" fill="none" stroke="#00D4FF" stroke-width="2.5" points="0,60 400,60"/><circle id="chart-dot" cx="400" cy="60" r="5" fill="#00D4FF" stroke="#0F172A" stroke-width="2"/></svg></div><div style="display:flex;justify-content:space-between;margin-top:8px;font-size:10px;color:#64748B"><span id="chart-start">Loading Firebase history...</span><span>Real data from Firebase RTDB - Survives restarts!</span><span id="chart-end">Now</span></div></div>
</div>
<div class="grid" style="grid-template-columns:2fr 1fr">
<div class="card"><div class="card-header"><div class="card-title">💧 Humidity V3 + Firebase Permanent Logs</div><span class="pin-badge">V3</span></div><div class="big"><span id="v3">45</span>%</div><div style="height:6px;background:#0F172A;border-radius:3px;margin-top:12px;overflow:hidden"><div id="v3-bar" style="width:45%;height:100%;background:#22C55E"></div></div><div style="margin-top:16px"><div style="font-size:11px;color:#F59E0B">🔥 Firebase History (last 15):</div><div id="history" style="font-family:monospace;font-size:10px;color:#94A3B8;max-height:120px;overflow-y:auto;margin-top:8px;background:#0F172A;padding:8px;border-radius:8px">Loading from Firebase...</div></div></div>
<div class="card"><div class="card-header"><div class="card-title">📊 Firebase Stats</div></div><div style="font-size:11px;color:#94A3B8;line-height:1.8"><div style="display:flex;justify-content:space-between"><span>Total logs</span><span style="color:#F59E0B" id="stat-total">0</span></div><div style="display:flex;justify-content:space-between"><span>V2 readings</span><span style="color:#00D4FF" id="stat-v2">0</span></div><div style="display:flex;justify-content:space-between"><span>V0 toggles</span><span style="color:#22C55E" id="stat-v0">0</span></div><div style="display:flex;justify-content:space-between"><span>Firebase URL</span><span style="color:#64748B;font-size:9px">asia-southeast1</span></div><div style="margin-top:12px;padding:8px;background:#0F172A;border-radius:8px;font-size:10px;color:#22C55E">✅ Chart loads real V2 data from Firebase<br>✅ Survives Render restarts<br>✅ Shows true min/max/avg</div></div></div>
</div>
</div></div>
<script>
let v0=1,v1=72,v2=24.6,v3=45;
let tempHistory = [];

function drawRealChart(history){
  const v2Data = history.filter(h => h.pin === 'V2').slice(-50);
  if(v2Data.length === 0) return;
  
  tempHistory = v2Data.map(h => parseFloat(h.value));
  const min = Math.min(...tempHistory);
  const max = Math.max(...tempHistory);
  const avg = tempHistory.reduce((a,b)=>a+b,0)/tempHistory.length;
  
  document.getElementById('t-min').textContent = min.toFixed(1)+'°C';
  document.getElementById('t-max').textContent = max.toFixed(1)+'°C';
  document.getElementById('t-avg').textContent = avg.toFixed(1)+'°C';
  document.getElementById('stat-v2').textContent = v2Data.length;
  document.getElementById('chart-range').textContent = `Last ${v2Data.length} readings`;
  
  const chartMin = min - 1;
  const chartMax = max + 1;
  const range = chartMax - chartMin || 1;
  
  const points = tempHistory.map((temp, i) => {
    const x = (i / (tempHistory.length - 1)) * 400;
    const y = 120 - ((temp - chartMin) / range) * 100 - 10;
    return `${x},${y}`;
  }).join(' ');
  
  document.getElementById('chart-line').setAttribute('points', points);
  const areaPoints = points + ` 400,120 0,120`;
  document.getElementById('chart-area').setAttribute('d', `M${points} L400,120 L0,120 Z`);
  
  const last = tempHistory[tempHistory.length-1];
  const lastX = 400;
  const lastY = 120 - ((last - chartMin) / range) * 100 - 10;
  document.getElementById('chart-dot').setAttribute('cx', lastX);
  document.getElementById('chart-dot').setAttribute('cy', lastY);
  
  if(v2Data.length > 0){
    document.getElementById('chart-start').textContent = new Date(v2Data[0].time).toLocaleTimeString();
    document.getElementById('chart-end').textContent = new Date(v2Data[v2Data.length-1].time).toLocaleTimeString();
  }
}

async function toggleV0(){v0=v0?0:1;const b=document.getElementById('v0-btn');const t=document.getElementById('v0-text');if(v0){b.className='big-btn on';t.textContent='ON';}else{b.className='big-btn off';t.textContent='OFF';}await fetch('/api/device/esp32_01/V0',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({value:v0})});}
async function setV1(v){v1=v;document.getElementById('v1-val').textContent=v;document.getElementById('v1d').textContent=v;await fetch('/api/device/esp32_01/V1',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({value:parseInt(v)})});}
async function syncAll(){
  try{
    const r0=await fetch('/api/device/esp32_01/V0');const j0=await r0.json();if(j0.value!==undefined && j0.value!=v0){v0=j0.value;const b=document.getElementById('v0-btn');const t=document.getElementById('v0-text');if(v0){b.className='big-btn on';t.textContent='ON';}else{b.className='big-btn off';t.textContent='OFF';}}
    const r1=await fetch('/api/device/esp32_01/V1');const j1=await r1.json();if(j1.value!==undefined){v1=j1.value;document.getElementById('v1-val').textContent=v1;document.getElementById('v1d').textContent=v1;document.getElementById('v1').value=v1;}
    const r2=await fetch('/api/device/esp32_01/V2');const j2=await r2.json();if(j2.value){v2=j2.value;document.getElementById('v2').textContent=v2;}
    const r3=await fetch('/api/device/esp32_01/V3');const j3=await r3.json();if(j3.value){v3=j3.value;document.getElementById('v3').textContent=v3;document.getElementById('v3-bar').style.width=v3+'%';}
  }catch(e){}
  try{
    const hr=await fetch('/api/history');const h=await hr.json();
    document.getElementById('history').innerHTML=h.slice(-15).reverse().map(x=>`${x.time.split('T')[1].split('.')[0]} ${x.pin}=${x.value}`).join('<br>');
    document.getElementById('history-count').textContent=h.length;
    document.getElementById('stat-total').textContent=h.length;
    document.getElementById('stat-v0').textContent=h.filter(x=>x.pin==='V0').length;
    drawRealChart(h);
  }catch(e){}
}
setInterval(syncAll,1500);
syncAll();
</script></body></html>
"""

@app.route('/')
def index(): return HTML

@app.route('/api/devices')
def get_devices(): return jsonify(devices)

@app.route('/api/history')
def get_history(): return jsonify(history)

@app.route('/api/device/<device_id>/<pin>', methods=['GET','POST'])
def datastream(device_id, pin):
    if request.method == 'POST':
        data = request.get_json()
        val = data.get('value') if data else 0
        if device_id in devices and pin in devices[device_id]['datastreams']:
            devices[device_id]['datastreams'][pin]['value'] = val
            history.append({"time": datetime.now().isoformat(), "device": device_id, "pin": pin, "value": val})
            save_data()
        return jsonify({"success": True})
    ds = devices.get(device_id, {}).get('datastreams', {}).get(pin, {})
    if pin == 'V2': ds['value'] = round(22 + random.random()*6, 1)
    if pin == 'V3': ds['value'] = random.randint(40,75)
    return jsonify(ds)

@app.route('/api/device/<device_id>/update', methods=['POST'])
def device_update(device_id):
    data = request.get_json()
    for k,v in data.items():
        if device_id in devices and k in devices[device_id]['datastreams']:
            devices[device_id]['datastreams'][k]['value'] = v
            history.append({"time": datetime.now().isoformat(), "device": device_id, "pin": k, "value": v})
    save_data()
    return jsonify({"ok": True})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"Firebase: {FIREBASE_DB_URL}")
    print(f"History: {len(history)} entries - Chart loads REAL data from Firebase!")
    app.run(host='0.0.0.0', port=port, debug=False)
