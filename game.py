import random

SUITS = ['S', 'H', 'D', 'C']
SUIT_SYMBOLS = {'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣'}
SUIT_COLORS = {'S': 'black', 'H': 'red', 'D': 'red', 'C': 'black'}
VALUES = ['3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A', '2']
VALUE_ORDER = {v: i for i, v in enumerate(VALUES)}
LETTER_VALUES = ['J', 'Q', 'K', 'A']
NUMBER_VALUES = ['3', '4', '5', '6', '7', '8', '9', '10']


def effective_hand(hand):
    """Kartu efektif = semua kartu kecuali 3 (kartu 3 = pengecoh, tidak dihitung)."""
    return [c for c in hand if c.value != '3']


def check_instant_lose(hand):
    """
    Cek kondisi langsung kalah:
    - Sisa efektif = 0 tapi ada kartu 3 → sisa pengecoh saja → kalah
    - Sisa efektif = tepat 1 kartu dan itu adalah '2' → tidak bisa menang → kalah
    Returns: (is_lose, reason_msg)
    """
    eff = effective_hand(hand)
    if len(eff) == 0 and len(hand) > 0:
        return True, "Sisa kartu 3 semua (pengecoh) — langsung kalah!"
    if len(eff) == 1 and eff[0].value == '2':
        return True, "Sisa kartu 2 saja — tidak bisa menang dengan kartu 2 terakhir!"
    return False, ""


class Card:
    def __init__(self, suit, value):
        self.suit = suit
        self.value = value

    def display(self):
        return f"{self.value}{SUIT_SYMBOLS[self.suit]}"

    def to_dict(self):
        return {
            'suit': self.suit,
            'value': self.value,
            'display': self.display(),
            'color': SUIT_COLORS[self.suit]
        }

    @staticmethod
    def from_dict(d):
        return Card(d['suit'], d['value'])

    def __eq__(self, other):
        return self.suit == other.suit and self.value == other.value

    def __hash__(self):
        return hash((self.suit, self.value))


class Deck:
    def __init__(self):
        self.cards = [Card(s, v) for s in SUITS for v in VALUES]
        random.shuffle(self.cards)

    def deal(self, num_players):
        hands = [[] for _ in range(num_players)]
        for i, card in enumerate(self.cards):
            hands[i % num_players].append(card)
        return hands


def card_value(card):
    return VALUE_ORDER[card.value]


def is_all_same_suit(cards):
    return len(set(c.suit for c in cards)) == 1


def is_valid_straight(cards):
    if len(cards) < 3:
        return False
    if not is_all_same_suit(cards):
        return False
    # No mixing numbers and letters
    all_num = all(c.value in NUMBER_VALUES and c.value != '3' for c in cards)
    all_let = all(c.value in LETTER_VALUES for c in cards)
    if not all_num and not all_let:
        return False
    vals = sorted([VALUE_ORDER[c.value] for c in cards])
    for i in range(1, len(vals)):
        if vals[i] != vals[i - 1] + 1:
            return False
    return True


def is_jqka(cards):
    if len(cards) != 4:
        return False
    vals = sorted([c.value for c in cards])
    return vals == ['A', 'J', 'K', 'Q'] and is_all_same_suit(cards)


def get_play_type(cards):
    n = len(cards)
    if n == 0:
        return None, 0
    if n == 1:
        return 'single', card_value(cards[0])
    if n == 2:
        if cards[0].value == cards[1].value:
            return 'double', card_value(cards[0])
        return None, 0
    if n == 3:
        vals = [c.value for c in cards]
        if len(set(vals)) == 1:
            return 'triple', card_value(cards[0])
        if is_valid_straight(cards):
            return 'straight3', card_value(sorted(cards, key=card_value)[-1])
        return None, 0
    if n == 4:
        if is_jqka(cards):
            return 'jqka', 99
        vals = [c.value for c in cards]
        if len(set(vals)) == 1:
            return 'bomb4', card_value(cards[0])
        if is_valid_straight(cards):
            return 'straight4', card_value(sorted(cards, key=card_value)[-1])
        return None, 0
    if n >= 5:
        if is_valid_straight(cards):
            return 'straight5plus', card_value(sorted(cards, key=card_value)[-1])
        return None, 0
    return None, 0


def can_beat(play_cards, table_cards, table_type):
    if not table_cards or table_type is None:
        return True
    play_type, play_val = get_play_type(play_cards)
    if play_type is None:
        return False
    _, t_val = get_play_type(table_cards)
    if table_type == 'single' and table_cards[0].value == '2':
        return play_type in ['bomb4', 'jqka']
    if table_type == 'double' and all(c.value == '2' for c in table_cards):
        return False
    if play_type != table_type:
        return False
    if table_type in ['straight3', 'straight4', 'straight5plus']:
        if len(play_cards) != len(table_cards):
            return False
    return play_val > t_val


# ── GAME PHASES ──
PHASE_OPENING = 'opening'  # Ronde pembukaan: buang kartu 3
PHASE_NORMAL  = 'normal'   # Main normal


class GameState:
    def __init__(self, num_players):
        self.num_players = num_players
        self.hands = []
        self.current_player = 0
        self.table_cards = []
        self.table_type = None
        self.rankings = []
        self.active_players = []
        self.stopped_players = set()
        self.skipped_this_round = set()
        self.last_player_played = None
        self.started = False
        self.game_over = False
        self.message = ""
        self.phase = PHASE_OPENING
        self.opening_done = set()
        self.opener_idx = 0         # pemegang 3♠, main pertama di fase normal
        self.decoy_cards = []
        self.opening_table = []     # kartu 3 yang dibuang saat ronde pembukaan       # kartu 3 pengecoh yang baru dibuang (tampil sebentar)

    def start_game(self):
        deck = Deck()
        self.hands = deck.deal(self.num_players)
        self.rankings = []
        self.stopped_players = set()
        self.skipped_this_round = set()
        self.active_players = list(range(self.num_players))
        self.table_cards = []
        self.table_type = None
        self.last_player_played = None
        self.started = True
        self.game_over = False
        self.phase = PHASE_OPENING
        self.opening_done = set()
        self.decoy_cards = []
        self.opening_table = []

        # Cari pemegang 3♠
        for i, hand in enumerate(self.hands):
            for card in hand:
                if card.value == '3' and card.suit == 'S':
                    self.current_player = i
                    self.opener_idx = i
                    self.message = f"🃏 Ronde pembukaan! Semua boleh buang kartu 3 atau skip. Pemain {i+1} wajib keluarkan 3♠!"
                    return

    # ── OPENING PHASE ──
    def play_opening(self, player_idx, selected_cards):
        """
        Fase opening: SERENTAK, tidak bergilir.
        - Siapa saja boleh keluarkan kartu 3 milik mereka atau skip KAPAN SAJA
        - Pemegang 3♠ WAJIB keluarkan 3♠ sebelum opening selesai
        - Opening selesai setelah semua pemain sudah aksi (buang/skip)
        - Setelah opening selesai: ronde normal dimulai, pemegang 3♠ main pertama
        """
        # Cek sudah aksi belum
        if player_idx in self.opening_done:
            return False, "Kamu sudah aksi di ronde pembukaan!"

        if player_idx == self.opener_idx:
            # Pemegang 3♠ wajib keluarkan 3♠, tidak boleh skip
            if not selected_cards:
                return False, "Kamu pegang 3♠, wajib keluarkan 3♠ di ronde pembukaan!"
            if len(selected_cards) != 1 or not (selected_cards[0].value == '3' and selected_cards[0].suit == 'S'):
                return False, "Kamu harus keluarkan 3♠ (bukan kartu lain)!"
        else:
            # Pemain lain: boleh keluarkan kartu 3 atau skip
            if selected_cards:
                if len(selected_cards) != 1 or selected_cards[0].value != '3':
                    return False, "Di ronde pembukaan hanya boleh keluarkan 1 kartu 3!"

        # Buang kartu dari tangan
        for card in selected_cards:
            self.hands[player_idx].remove(card)

        if selected_cards:
            msg = f"Pemain {player_idx+1} buang {selected_cards[0].display()}"
            # Tampilkan kartu yang dibuang di meja (opening_table)
            self.opening_table.append(selected_cards[0])
        else:
            msg = f"Pemain {player_idx+1} simpan kartu 3 (skip)"

        self.opening_done.add(player_idx)

        # Cek apakah semua pemain sudah aksi
        if len(self.opening_done) >= len(self.active_players):
            self.phase = PHASE_NORMAL
            self.current_player = self.opener_idx
            self.table_cards = []
            self.table_type = None
            self.skipped_this_round = set()
            self.last_player_played = None
            self.opening_table = []  # bersihkan meja opening
            msg += f" | ✅ Ronde pembukaan selesai! Pemain {self.opener_idx+1} mulai ronde normal!"
        else:
            sisa = len(self.active_players) - len(self.opening_done)
            msg += f" | Menunggu {sisa} pemain lagi..."

        self.message = msg
        return True, msg

    # ── NORMAL PHASE ──
    def play_cards(self, player_idx, selected_cards):
        if self.phase == PHASE_OPENING:
            return self.play_opening(player_idx, selected_cards)

        if player_idx != self.current_player:
            return False, "Bukan giliran kamu!"
        if not selected_cards:
            return False, "Pilih kartu dulu!"

        # ── KARTU 3 SPECIAL: selalu pengecoh, kapanpun dikeluarkan ──
        # 1 kartu 3 = pengecoh: dibuang ke meja tapi giliran tetap di pemain ini
        # Meja tidak berubah (kartu 3 tidak bisa dilawan, tidak bisa melawan)
        is_three_decoy = (
            len(selected_cards) == 1 and
            selected_cards[0].value == '3'
        )

        if is_three_decoy:
            card3 = selected_cards[0]
            self.hands[player_idx].remove(card3)
            self.decoy_cards = [card3]
            msg = f"Pemain {player_idx+1} buang {card3.display()} (pengecoh) — harus main lagi!"

            # Cek apakah sisa kartu menyebabkan langsung kalah
            is_lose, lose_msg = check_instant_lose(self.hands[player_idx])
            if is_lose:
                self.hands[player_idx] = []  # kosongkan
                msg += f" | 💀 {lose_msg} Pemain {player_idx+1} KALAH!"
                if player_idx in self.active_players:
                    self.active_players.remove(player_idx)
                if len(self.active_players) <= 1:
                    self.game_over = True
                if not self.game_over:
                    self._next_turn(from_player=player_idx)
                self.message = msg
                return True, msg

            # Giliran TIDAK pindah, meja TIDAK berubah
            self.message = msg
            return True, msg

        play_type, play_val = get_play_type(selected_cards)
        if play_type is None:
            return False, "Kombinasi kartu tidak valid!"

        is_free = not self.table_cards

        if not is_free:
            if not can_beat(selected_cards, self.table_cards, self.table_type):
                return False, "Kartu tidak bisa mengalahkan kartu di meja!"

        # Efek bom terhadap pemain yang keluarkan kartu 2
        bom_victim = None
        if not is_free and self.table_type == 'single' and self.table_cards[0].value == '2':
            if play_type in ['bomb4', 'jqka']:
                bom_victim = self.last_player_played

        # ── CEK WAJIB MAIN 2 DULUAN ──
        # Kalau sisa efektif tepat 2 kartu dan salah satunya adalah '2',
        # pemain WAJIB keluarkan '2' duluan — tidak boleh keluarkan kartu lain
        eff_before = effective_hand(self.hands[player_idx])
        if len(eff_before) == 2:
            has_two = any(c.value == '2' for c in eff_before)
            playing_two = any(c.value == '2' for c in selected_cards)
            if has_two and not playing_two:
                return False, "⚠️ Sisa 2 kartu efektif dan ada kartu 2 — wajib keluarkan 2 duluan atau kamu kalah!"

        # Hapus kartu dari tangan
        for card in selected_cards:
            self.hands[player_idx].remove(card)

        prev_last = self.last_player_played
        self.table_cards = selected_cards
        self.table_type = play_type
        self.last_player_played = player_idx
        self.skipped_this_round = set()
        self.decoy_cards = []  # hapus pengecoh saat main asli
        msg = f"Pemain {player_idx+1} main: {', '.join(c.display() for c in selected_cards)}"

        # Efek bom
        if bom_victim is not None and bom_victim in self.active_players:
            self.active_players.remove(bom_victim)
            msg += f" | 💥 BOM! Pemain {bom_victim+1} langsung kalah!"
            if len(self.active_players) <= 1:
                self.game_over = True

        # Efek berhentiin
        if play_type == 'straight4' and prev_last is not None and prev_last != player_idx:
            if prev_last in self.active_players:
                self.stopped_players.add(prev_last)
                msg += f" | 🛑 Pemain {prev_last+1} di-stop 1 putaran!"

        # ── CEK LANGSUNG KALAH setelah main ──
        # Kalau sisa kartu efektif = hanya 2, atau sisa hanya 3-3 (pengecoh semua)
        is_lose, lose_msg = check_instant_lose(self.hands[player_idx])
        if is_lose and len(self.hands[player_idx]) > 0:
            msg += f" | 💀 {lose_msg} Pemain {player_idx+1} KALAH!"
            self.hands[player_idx] = []
            if player_idx in self.active_players:
                self.active_players.remove(player_idx)
            if len(self.active_players) <= 1:
                self.game_over = True
            if not self.game_over:
                self._next_turn(from_player=player_idx)
            self.message = msg
            return True, msg

        # Cek habis kartu
        if len(self.hands[player_idx]) == 0:
            self.rankings.append(player_idx)
            if player_idx in self.active_players:
                self.active_players.remove(player_idx)
            rank = len(self.rankings)
            msg += f" | 🏆 Pemain {player_idx+1} Juara {rank}!"
            if len(self.active_players) <= 1:
                self.game_over = True
            if not self.game_over:
                self._next_turn(from_player=player_idx)
            self.message = msg
            return True, msg

        self._next_turn()
        self.message = msg
        return True, msg

    def skip_turn(self, player_idx):
        if self.phase == PHASE_OPENING:
            # Skip di opening = simpan kartu 3 (boleh kapan saja, tidak perlu giliran)
            return self.play_opening(player_idx, [])

        if player_idx != self.current_player:
            return False, "Bukan giliran kamu!"
        self.skipped_this_round.add(player_idx)
        self.decoy_cards = []  # hapus pengecoh saat skip
        msg = f"Pemain {player_idx+1} skip"
        self._next_turn()

        others = [p for p in self.active_players if p != self.last_player_played]
        if others and all(p in self.skipped_this_round for p in others):
            self.table_cards = []
            self.table_type = None
            self.skipped_this_round = set()
            msg += f" | Meja reset! Pemain {self.current_player+1} bebas main!"

        self.message = msg
        return True, msg

    def _next_turn(self, from_player=None):
        active = self.active_players
        if not active:
            return
        start = from_player if from_player is not None else self.current_player
        if start not in active:
            start = active[0]
        start_idx = active.index(start)
        for i in range(1, len(active) + 1):
            nxt = active[(start_idx + i) % len(active)]
            if nxt in self.stopped_players:
                self.stopped_players.discard(nxt)
                continue
            self.current_player = nxt
            return

    def get_rankings_display(self):
        result = []
        for rank, pidx in enumerate(self.rankings):
            result.append({'rank': rank+1, 'player': pidx+1, 'status': f'Juara {rank+1}'})
        for pidx in self.active_players:
            result.append({'rank': self.num_players, 'player': pidx+1, 'status': 'Kalah'})
        return result

    def to_dict(self, for_player=None):
        return {
            'num_players': self.num_players,
            'current_player': self.current_player,
            'table_cards': [c.to_dict() for c in self.table_cards],
            'table_type': self.table_type,
            'rankings': self.rankings,
            'active_players': self.active_players,
            'stopped_players': list(self.stopped_players),
            'game_over': self.game_over,
            'message': self.message,
            'phase': self.phase,
            'opener_idx': self.opener_idx,
            'opening_done': list(self.opening_done),
            'decoy_cards': [c.to_dict() for c in self.decoy_cards],
            'opening_table': [c.to_dict() for c in self.opening_table],
            'hand': [c.to_dict() for c in self.hands[for_player]] if for_player is not None else [],
            'hand_counts': [len(h) for h in self.hands],
        }
