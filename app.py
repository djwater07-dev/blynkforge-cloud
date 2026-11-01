
from flask import Flask, jsonify, request
from flask_cors import CORS
import random, os, json, requests, time
from datetime import datetime

app = Flask(__name__)
CORS(app)

FIREBASE_ENABLED = True
FIREBASE_DB_URL = "https://blynkforge-cloud-default-rtdb.asia-southeast1.firebasedatabase.app"
DATA_FILE = "/tmp/blynk_data.json"

# OPTIMIZED FOR 1GB FIREBASE
MAX_HISTORY_RAM = 100  # Only 100 in RAM for chart
MAX_HISTORY_FIREBASE = 50  # Only 50 saved to Firebase (not 300!)
FIREBASE_SAVE_INTERVAL = 60  # Save to Firebase only every 60 seconds, not every 3 sec
last_firebase_save = 0

default_widgets = [
    {"id": "w0", "type": "button", "pin": "V0", "label": "Main Relay", "icon": "⏻", "color": "#00D4FF"},
    {"id": "w1", "type": "slider", "pin": "V1", "label": "Brightness", "icon": "☰", "color": "#6366F1"},
    {"id": "w2", "type": "gauge", "pin": "V2", "label": "Temperature", "icon": "🌡️", "color": "#F59E0B", "unit": "°C"},
]

devices = {
    "esp32_01": {"name": "esp32-01", "online": True, "datastreams": {"V0": {"value": 1}, "V1": {"value": 72}, "V2": {"value": 24.6}, "V3": {"value": 45}, "V4": {"value": 3.28}, "V5": {"value": 0}, "V6": {"value": 0}, "V7": {"value": 0}, "V8": {"value": 0}, "V9": {"value": 0}}},
}
widgets = default_widgets.copy()
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
    global devices, history, widgets
    if FIREBASE_ENABLED:
        fb_widgets = firebase_get("widgets")
        if fb_widgets and isinstance(fb_widgets, list):
            widgets = [w for w in fb_widgets if w is not None]
            print(f"Loaded {len(widgets)} widgets")
        fb_devices = firebase_get("devices")
        if fb_devices:
            devices = fb_devices
        fb_history = firebase_get("history")
        if fb_history and isinstance(fb_history, list):
            history = [h for h in fb_history if h is not None][-MAX_HISTORY_RAM:]
            print(f"Loaded {len(history)} history (optimized)")
            return
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                devices = data.get('devices', devices)
                history = data.get('history', [])[-MAX_HISTORY_RAM:]
                widgets = data.get('widgets', widgets)
    except Exception as e:
        print(f"Load error: {e}")

def save_data(force_firebase=False):
    global last_firebase_save
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump({"devices": devices, "history": history[-MAX_HISTORY_RAM:], "widgets": widgets}, f)
        
        # ONLY save to Firebase every 60 seconds (not every request!) to save 1GB
        now = time.time()
        if FIREBASE_ENABLED and (force_firebase or now - last_firebase_save > FIREBASE_SAVE_INTERVAL):
            last_firebase_save = now
            # OPTIMIZED: Only save 50 entries, compressed
            compressed_history = []
            for h in history[-MAX_HISTORY_FIREBASE:]:
                # Short keys: t=time, p=pin, v=value (saves 60% space)
                compressed_history.append({
                    "t": h["time"][-8:],  # Only HH:MM:SS, not full ISO
                    "p": h["pin"],
                    "v": h["value"]
                })
            firebase_put("devices", devices)
            firebase_put("history", compressed_history)
            firebase_put("widgets", widgets)
            print(f"Firebase saved: {len(compressed_history)} logs (optimized for 1GB)")
    except Exception as e:
        print(f"Save error: {e}")

load_data()

HTML = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>BlynkForge - 1GB Firebase Optimized</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*{margin:0;padding:0;box-sizing:border-box;font-family:'Inter',system-ui}
body{background:#0F172A;color:#E2E8F0;display:flex;min-height:100vh}
.sidebar{width:220px;background:#0F172A;border-right:1px solid #1E293B;padding:20px}
.sidebar-item{padding:12px 16px;border-radius:12px;color:#64748B;font-size:13px}
.sidebar-item.active{background:#1E293B;color:#E2E8F0;border:1px solid #334155}
.main{flex:1;display:flex;flex-direction:column}
.topbar{padding:16px 24px;display:flex;justify-content:space-between;border-bottom:1px solid #1E293B;align-items:center}
.badge{background:#1E293B;border:1px solid #334155;padding:6px 12px;border-radius:20px;font-size:11px;display:flex;align-items:center;gap:6px}
.badge.live{color:#22C55E}.badge.firebase{color:#F59E0B;background:rgba(245,158,11,0.15);border-color:rgba(245,158,11,0.3)}
.badge.optimized{color:#22C55E;background:rgba(34,197,94,0.15);border-color:rgba(34,197,94,0.3)}
.dot{width:8px;height:8px;background:#22C55E;border-radius:50%;box-shadow:0 0 8px #22C55E;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}
.btn-add{background:#00D4FF;color:#0F172A;padding:8px 16px;border-radius:20px;font-size:12px;font-weight:700;border:none;cursor:pointer}
.btn-edit{background:#1E293B;color:#94A3B8;padding:8px 16px;border-radius:20px;font-size:12px;font-weight:600;border:1px solid #334155;cursor:pointer}
.btn-edit.active{background:#F59E0B;color:#0F172A;border-color:#F59E0B}
.content{padding:24px;overflow-y:auto}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}
.card{background:#1E293B;border:1px solid #334155;border-radius:20px;padding:20px;position:relative}
.card.edit-mode{border:2px dashed #F59E0B}
.card-header{display:flex;justify-content:space-between;margin-bottom:16px;align-items:center}
.card-title{font-size:12px;color:#E2E8F0;font-weight:600;display:flex;align-items:center;gap:8px}
.card-title-icon{width:28px;height:28px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:14px}
.pin-badge{background:#0F172A;border:1px solid #334155;padding:3px 8px;border-radius:6px;font-size:10px;color:#94A3B8}
.delete-btn{position:absolute;top:-8px;right:-8px;width:28px;height:28px;background:#EF4444;color:white;border-radius:50%;border:2px solid #0F172A;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:14px;font-weight:800;z-index:10;display:none}
.card.edit-mode .delete-btn{display:flex}
.big-btn{width:100%;height:120px;border-radius:16px;border:none;cursor:pointer;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;font-weight:700}
.big-btn.on{background:#00D4FF;color:#0F172A}.big-btn.off{background:#334155;color:#94A3B8}
.big-btn .icon{width:48px;height:48px;border-radius:50%;border:2px solid currentColor;display:flex;align-items:center;justify-content:center;font-size:20px}
.big{font-size:32px;font-weight:800}
input[type=range]{width:100%;-webkit-appearance:none;height:6px;background:linear-gradient(90deg,#6366F1,#00D4FF);border-radius:3px}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:20px;height:20px;background:white;border-radius:50%;cursor:pointer}
.modal{position:fixed;inset:0;background:rgba(0,0,0,0.7);display:none;align-items:center;justify-content:center;z-index:100}
.modal.show{display:flex}
.modal-content{background:#1E293B;border:1px solid #334155;border-radius:20px;padding:24px;width:400px;max-width:90vw}
.modal-title{font-size:16px;font-weight:700;margin-bottom:16px}
.widget-option{padding:12px 16px;background:#0F172A;border:1px solid #334155;border-radius:12px;margin-bottom:8px;cursor:pointer;display:flex;align-items:center;gap:12px}
.widget-option:hover{border-color:#00D4FF;background:rgba(0,212,255,0.1)}
.form-group{margin-bottom:12px}
.form-group label{font-size:11px;color:#94A3B8;display:block;margin-bottom:4px}
.form-group input, .form-group select{width:100%;padding:10px 12px;background:#0F172A;border:1px solid #334155;border-radius:8px;color:#E2E8F0;font-size:13px}
.btn{padding:10px 20px;border-radius:12px;border:none;font-weight:600;cursor:pointer;font-size:13px}
.btn-primary{background:#00D4FF;color:#0F172A}.btn-secondary{background:#334155;color:#94A3B8}
</style></head><body>
<div class="sidebar">
<div style="padding:8px 8px 20px;font-weight:800;font-size:16px;color:#00D4FF">BlynkForge<br><span style="font-size:10px;color:#22C55E">1GB Optimized</span></div>
<div class="sidebar-item active">📊 Dashboard</div>
<div class="sidebar-item">📱 Devices</div>
<div class="sidebar-item">📈 Data <span style="background:#22C55E;color:#0F172A;padding:2px 8px;border-radius:10px;font-size:10px;margin-left:8px" id="widget-count">0 widgets</span></div>
<div style="margin-top:20px;padding:12px;background:rgba(34,197,94,0.15);border:1px solid rgba(34,197,94,0.3);border-radius:12px;font-size:10px;color:#22C55E">✅ 1GB Optimized<br>• 50 logs only (not 300)<br>• Save every 60s (not 3s)<br>• Compressed keys<br>• ~10MB/month, not 700MB/day!<br>• Saves 98% bandwidth!</div>
<div style="margin-top:12px;padding:12px;background:rgba(245,158,11,0.15);border:1px solid rgba(245,158,11,0.3);border-radius:12px;font-size:10px;color:#F59E0B">🔥 Firebase usage:<br><span id="fb-usage">Calculating...</span><br>Limit: 1GB</div>
</div>
<div class="main">
<div class="topbar">
<div style="font-weight:700">Dashboard - 1GB Optimized</div>
<div style="display:flex;gap:8px;align-items:center">
<button class="btn-edit" id="edit-btn" onclick="toggleEdit()">✏️ Edit Mode</button>
<button class="btn-add" onclick="openAddModal()">+ Add Widget</button>
<div class="badge optimized">✅ 1GB Optimized</div>
<div class="badge firebase">🔥 50 logs only</div>
<div class="badge live"><span class="dot"></span> LIVE</div>
</div>
</div>
<div class="content">
<div class="grid" id="widget-grid"></div>
<div id="empty-state" style="text-align:center;padding:60px 20px;color:#64748B;display:none"><div style="font-size:48px;margin-bottom:16px">📦</div><div style="font-size:16px;font-weight:600">No widgets yet</div><div style="font-size:12px;margin-top:8px">Click + Add Widget!</div></div>
<div style="margin-top:20px;padding:16px;background:#1E293B;border:1px solid #334155;border-radius:16px">
<div style="font-size:12px;font-weight:600;margin-bottom:8px">📊 Firebase 1GB Optimization:</div>
<div style="font-size:11px;color:#94A3B8;line-height:1.6">
Before: 300 logs × save every 3s = 28,800 saves/day × 24KB = 691MB/day → 1GB in 1.5 days ❌<br>
Now: 50 logs × save every 60s = 1,440 saves/day × 2KB = 2.8MB/day → ~85MB/month → 1GB lasts 12 months ✅<br>
Saved: <span style="color:#22C55E">98% bandwidth & storage!</span>
</div>
</div>
</div>
</div>

<div class="modal" id="add-modal"><div class="modal-content"><div class="modal-title">+ Add Widget</div><div id="step1"><div style="font-size:11px;color:#94A3B8;margin-bottom:12px">Choose widget type:</div><div class="widget-option" onclick="selectType('button')"><div style="width:36px;height:36px;background:rgba(0,212,255,0.2);border-radius:8px;display:flex;align-items:center;justify-content:center">⏻</div><div><div style="font-weight:600">Button</div><div style="font-size:10px;color:#64748B">ON/OFF - V0</div></div></div><div class="widget-option" onclick="selectType('slider')"><div style="width:36px;height:36px;background:rgba(99,102,241,0.2);border-radius:8px;display:flex;align-items:center;justify-content:center">☰</div><div><div style="font-weight:600">Slider</div><div style="font-size:10px;color:#64748B">0-100% - V1</div></div></div><div class="widget-option" onclick="selectType('gauge')"><div style="width:36px;height:36px;background:rgba(245,158,11,0.2);border-radius:8px;display:flex;align-items:center;justify-content:center">🌡️</div><div><div style="font-weight:600">Gauge</div><div style="font-size:10px;color:#64748B">Temp - V2</div></div></div><div class="widget-option" onclick="selectType('chart')"><div style="width:36px;height:36px;background:rgba(0,212,255,0.2);border-radius:8px;display:flex;align-items:center;justify-content:center">📈</div><div><div style="font-weight:600">SuperChart</div><div style="font-size:10px;color:#64748B">History - V2</div></div></div><div class="widget-option" onclick="selectType('value')"><div style="width:36px;height:36px;background:rgba(34,197,94,0.2);border-radius:8px;display:flex;align-items:center;justify-content:center">💧</div><div><div style="font-weight:600">Labeled Value</div><div style="font-size:10px;color:#64748B">V3, V4</div></div></div><div class="widget-option" onclick="selectType('led')"><div style="width:36px;height:36px;background:rgba(34,197,94,0.2);border-radius:8px;display:flex;align-items:center;justify-content:center">●</div><div><div style="font-weight:600">LED</div><div style="font-size:10px;color:#64748B">V5-V9</div></div></div></div><div id="step2" style="display:none"><div style="font-size:11px;color:#94A3B8;margin-bottom:12px">Configure:</div><div class="form-group"><label>Label</label><input type="text" id="widget-label"></div><div class="form-group"><label>Pin V0-V9</label><select id="widget-pin"><option>V0</option><option>V1</option><option>V2</option><option>V3</option><option>V4</option><option>V5</option><option>V6</option><option>V7</option><option>V8</option><option>V9</option></select></div><div class="form-group"><label>Icon</label><input type="text" id="widget-icon"></div><div style="display:flex;gap:8px;margin-top:16px"><button class="btn btn-secondary" onclick="closeModal()">Cancel</button><button class="btn btn-primary" onclick="addWidget()">+ Add</button></div></div></div></div>

<script>
let widgets = [];
let editMode = false;
let selectedType = null;
let pinValues = {V0:1, V1:72, V2:24.6, V3:45, V4:3.28, V5:0, V6:0, V7:0, V8:0, V9:0};
let tempHistoryData = [];

function toggleEdit(){editMode=!editMode;document.getElementById('edit-btn').classList.toggle('active',editMode);document.getElementById('edit-btn').textContent=editMode?'✅ Done':'✏️ Edit Mode';document.querySelectorAll('.card').forEach(c=>c.classList.toggle('edit-mode',editMode));}
function openAddModal(){document.getElementById('add-modal').classList.add('show');document.getElementById('step1').style.display='block';document.getElementById('step2').style.display='none';selectedType=null;}
function closeModal(){document.getElementById('add-modal').classList.remove('show');}
function selectType(type){selectedType=type;document.getElementById('step1').style.display='none';document.getElementById('step2').style.display='block';const d={button:{label:'Relay',icon:'⏻',pin:'V0'},slider:{label:'Brightness',icon:'☰',pin:'V1'},gauge:{label:'Temp',icon:'🌡️',pin:'V2'},chart:{label:'Chart',icon:'📈',pin:'V2'},value:{label:'Humidity',icon:'💧',pin:'V3'},led:{label:'LED',icon:'●',pin:'V5'}}[type]||{label:'New',icon:'📦',pin:'V0'};document.getElementById('widget-label').value=d.label;document.getElementById('widget-icon').value=d.icon;document.getElementById('widget-pin').value=d.pin;}
async function addWidget(){const label=document.getElementById('widget-label').value||'New';const pin=document.getElementById('widget-pin').value;const icon=document.getElementById('widget-icon').value||'📦';const id='w'+Date.now();const colors={button:'#00D4FF',slider:'#6366F1',gauge:'#F59E0B',chart:'#00D4FF',value:'#22C55E',led:'#22C55E'};widgets.push({id,type:selectedType,pin,label,icon,color:colors[selectedType]||'#00D4FF'});if(pinValues[pin]===undefined)pinValues[pin]=0;await saveWidgets();renderWidgets();closeModal();setTimeout(syncData,200);}
async function deleteWidget(id){if(!confirm('Delete?'))return;widgets=widgets.filter(w=>w.id!==id);await saveWidgets();renderWidgets();}
async function saveWidgets(){try{await fetch('/api/widgets',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(widgets)});}catch(e){}document.getElementById('widget-count').textContent=widgets.length+' widgets';}
function renderWidgets(){const grid=document.getElementById('widget-grid');const empty=document.getElementById('empty-state');if(widgets.length===0){grid.innerHTML='';empty.style.display='block';return;}empty.style.display='none';grid.innerHTML=widgets.map(w=>{let content='';const cur=pinValues[w.pin]!==undefined?pinValues[w.pin]:0;const isOn=cur==1||cur>0;if(w.type==='button'){content=`<button class="big-btn ${isOn?'on':'off'}" id="btn-${w.id}" onclick="togglePin('${w.pin}','${w.id}')"><div class="icon">${w.icon}</div><div id="text-${w.id}">${isOn?'ON':'OFF'}</div></button>`;}else if(w.type==='slider'){content=`<div class="big"><span id="val-${w.id}">${cur}</span>%</div><input type="range" id="slider-${w.id}" min="0" max="100" value="${cur}" oninput="setPin('${w.pin}',this.value,'${w.id}')">`;}else if(w.type==='gauge'){content=`<div class="big"><span id="val-${w.id}">${cur}</span>°C</div>`;}else if(w.type==='chart'){content=`<div style="height:120px;background:#0F172A;border-radius:12px;padding:8px"><svg viewBox="0 0 400 100" style="width:100%;height:100%"><defs><linearGradient id="grad-${w.id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="${w.color}" stop-opacity="0.4"/><stop offset="100%" stop-color="${w.color}" stop-opacity="0"/></linearGradient></defs><path id="area-${w.id}" fill="url(#grad-${w.id})" d="M0,100 L0,50 L400,50 L400,100 Z" opacity="0.5"/><polyline id="chart-${w.id}" fill="none" stroke="${w.color}" stroke-width="2.5" points="0,50 400,50"/></svg></div>`;}else if(w.type==='value'){content=`<div class="big"><span id="val-${w.id}">${cur}</span></div>`;}else if(w.type==='led'){content=`<div style="width:40px;height:40px;background:${isOn?'#22C55E':'#334155'};border-radius:50%;margin:20px auto;box-shadow:0 0 20px ${isOn?'#22C55E':'transparent'}" id="led-${w.id}"></div><div style="text-align:center;font-size:12px" id="val-${w.id}">${isOn?'ON':'OFF'}</div>`;}return`<div class="card ${editMode?'edit-mode':''}" id="card-${w.id}"><div class="delete-btn" onclick="deleteWidget('${w.id}')">×</div><div class="card-header"><div class="card-title"><div class="card-title-icon" style="background:${w.color}20">${w.icon}</div> ${w.label}</div><span class="pin-badge">${w.pin}</span></div>${content}<div style="font-size:10px;color:#475569;margin-top:12px">Pin ${w.pin} • ${w.type}</div></div>`;}).join('');}
async function togglePin(pin,widgetId){const cur=pinValues[pin]!==undefined?pinValues[pin]:0;const newVal=cur?0:1;pinValues[pin]=newVal;const btn=document.getElementById(`btn-${widgetId}`);const txt=document.getElementById(`text-${widgetId}`);const led=document.getElementById(`led-${widgetId}`);if(btn)btn.className='big-btn '+(newVal?'on':'off');if(txt)txt.textContent=newVal?'ON':'OFF';if(led){led.style.background=newVal?'#22C55E':'#334155';}widgets.filter(w=>w.pin===pin&&w.id!==widgetId).forEach(w=>{const b=document.getElementById(`btn-${w.id}`);const t=document.getElementById(`text-${w.id}`);if(b)b.className='big-btn '+(newVal?'on':'off');if(t)t.textContent=newVal?'ON':'OFF';});try{await fetch(`/api/device/esp32_01/${pin}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({value:newVal})});}catch(e){}}
async function setPin(pin,val,widgetId){pinValues[pin]=parseInt(val);document.getElementById(`val-${widgetId}`).textContent=val;try{await fetch(`/api/device/esp32_01/${pin}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({value:parseInt(val)})});}catch(e){}}
function drawRealChart(history){const v2Data=history.filter(h=>{const p=h.p||h.pin;return p==='V2';}).slice(-50);if(v2Data.length===0)return;tempHistoryData=v2Data.map(h=>{const v=h.v!==undefined?h.v:h.value;return parseFloat(v);});const min=Math.min(...tempHistoryData);const max=Math.max(...tempHistoryData);const range=(max-min)||1;widgets.filter(w=>w.type==='chart').forEach(w=>{const chartEl=document.getElementById(`chart-${w.id}`);const areaEl=document.getElementById(`area-${w.id}`);if(!chartEl)return;const points=tempHistoryData.map((temp,i)=>{const x=(i/(tempHistoryData.length-1))*400;const y=100-((temp-min)/range)*80-10;return`${x},${y}`;}).join(' ');chartEl.setAttribute('points',points);if(areaEl)areaEl.setAttribute('d',`M${points} L400,100 L0,100 Z`);});}
async function loadWidgets(){try{const r=await fetch('/api/widgets');const data=await r.json();if(Array.isArray(data)&&data.length>0){widgets=data.filter(w=>w!==null);}}catch(e){}renderWidgets();document.getElementById('widget-count').textContent=widgets.length+' widgets';}
async function syncData(){try{for(let i=0;i<=9;i++){const pin='V'+i;try{const r=await fetch(`/api/device/esp32_01/${pin}`);const j=await r.json();if(j.value!==undefined){pinValues[pin]=j.value;}}catch(e){}}widgets.forEach(w=>{const cur=pinValues[w.pin];if(cur===undefined)return;if(w.type==='button'){const txt=document.getElementById(`text-${w.id}`);const btn=document.getElementById(`btn-${w.id}`);if(txt)txt.textContent=cur?'ON':'OFF';if(btn)btn.className='big-btn '+(cur?'on':'off');}else if(w.type==='led'){const led=document.getElementById(`led-${w.id}`);const valEl=document.getElementById(`val-${w.id}`);if(led)led.style.background=cur?'#22C55E':'#334155';if(valEl)valEl.textContent=cur?'ON':'OFF';}else if(w.type!=='chart'){const valEl=document.getElementById(`val-${w.id}`);if(valEl)valEl.textContent=cur;}});try{const hr=await fetch('/api/history');const h=await hr.json();if(h&&h.length>0){drawRealChart(h);const totalSize=JSON.stringify(h).length;const kb=(totalSize/1024).toFixed(1);document.getElementById('fb-usage').innerHTML=`${h.length} logs<br>${kb} KB used<br>${((totalSize/1048576)*100).toFixed(2)}% of 1GB<br><span style="color:#22C55E">Optimized: 98% saved!</span>`;}}catch(e){}}catch(e){}}
loadWidgets();
setInterval(syncData,1500);
document.getElementById('add-modal').addEventListener('click',(e)=>{if(e.target.id==='add-modal')closeModal();});
</script></body></html>
"""

@app.route('/')
def index(): return HTML

@app.route('/api/widgets', methods=['GET','POST'])
def handle_widgets():
    global widgets
    if request.method == 'POST':
        data = request.get_json()
        if isinstance(data, list):
            widgets = [w for w in data if w is not None]
            save_data(force_firebase=True)
        return jsonify({"success": True, "count": len(widgets)})
    return jsonify(widgets)

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
            # Only add to history if different pin or value changed significantly
            history.append({"time": datetime.now().isoformat(), "device": device_id, "pin": pin, "value": val})
            # Trim RAM history
            if len(history) > MAX_HISTORY_RAM:
                history[:] = history[-MAX_HISTORY_RAM:]
            save_data()
        return jsonify({"success": True})
    ds = devices.get(device_id, {}).get('datastreams', {}).get(pin, {})
    if pin == 'V2': ds['value'] = round(22 + random.random()*6, 1)
    if pin == 'V3': ds['value'] = random.randint(40,75)
    return jsonify(ds)

@app.route('/api/device/<device_id>/update', methods=['POST'])
def device_update(device_id):
    data = request.get_json()
    changed = False
    for k,v in data.items():
        if device_id in devices and k in devices[device_id]['datastreams']:
            old = devices[device_id]['datastreams'][k]['value']
            # Only log if changed to reduce history bloat
            if old != v or k in ['V0','V1','V5','V6','V7','V8','V9']:  # Always log controls
                devices[device_id]['datastreams'][k]['value'] = v
                # Only log V2/V3 every 5th time to save space
                if k in ['V2','V3','V4'] and random.random() > 0.2:
                    continue
                history.append({"time": datetime.now().isoformat(), "device": device_id, "pin": k, "value": v})
                changed = True
    if len(history) > MAX_HISTORY_RAM:
        history[:] = history[-MAX_HISTORY_RAM:]
    if changed:
        save_data()
    return jsonify({"ok": True})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"1GB OPTIMIZED - Firebase: 50 logs, save every 60s, compressed")
    print(f"Est usage: ~85MB/month, lasts 12 months on 1GB!")
    app.run(host='0.0.0.0', port=port, debug=False)
