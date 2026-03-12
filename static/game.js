// ── STATE ──
let socket = null;
let myPlayerIdx = null;
let myRoomId = null;
let isHost = false;
let selectedCards = [];
let handCards = [];
let selectedNum = 2;
let currentState = null;

// ── SOCKET INIT ──
function initSocket() {
  if (socket) socket.disconnect();
  socket = io();

  socket.on('connect', () => console.log('Connected:', socket.id));
  socket.on('disconnect', () => showToast('Koneksi terputus!'));

  socket.on('room_created', (data) => {
    myPlayerIdx = data.player_idx;
    myRoomId = data.room_id;
    isHost = true;
    document.getElementById('lobby-room-code').textContent = data.room_id;
    document.getElementById('lobby-status-text').textContent = `Menunggu ${data.num_players - 1} pemain lagi...`;
    showScreen('screen-lobby');
  });

  socket.on('joined_room', (data) => {
    myPlayerIdx = data.player_idx;
    myRoomId = data.room_id;
    isHost = false;
    document.getElementById('lobby-room-code').textContent = data.room_id;
    document.getElementById('lobby-status-text').textContent = data.message;
    showScreen('screen-lobby');
  });

  socket.on('player_joined', (data) => {
    document.getElementById('lobby-status-text').textContent = data.message;
    updateLobbyPlayers(data.player_names, data.num_players);
    if (isHost && data.players_joined >= 2) {
      document.getElementById('btn-start-game').style.display = 'block';
    }
  });

  socket.on('player_left', (data) => showToast(data.message));

  socket.on('game_started', (data) => {
    currentState = data;
    showScreen('screen-game');
    renderGame(data);
  });

  socket.on('state_update', (data) => {
    currentState = data;
    renderGame(data);
    if (data.game_over) showGameOver(data);
  });

  socket.on('error', (data) => showToast(data.message));
}

// ── SCREEN NAV ──
function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}

function goCreateRoom() {
  const name = document.getElementById('input-name').value.trim();
  if (!name) { showToast('Masukkan nama dulu!'); return; }
  initSocket();
  showScreen('screen-create');
}

function goJoinRoom() {
  const name = document.getElementById('input-name').value.trim();
  if (!name) { showToast('Masukkan nama dulu!'); return; }
  initSocket();
  showScreen('screen-join');
}

function selectNum(n) {
  selectedNum = n;
  [2,3,4].forEach(i => {
    document.getElementById(`num-${i}`).classList.toggle('selected', i === n);
  });
}

function createRoom() {
  const name = document.getElementById('input-name').value.trim() || 'Pemain 1';
  socket.emit('create_room', { num_players: selectedNum, name });
}

function joinRoom() {
  const name = document.getElementById('input-name').value.trim() || 'Pemain';
  const roomId = document.getElementById('input-room-id').value.trim().toUpperCase();
  if (!roomId) { showToast('Masukkan kode room!'); return; }
  socket.emit('join_room_game', { room_id: roomId, name });
}

function startGame() {
  socket.emit('start_game', {});
}

function backToMenu() {
  document.getElementById('modal-gameover').classList.remove('active');
  selectedCards = [];
  handCards = [];
  myPlayerIdx = null;
  myRoomId = null;
  isHost = false;
  currentState = null;
  if (socket) socket.disconnect();
  showScreen('screen-menu');
}

// ── LOBBY ──
function updateLobbyPlayers(playerNames, numPlayers) {
  const list = document.getElementById('lobby-players-list');
  list.innerHTML = '';
  for (let i = 0; i < numPlayers; i++) {
    const li = document.createElement('li');
    const name = playerNames[i] || '...';
    li.textContent = `P${i+1}: ${name}${i === myPlayerIdx ? ' (Kamu)' : ''}`;
    list.appendChild(li);
  }
}

// ── GAME RENDER ──
function renderGame(state) {
  selectedCards = [];

  // Turn indicator
  const isMyTurn = state.current_player === myPlayerIdx;
  const turnEl = document.getElementById('game-turn-text');
  const pName = state.player_names ? state.player_names[state.current_player] : `Pemain ${state.current_player+1}`;
  if (isMyTurn) {
    turnEl.textContent = '🟢 GILIRAN KAMU!';
    turnEl.className = 'turn-indicator my-turn';
  } else {
    turnEl.textContent = `Giliran ${pName}`;
    turnEl.className = 'turn-indicator';
  }
  document.getElementById('game-room-id').textContent = `Room: ${state.room_id || myRoomId}`;

  // Opponents
  const oppArea = document.getElementById('opponents-area');
  oppArea.innerHTML = '';
  for (let i = 0; i < state.num_players; i++) {
    if (i === myPlayerIdx) continue;
    const div = document.createElement('div');
    div.className = 'opponent-card';
    if (i === state.current_player) div.classList.add('active-turn');
    if (state.stopped_players && state.stopped_players.includes(i)) div.classList.add('stopped');
    const pn = state.player_names ? state.player_names[i] : `P${i+1}`;
    const isActive = state.active_players.includes(i);
    const cardCount = state.hand_counts ? state.hand_counts[i] : '?';
    let status = '';
    if (!isActive) {
      const rank = state.rankings.indexOf(i);
      status = rank >= 0 ? `🏆${rank+1}` : '❌';
    } else if (state.stopped_players && state.stopped_players.includes(i)) {
      status = '🛑';
    } else if (i === state.current_player) {
      status = '▶';
    }
    div.innerHTML = `<div>${pn}</div><div>${cardCount}🃏</div><div>${status}</div>`;
    oppArea.appendChild(div);
  }

  // Table cards
  const tableArea = document.getElementById('table-cards-area');
  tableArea.innerHTML = '';
  if (state.table_cards && state.table_cards.length > 0) {
    state.table_cards.forEach(c => {
      tableArea.appendChild(makeCardEl(c, false));
    });
  } else {
    tableArea.innerHTML = '<span style="color:rgba(255,255,255,0.3);font-size:0.85em;">Meja kosong</span>';
  }

  // Table type badge
  const typeLabels = {
    'single':'Single','double':'Double','triple':'Triple',
    'bomb4':'💣 BOM 4x','straight3':'Straight 3','straight4':'Straight 4 🛑',
    'straight5plus':'💣 Straight 5+','jqka':'💣 J-Q-K-A'
  };
  const badge = document.getElementById('table-type-badge');
  badge.textContent = state.table_type ? (typeLabels[state.table_type] || state.table_type) : '';

  // Message
  document.getElementById('msg-bar').textContent = state.message || '-';

  // Hand
  handCards = state.hand || [];
  renderHand(handCards);

  // Buttons
  const amActive = state.active_players.includes(myPlayerIdx);
  document.getElementById('btn-play').disabled = !(isMyTurn && amActive);
  document.getElementById('btn-skip').disabled = !(isMyTurn && amActive);
  document.getElementById('btn-play').style.opacity = (isMyTurn && amActive) ? '1' : '0.5';
  document.getElementById('btn-skip').style.opacity = (isMyTurn && amActive) ? '1' : '0.5';
}

function renderHand(cards) {
  const area = document.getElementById('hand-cards-area');
  area.innerHTML = '';
  selectedCards = [];

  // Sort: nilai kecil -> besar, suit S H D C
  const valueOrder = ['4','5','6','7','8','9','10','J','Q','K','A','2'];
  const suitOrder = ['S','H','D','C'];
  const sorted = [...cards].sort((a, b) => {
    const vi = valueOrder.indexOf(a.value) - valueOrder.indexOf(b.value);
    if (vi !== 0) return vi;
    return suitOrder.indexOf(a.suit) - suitOrder.indexOf(b.suit);
  });

  document.getElementById('hand-count').textContent = sorted.length;
  sorted.forEach(c => {
    const el = makeCardEl(c, true);
    el.onclick = () => toggleCard(el, c);
    area.appendChild(el);
  });
}

function makeCardEl(card, clickable) {
  const el = document.createElement('div');
  el.className = `card ${card.color}${!clickable ? ' table-card' : ''}`;
  el.innerHTML = `<div class="card-value">${card.value}</div><div class="card-suit">${card.display.replace(card.value,'')}</div>`;
  el.dataset.suit = card.suit;
  el.dataset.value = card.value;
  return el;
}

function toggleCard(el, card) {
  const isMyTurn = currentState && currentState.current_player === myPlayerIdx;
  const amActive = currentState && currentState.active_players.includes(myPlayerIdx);
  if (!isMyTurn || !amActive) return;

  const idx = selectedCards.findIndex(c => c.suit === card.suit && c.value === card.value);
  if (idx >= 0) {
    selectedCards.splice(idx, 1);
    el.classList.remove('selected');
  } else {
    selectedCards.push(card);
    el.classList.add('selected');
  }
}

// ── ACTIONS ──
function playCards() {
  if (selectedCards.length === 0) { showToast('Pilih kartu dulu!'); return; }
  socket.emit('play_cards', { cards: selectedCards });
  selectedCards = [];
}

function skipTurn() {
  socket.emit('skip_turn', {});
}

// ── GAME OVER ──
function showGameOver(state) {
  const list = document.getElementById('rankings-list');
  list.innerHTML = '';
  const rankings = state.rankings || [];
  const active = state.active_players || [];
  const names = state.player_names || {};

  rankings.forEach((pidx, i) => {
    const li = document.createElement('li');
    li.className = i === 0 ? 'juara1' : '';
    li.textContent = `${i === 0 ? '🥇' : i === 1 ? '🥈' : '🥉'} Juara ${i+1}: ${names[pidx] || 'P'+(pidx+1)}`;
    list.appendChild(li);
  });
  active.forEach(pidx => {
    const li = document.createElement('li');
    li.className = 'kalah';
    li.textContent = `❌ Kalah: ${names[pidx] || 'P'+(pidx+1)}`;
    list.appendChild(li);
  });

  document.getElementById('modal-gameover').classList.add('active');
}

// ── TOAST ──
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2500);
}
