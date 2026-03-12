from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO, emit, join_room
import random, string, os, json
from game import GameState, Card

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'capsa2024secret')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# ── Firebase Admin (opsional, aktif jika ada env var FIREBASE_CREDENTIALS) ──
db = None
try:
    import firebase_admin
    from firebase_admin import credentials, firestore as fsdb
    _creds = os.environ.get('FIREBASE_CREDENTIALS')
    if _creds:
        firebase_admin.initialize_app(credentials.Certificate(json.loads(_creds)))
        db = fsdb.client()
        print("[FIREBASE] Firestore connected!")
except Exception as e:
    print(f"[FIREBASE] Skipped: {e}")

rooms = {}
sid_room = {}

def gen_room_id():
    while True:
        rid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if rid not in rooms: return rid

def get_room_state(room_id, for_player=None):
    room = rooms[room_id]; gs = room['game']
    state = gs.to_dict(for_player=for_player)
    state.update({'room_id': room_id, 'player_names': room['player_names'],
                  'num_players': room['num_players'], 'players_joined': len(room['players'])})
    return state

def _save_game(room_id, pnames, pemails, rankings):
    if not db: return
    try:
        import eventlet, time
        from firebase_admin import firestore as fsdb
        eventlet.sleep(0)
        gid = f"{room_id}_{int(time.time())}"
        db.collection('game_history').document(gid).set({
            'room_id': room_id, 'played_at': fsdb.SERVER_TIMESTAMP,
            'winner_name': pnames.get(rankings[0], '?') if rankings else '?',
            'rankings': [{'rank': i+1, 'name': pnames.get(idx,'?'), 'email': pemails.get(idx,'')}
                         for i, idx in enumerate(rankings)]
        })
        for rank, pidx in enumerate(rankings):
            email = pemails.get(pidx, '')
            if not email: continue
            uref = db.collection('users').document(email)
            snap = uref.get(); iw = (rank == 0)
            if snap.exists:
                d = snap.to_dict()
                w = d.get('wins',0) + (1 if iw else 0); gp = d.get('games_played',0) + 1
                uref.update({'wins': w, 'losses': gp-w, 'games_played': gp,
                             'name': pnames.get(pidx,'?'), 'last_seen': fsdb.SERVER_TIMESTAMP})
            else:
                uref.set({'name': pnames.get(pidx,'?'), 'email': email,
                          'wins': 1 if iw else 0, 'losses': 0 if iw else 1,
                          'games_played': 1, 'last_seen': fsdb.SERVER_TIMESTAMP})
        print(f"[FIREBASE] Saved {gid}")
    except Exception as e:
        print(f"[FIREBASE] Save error: {e}")

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/leaderboard')
def api_leaderboard():
    if not db: return jsonify({'leaderboard': []})
    try:
        from firebase_admin import firestore as fsdb
        docs = db.collection('users').order_by('wins', direction=fsdb.Query.DESCENDING).limit(20).stream()
        lb = []
        for i, doc in enumerate(docs):
            d = doc.to_dict(); gp = max(d.get('games_played',1), 1)
            lb.append({'rank': i+1, 'name': d.get('name','?'), 'wins': d.get('wins',0),
                       'games_played': gp, 'win_rate': round(d.get('wins',0)/gp*100, 1)})
        return jsonify({'leaderboard': lb})
    except Exception as e:
        return jsonify({'leaderboard': [], 'error': str(e)})

@app.route('/manifest.json')
def manifest():
    return jsonify({"name":"Capsa Big Two","short_name":"Capsa",
        "description":"Game kartu Capsa Big Two online multiplayer",
        "start_url":"/","display":"standalone","background_color":"#050e05",
        "theme_color":"#0a6b30","orientation":"portrait-primary",
        "icons":[{"src":"/static/icon-192.png","sizes":"192x192","type":"image/png"},
                 {"src":"/static/icon-512.png","sizes":"512x512","type":"image/png","purpose":"any maskable"}],
        "categories":["games"]})

@app.route('/sw.js')
def sw():
    return Response("""const C='capsa-v2';
self.addEventListener('install',e=>e.waitUntil(caches.open(C).then(c=>c.addAll(['/']).then(()=>self.skipWaiting()))));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==C).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{
  if(e.request.url.includes('/socket.io')||e.request.url.includes('/api/'))return;
  e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request)));
});""", mimetype='application/javascript')

@socketio.on('connect')
def on_connect(): print(f"[+] {request.sid}")

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    if sid in sid_room:
        rid = sid_room[sid]
        if rid in rooms:
            room = rooms[rid]
            if sid in room['players']:
                pidx = room['players'].pop(sid)
                socketio.emit('player_left', {'message': f"Pemain {room['player_names'].get(pidx,'')} keluar!"}, to=rid)
        del sid_room[sid]

@socketio.on('create_room')
def on_create_room(data):
    sid = request.sid
    num = int(data.get('num_players', 2)); name = data.get('name','Pemain')
    email = data.get('email',''); bot = data.get('bot_mode', False); diff = data.get('bot_diff','easy')
    rid = gen_room_id(); gs = GameState(num)
    pnames = {0: name}; pemails = {0: email}
    if bot:
        for i in range(1, num): pnames[i] = '🤖 ' + ['Bot-A','Bot-B','Bot-C'][i-1]
    rooms[rid] = {'game':gs,'players':{sid:0},'player_names':pnames,'player_emails':pemails,
                  'num_players':num,'host_sid':sid,'started':False,'bot_mode':bot,'bot_diff':diff,
                  'bot_indices':list(range(1,num)) if bot else []}
    sid_room[sid] = rid; join_room(rid)
    if bot:
        rooms[rid]['game'].start_game(); rooms[rid]['started'] = True
        emit('room_created', {'room_id':rid,'player_idx':0,'num_players':num})
        emit('game_started', get_room_state(rid, for_player=0))
        socketio.start_background_task(bot_think, rid)
    else:
        emit('room_created', {'room_id':rid,'player_idx':0,'num_players':num,'message':f'Room {rid} dibuat!'})
    print(f'[ROOM] {rid} by {name} bot={bot}')

def bot_think(room_id):
    import eventlet
    from game import can_beat
    eventlet.sleep(1.5)
    VAL = ['3','4','5','6','7','8','9','10','J','Q','K','A','2']
    while room_id in rooms:
        room = rooms[room_id]; gs = room['game']
        if gs.game_over: break
        acted = False
        if gs.phase == 'opening':
            for bi in room['bot_indices']:
                if bi in gs.opening_done or bi not in gs.active_players: continue
                eventlet.sleep(0.9)
                if room_id not in rooms: return
                gs = rooms[room_id]['game']
                if gs.phase != 'opening' or bi in gs.opening_done: continue
                hand = gs.hands[bi]; threes = [c for c in hand if c.value=='3']
                if bi == gs.opener_idx:
                    ts = next((c for c in threes if c.suit=='S'), None)
                    if ts: gs.play_opening(bi, [ts])
                else:
                    gs.play_opening(bi, [threes[0]] if threes and random.random()>0.4 else [])
                acted = True
                for psid,pidx in list(rooms.get(room_id,{}).get('players',{}).items()):
                    socketio.emit('state_update', get_room_state(room_id,for_player=pidx), to=psid)
            if not acted: eventlet.sleep(0.4)
            continue
        cp = gs.current_player
        if cp not in room['bot_indices']: eventlet.sleep(0.4); continue
        eventlet.sleep(1.2 if room['bot_diff']=='easy' else 0.7)
        if room_id not in rooms: break
        gs = rooms[room_id]['game']
        if gs.game_over: break
        cp = gs.current_player
        if cp not in room['bot_indices']: continue
        hand = gs.hands[cp]; non3 = [c for c in hand if c.value!='3']; played = False
        if gs.table_cards:
            cands = [[c] for c in non3 if can_beat([c],gs.table_cards,gs.table_type)] if gs.table_type=='single' else []
            if cands:
                ok,_ = gs.play_cards(cp, min(cands, key=lambda cs: VAL.index(cs[0].value)))
                if ok: played = True
            if not played: gs.skip_turn(cp)
        else:
            if non3:
                ok,_ = gs.play_cards(cp, [min(non3, key=lambda c: VAL.index(c.value))])
                if ok: played = True
            if not played and hand: gs.skip_turn(cp)
        for psid,pidx in list(rooms.get(room_id,{}).get('players',{}).items()):
            socketio.emit('state_update', get_room_state(room_id,for_player=pidx), to=psid)
        eventlet.sleep(0.2)

@socketio.on('join_room_game')
def on_join_room(data):
    sid = request.sid; rid = data.get('room_id','').upper().strip()
    name = data.get('name','Pemain'); email = data.get('email','')
    if rid not in rooms: emit('error',{'message':f'Room {rid} tidak ditemukan!'}); return
    room = rooms[rid]
    if room['started']: emit('error',{'message':'Game sudah dimulai!'}); return
    if len(room['players']) >= room['num_players']: emit('error',{'message':'Room sudah penuh!'}); return
    used = set(room['players'].values())
    pidx = next(i for i in range(room['num_players']) if i not in used)
    room['players'][sid]=pidx; room['player_names'][pidx]=name; room['player_emails'][pidx]=email
    sid_room[sid]=rid; join_room(rid)
    emit('joined_room',{'room_id':rid,'player_idx':pidx,'num_players':room['num_players'],'message':f'Bergabung ke room {rid}'})
    socketio.emit('player_joined',{
        'message':f"{name} bergabung! ({len(room['players'])}/{room['num_players']})",
        'players_joined':len(room['players']),'num_players':room['num_players'],'player_names':room['player_names']
    }, to=rid)

@socketio.on('start_game')
def on_start_game(data):
    sid = request.sid
    if sid not in sid_room: return
    rid = sid_room[sid]; room = rooms[rid]
    if room['host_sid'] != sid: emit('error',{'message':'Hanya host yang bisa mulai!'}); return
    if len(room['players']) < 2: emit('error',{'message':'Minimal 2 pemain!'}); return
    room['game'].start_game(); room['started'] = True
    for psid,pidx in room['players'].items():
        socketio.emit('game_started', get_room_state(rid,for_player=pidx), to=psid)

def _broadcast(rid):
    room = rooms.get(rid)
    if not room: return
    gs = room['game']
    for psid,pidx in list(room['players'].items()):
        socketio.emit('state_update', get_room_state(rid,for_player=pidx), to=psid)
    if gs.game_over:
        socketio.start_background_task(_save_game, rid, room['player_names'],
                                       room.get('player_emails',{}), gs.rankings)

@socketio.on('play_cards')
def on_play_cards(data):
    sid = request.sid
    if sid not in sid_room: return
    rid = sid_room[sid]; room = rooms[rid]; pidx = room['players'].get(sid)
    if pidx is None: return
    cards = [Card.from_dict(c) for c in data.get('cards',[])]
    ok, msg = room['game'].play_cards(pidx, cards)
    if not ok: emit('error',{'message':msg}); return
    _broadcast(rid)

@socketio.on('skip_turn')
def on_skip_turn(data):
    sid = request.sid
    if sid not in sid_room: return
    rid = sid_room[sid]; room = rooms[rid]; pidx = room['players'].get(sid)
    if pidx is None: return
    ok, msg = room['game'].skip_turn(pidx)
    if not ok: emit('error',{'message':msg}); return
    _broadcast(rid)

@socketio.on('get_state')
def on_get_state(data):
    sid = request.sid
    if sid not in sid_room: return
    rid = sid_room[sid]; pidx = rooms[rid]['players'].get(sid, 0)
    emit('state_update', get_room_state(rid, for_player=pidx))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"[SERVER] Port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
