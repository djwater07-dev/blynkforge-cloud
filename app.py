
from flask import Flask, jsonify, request
from flask_cors import CORS
import random
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

devices = {
    "esp32_01": {"name": "esp32-01", "online": True, "datastreams": {"V0": {"value": 1}, "V1": {"value": 72}, "V2": {"value": 24.6}, "V3": {"value": 45}, "V4": {"value": 3.28}}},
    "esp32_02": {"name": "esp32-02", "online": False, "datastreams": {}},
    "esp32_03": {"name": "esp32-03", "online": False, "datastreams": {}},
}
history = []

HTML = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>BlynkForge Cloud - Always On</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*{margin:0;padding:0;box-sizing:border-box;font-family:'Inter',system-ui}
body{background:#0F172A;color:#E2E8F0;display:flex;min-height:100vh}
.sidebar{width:220px;background:#0F172A;border-right:1px solid #1E293B;padding:20px;display:flex;flex-direction:column;gap:8px}
.sidebar-item{padding:12px 16px;border-radius:12px;color:#64748B;font-size:13px;font-weight:500}
.sidebar-item.active{background:#1E293B;color:#E2E8F0;border:1px solid #334155}
.main{flex:1;display:flex;flex-direction:column}
.topbar{padding:16px 24px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #1E293B}
.badge{background:#1E293B;border:1px solid #334155;padding:6px 12px;border-radius:20px;font-size:11px;display:flex;align-items:center;gap:6px}
.badge.live{color:#22C55E}.dot{width:8px;height:8px;background:#22C55E;border-radius:50%;box-shadow:0 0 8px #22C55E;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}
.edit-mode{background:#00D4FF;color:#0F172A;padding:6px 14px;border-radius:20px;font-size:11px;font-weight:700;border:none}
.content{padding:24px;overflow-y:auto}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-bottom:20px}
.card{background:#1E293B;border:1px solid #334155;border-radius:20px;padding:20px}
.card-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}
.card-title{font-size:12px;color:#E2E8F0;font-weight:600;display:flex;align-items:center;gap:8px}
.card-title-icon{width:28px;height:28px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:14px}
.pin-badge{background:#0F172A;border:1px solid #334155;padding:3px 8px;border-radius:6px;font-size:10px;color:#94A3B8}
.big-btn{width:100%;height:140px;border-radius:16px;border:none;cursor:pointer;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;font-weight:700}
.big-btn.on{background:#00D4FF;color:#0F172A;box-shadow:0 8px 24px rgba(0,212,255,0.3)}
.big-btn.off{background:#334155;color:#94A3B8}
.big-btn .icon{width:56px;height:56px;border-radius:50%;border:2px solid currentColor;display:flex;align-items:center;justify-content:center;font-size:24px}
.big{font-size:36px;font-weight:800}
.small{font-size:11px;color:#64748B;margin-top:4px}
input[type=range]{width:100%;-webkit-appearance:none;height:6px;background:linear-gradient(90deg,#6366F1 0%,#00D4FF 100%);border-radius:3px;outline:none}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:20px;height:20px;background:white;border-radius:50%;cursor:pointer}
.chart-container{height:180px;background:#0F172A;border-radius:12px;padding:12px;margin-top:12px;border:1px solid #1E293B}
.led-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}
.led{background:#0F172A;border:1px solid #1E293B;border-radius:12px;padding:16px;text-align:center}
.led.on{background:rgba(34,197,94,0.1);border-color:rgba(34,197,94,0.3)}
.led-dot{width:12px;height:12px;border-radius:50%;margin:0 auto 8px;background:#334155}
.led.on .led-dot{background:#22C55E;box-shadow:0 0 12px #22C55E}
.joystick{width:100%;height:160px;background:#0F172A;border-radius:16px;position:relative;border:1px solid #1E293B;cursor:grab}
.joystick-knob{width:40px;height:40px;background:white;border-radius:50%;position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);box-shadow:0 4px 16px rgba(255,255,255,0.3)}
.info-box{background:#1E293B;border:1px solid #334155;border-radius:16px;padding:20px;margin-top:20px}
.code{background:#0F172A;padding:12px;border-radius:8px;font-family:monospace;font-size:11px;color:#00D4FF;word-break:break-all;margin-top:8px}
</style></head><body>
<div class="sidebar">
<div style="padding:8px 8px 20px;font-weight:800;font-size:16px;color:#00D4FF">BlynkForge Cloud<br><span style="font-size:10px;color:#22C55E">ALWAYS ON - Render.com</span></div>
<div class="sidebar-item active">📊 Dashboard</div>
<div class="sidebar-item">📱 Devices</div>
<div class="sidebar-item">📄 Templates</div>
<div class="sidebar-item">📈 Data Logs</div>
<div class="sidebar-item">⚙️ Settings & Code</div>
<div style="margin-top:20px;padding:12px;background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.2);border-radius:12px;font-size:10px;color:#22C55E">✅ Cloud deployed - No desktop needed!<br>ESP32 can POST from anywhere</div>
</div>
<div class="main">
<div class="topbar"><div style="display:flex;align-items:center;gap:16px"><div style="font-weight:700;font-size:18px">Dashboard</div><div style="display:flex;gap:8px"><div class="badge" style="background:white;color:#0F172A">esp32-01</div><div class="badge">esp32-02</div><div class="badge">esp32-03</div></div></div><div style="display:flex;gap:8px;align-items:center"><div class="badge live"><span class="dot"></span> LIVE - CLOUD</div><div class="badge">Render.com</div><button class="edit-mode">ALWAYS ON</button></div></div>
<div class="content">
<div class="grid">
<div class="card"><div class="card-header"><div class="card-title"><div class="card-title-icon" style="background:rgba(34,197,94,0.2);color:#22C55E">⏻</div> Main Relay</div><span class="pin-badge">V0</span></div><button class="big-btn on" id="v0-btn" onclick="toggleV0()"><div class="icon">⏻</div><div id="v0-text">ON</div><div style="font-size:10px;opacity:0.7;margin-top:4px">TAP TO TURN OFF</div></button></div>
<div class="card"><div class="card-header"><div class="card-title"><div class="card-title-icon" style="background:rgba(99,102,241,0.2);color:#6366F1">☰</div> Brightness</div><span class="pin-badge">V1</span></div><div style="display:flex;align-items:baseline;gap:8px"><div class="big"><span id="v1-val">72</span><span style="font-size:18px;color:#64748B">%</span></div></div><div style="margin-top:20px"><input type="range" id="v1" min="0" max="100" value="72" oninput="setV1(this.value)"><div style="display:flex;justify-content:space-between;font-size:10px;color:#475569;margin-top:6px"><span>0</span><span>50</span><span>100</span></div></div></div>
<div class="card"><div class="card-header"><div class="card-title"><div class="card-title-icon" style="background:rgba(245,158,11,0.2);color:#F59E0B">🌡️</div> Temperature</div><span class="pin-badge">V2</span></div><div class="big"><span id="v2">24.6</span>°C</div><div class="chart-container"><svg viewBox="0 0 400 120" preserveAspectRatio="none"><polyline id="chart-line" fill="none" stroke="#00D4FF" stroke-width="2" points="0,40 20,20 40,50 60,80 80,90 100,70 120,30 140,60 160,80 180,40 200,90 220,50 240,20 260,60 280,30 300,80 320,40 340,60 360,20 380,50 400,30"/></svg></div></div>
</div>
<div class="grid" style="grid-template-columns:2fr 1fr"><div class="card"><div class="card-header"><div class="card-title">📈 SuperChart — Temperature History <span class="pin-badge">V2</span></div><div style="display:flex;gap:8px;align-items:center"><span style="font-size:10px;color:#64748B">Range</span><select style="background:#0F172A;border:1px solid #334155;color:#94A3B8;padding:4px 8px;border-radius:6px;font-size:11px"><option>Live - 1m</option></select><div class="dot"></div></div></div><div class="chart-container" style="height:200px"><svg id="chart-svg" viewBox="0 0 400 120"><polyline id="chart-line2" fill="none" stroke="#00D4FF" stroke-width="2" points="0,40 20,20 40,50 60,80 80,90 100,70 120,30 140,60 160,80 180,40 200,90 220,50 240,20 260,60 280,30 300,80 320,40 340,60 360,20 380,50 400,30"/></svg></div></div><div style="display:flex;flex-direction:column;gap:20px"><div class="card"><div class="card-header"><div class="card-title">💧 Humidity</div><span class="pin-badge">V3</span></div><div class="big"><span id="v3">45</span>%</div><div style="height:6px;background:#0F172A;border-radius:3px;margin-top:12px;overflow:hidden"><div id="v3-bar" style="width:45%;height:100%;background:#22C55E"></div></div></div><div class="card"><div class="card-header"><div class="card-title">⚡ Voltage</div><span class="pin-badge">V4</span></div><div class="big"><span id="v4">3.28</span>V</div></div></div></div>
<div class="grid" style="grid-template-columns:1fr 1fr 1fr"><div class="card"><div class="card-header"><div class="card-title">● Status LEDs</div><span class="pin-badge">V5</span></div><div class="led-grid"><div class="led on"><div class="led-dot"></div><div style="font-size:10px">LED 1</div></div><div class="led"><div class="led-dot"></div><div style="font-size:10px">LED 2</div></div><div class="led on"><div class="led-dot"></div><div style="font-size:10px">LED 3</div></div><div class="led"><div class="led-dot"></div><div style="font-size:10px">LED 4</div></div></div></div><div class="card"><div class="card-header"><div class="card-title">🕹️ Joystick</div><span class="pin-badge">V6 X V7 Y</span></div><div class="joystick" id="joystick"><div class="joystick-knob" id="knob"></div></div></div><div class="card"><div class="card-header"><div class="card-title">💻 Cloud Info</div></div><div style="font-size:11px;color:#64748B;line-height:1.6"><div style="display:flex;justify-content:space-between"><span>ID</span><span style="color:#E2E8F0">esp32-01</span></div><div style="display:flex;justify-content:space-between"><span>Host</span><span style="color:#22C55E">Render.com - Always On</span></div><div style="display:flex;justify-content:space-between"><span>Desktop needed?</span><span style="color:#22C55E">NO!</span></div><div class="code" id="cloud-url">Deploy to get public URL</div></div></div></div>
<div class="info-box"><div class="card-title">☁️ CLOUD DEPLOYMENT - ALWAYS ON</div><div style="font-size:11px;color:#94A3B8;line-height:1.8;margin-top:8px">Your BlynkForge is now on the cloud! No desktop needed. ESP32 can POST from any WiFi.<br>Update ESP32 code: <div class="code">#define SERVER_URL "https://your-app.onrender.com/api/device/esp32_01/update"</div></div></div>
</div></div>
<script>
let v0=1,v1=72,v2=24.6,v3=45;let chartData=[40,20,50,80,90,70,30,60,80,40,90,50,20,60,30,80,40,60,20,50,30];
async function toggleV0(){v0=v0?0:1;const b=document.getElementById('v0-btn');const t=document.getElementById('v0-text');if(v0){b.className='big-btn on';t.textContent='ON';}else{b.className='big-btn off';t.textContent='OFF';}try{await fetch('/api/device/esp32_01/V0',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({value:v0})});}catch(e){}}
async function setV1(v){v1=v;document.getElementById('v1-val').textContent=v;try{await fetch('/api/device/esp32_01/V1',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({value:parseInt(v)})});}catch(e){}}
async function syncAll(){try{const r0=await fetch('/api/device/esp32_01/V0');const j0=await r0.json();if(j0.value!==undefined && j0.value!=v0){v0=j0.value;const b=document.getElementById('v0-btn');const t=document.getElementById('v0-text');if(v0){b.className='big-btn on';t.textContent='ON';}else{b.className='big-btn off';t.textContent='OFF';}}const r1=await fetch('/api/device/esp32_01/V1');const j1=await r1.json();if(j1.value!==undefined){v1=j1.value;document.getElementById('v1-val').textContent=v1;document.getElementById('v1').value=v1;}const r2=await fetch('/api/device/esp32_01/V2');const j2=await r2.json();if(j2.value){v2=j2.value;document.getElementById('v2').textContent=v2;}const r3=await fetch('/api/device/esp32_01/V3');const j3=await r3.json();if(j3.value){v3=j3.value;document.getElementById('v3').textContent=v3;document.getElementById('v3-bar').style.width=v3+'%';}chartData.shift();chartData.push(60-Math.random()*40);const pts=chartData.map((y,i)=>`${i*20},${y}`).join(' ');document.getElementById('chart-line').setAttribute('points',pts);const el2=document.getElementById('chart-line2');if(el2)el2.setAttribute('points',pts);}catch(e){}}
setInterval(syncAll,1000);
</script></body></html>
"""

@app.route('/')
def index(): return HTML

@app.route('/api/devices')
def get_devices(): return jsonify(devices)

@app.route('/api/device/<device_id>/<pin>', methods=['GET','POST'])
def datastream(device_id, pin):
    if request.method == 'POST':
        data = request.get_json()
        val = data.get('value') if data else 0
        if device_id in devices and pin in devices[device_id]['datastreams']:
            devices[device_id]['datastreams'][pin]['value'] = val
            history.append({"time": datetime.now().isoformat(), "device": device_id, "pin": pin, "value": val})
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
    return jsonify({"ok": True})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
