import json, os, time, random, threading, webbrowser
from datetime import datetime
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright

BASE = os.path.dirname(os.path.abspath(__file__))
SITE = 'https://eticket.railway.gov.bd/'
API = 'https://railspaapi.shohoz.com/v1.0/web/bookings/search-trips-v2'
LABELS = {'SNIGDHA':'Snigdha','S_CHAIR':'Shovon Chair','SHOVAN':'Shovon','AC_B':'AC Berth','AC_S':'AC Chair','F_BERTH':'First Berth','F_SEAT':'First Seat','F_CHAIR':'First Chair','SULOV':'Sulov'}
def norm(x): return str(x or '').strip().upper().replace('_',' ')
def beep(stop):
    try:
        import winsound
        while not stop.is_set():
            winsound.Beep(1500,350)
            if stop.wait(.12): break
            winsound.Beep(2100,350); stop.wait(.25)
    except Exception:
        while not stop.is_set(): print('\a',end='',flush=True); stop.wait(1)
def alert(cfg, m):
    msg = (f"Date: {cfg['journey_date']}\nRoute: {cfg['from_station']} → {cfg['to_station']}\n"
           f"Train: {m['train']}\nSeat type: {m['label']}\nOnline seats reported: {m['seats']}\nFare: {m['fare']}\n\n"
           "Availability can change quickly. Confirm and book manually on the official site.")
    stop=threading.Event(); t=threading.Thread(target=beep,args=(stop,),daemon=True); t.start()
    try:
        import ctypes; ctypes.windll.user32.MessageBoxW(0,msg,'Bangladesh Railway — Seat Available!',0x40|0x1000)
    finally: stop.set()
    if cfg.get('open_railway_site_on_alert',True): webbrowser.open(SITE)
def main():
    cfg=json.load(open(os.path.join(BASE,'config.json'),encoding='utf-8'))
    interval=max(10,int(cfg.get('poll_interval_seconds',10)))
    print(f"Route: {cfg['from_station']} -> {cfg['to_station']} | Date: {cfg['journey_date']} | Train: {cfg['train_name']} | Seat: {cfg['seat_class']}")
    print('Connecting to browser session. No token copy/paste required.')
    with sync_playwright() as p:
        try: browser=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        except Exception as e: raise RuntimeError(f'Could not connect to monitor browser. Close it and rerun BAT. Details: {e}')
        ctx=browser.contexts[0]; pages=ctx.pages; page=pages[0] if pages else ctx.new_page()
        if 'eticket.railway.gov.bd' not in page.url: page.goto(SITE,wait_until='domcontentloaded',timeout=30000)
        print('Waiting for the logged-in browser session...')
        while True:
            try:
                s=page.evaluate("() => ({token:localStorage.getItem('token'), uudid:localStorage.getItem('uudid')})")
                if s.get('token') and s.get('uudid'): break
            except Exception: pass
            time.sleep(2)
        print('Session detected. Checking every 10 seconds. Ctrl+C stops monitoring.')
        was=False
        while True:
            try:
                seat=str(cfg.get('seat_class','SNIGDHA')).strip().upper()
                params={'from_city':cfg['from_station'].strip(),'to_city':cfg['to_station'].strip(),'date_of_journey':cfg['journey_date'].strip(),'seat_class':seat if seat not in ('ALL','ANY') else 'SNIGDHA'}
                result=page.evaluate('''async ({url,q}) => { const token=localStorage.getItem('token'), id=localStorage.getItem('uudid'), key=localStorage.getItem('ssdk'); if(!token||!id)return {error:'LOGIN_REQUIRED'}; const h={'Accept':'application/json, text/plain, */*','Authorization':'Bearer '+token,'X-Device-Id':id,'X-Requested-With':'XMLHttpRequest'}; if(key)h['X-Device-Key']=key; const r=await fetch(url+'?'+q,{headers:h,credentials:'include'}); const t=await r.text(); let body; try{body=JSON.parse(t)}catch(e){body={raw:t.slice(0,300)}} return {status:r.status,body}; }''',{'url':API,'q':urlencode(params)})
                if result.get('error'): raise RuntimeError('Login session not found. Log in normally in the opened browser.')
                status=result.get('status')
                if status==401: raise RuntimeError('Session expired/rejected (HTTP 401). Log in again in the monitor browser.')
                if status==429: raise RuntimeError('Rate limited (HTTP 429). Stopping to avoid further requests.')
                if status!=200: raise RuntimeError(f"API returned HTTP {status}: {str(result.get('body'))[:250]}")
                payload=result.get('body') or {}; data=payload.get('data') or {}; trains=data.get('trains') or []
                wanted_train=norm(cfg.get('train_name','ALL')); wanted_class=norm(seat); matches=[]
                for tr in trains:
                    name=tr.get('trip_number') or tr.get('train_name') or tr.get('name') or 'Unknown train'
                    if wanted_train not in ('','ALL','ANY') and wanted_train not in norm(name): continue
                    for st in tr.get('seat_types') or []:
                        raw=str(st.get('type','')); cls=norm(raw)
                        if wanted_class not in ('ALL','ANY') and cls!=wanted_class: continue
                        try: count=int((st.get('seat_counts') or {}).get('online',0) or 0)
                        except (TypeError,ValueError): count=0
                        if count>0: matches.append({'train':name,'label':LABELS.get(raw.upper(),raw),'seats':count,'fare':st.get('fare','N/A')})
                now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if matches:
                    if not was: print(f'\n[{now}] SEAT FOUND: {matches[0]}'); alert(cfg,matches[0])
                    else: print(f'[{now}] Matching seat still reported; no repeat alarm.')
                    was=True
                else: was=False; print(f'[{now}] No matching seat found ({len(trains)} trains checked).')
            except KeyboardInterrupt: print('\nStopped by user.'); break
            except Exception as e:
                print(f'\nERROR: {e}')
                low=str(e).lower()
                if 'http 401' in low or 'http 429' in low or 'rate limited' in low or 'session not found' in low: break
            time.sleep(interval+random.uniform(0,1))
if __name__=='__main__':
    try: main()
    except Exception as e: print(f'\nCould not start: {e}'); input('Press Enter to exit...')
