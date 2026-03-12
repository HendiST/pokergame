from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Rectangle
import threading

from game import GameState, Card, get_play_type, SUIT_SYMBOLS
from network import GameServer, GameClient, get_local_ip

# Warna tema
BG_COLOR = (0.1, 0.35, 0.1, 1)       # hijau gelap
TABLE_COLOR = (0.15, 0.5, 0.15, 1)   # hijau meja
CARD_BG = (1, 1, 1, 1)               # putih
CARD_SEL = (1, 0.9, 0.2, 1)          # kuning selected
BTN_PLAY = (0.2, 0.7, 0.2, 1)        # hijau
BTN_SKIP = (0.8, 0.3, 0.1, 1)        # oranye
BTN_MAIN = (0.15, 0.5, 0.8, 1)       # biru
TEXT_DARK = (0.1, 0.1, 0.1, 1)
TEXT_LIGHT = (1, 1, 1, 1)


def make_btn(text, bg_color, text_color=(1,1,1,1), font_size=16, **kwargs):
    btn = Button(
        text=text,
        background_normal='',
        background_color=bg_color,
        color=text_color,
        font_size=font_size,
        bold=True,
        **kwargs
    )
    return btn


# ─── SCREEN: MENU UTAMA ───────────────────────────────────────────────────────
class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*BG_COLOR)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)

        layout = BoxLayout(orientation='vertical', padding=40, spacing=20)

        layout.add_widget(Label(
            text='🃏 POKER GAME',
            font_size=42, bold=True,
            color=TEXT_LIGHT, size_hint_y=0.3
        ))

        btn_host = make_btn('BUAT ROOM (HOST)', BTN_MAIN, font_size=20, size_hint_y=0.15)
        btn_join = make_btn('GABUNG ROOM', BTN_PLAY, font_size=20, size_hint_y=0.15)
        btn_solo = make_btn('MAIN SENDIRI (TEST)', (0.5, 0.5, 0.5, 1), font_size=18, size_hint_y=0.12)

        btn_host.bind(on_press=self.go_host)
        btn_join.bind(on_press=self.go_join)
        btn_solo.bind(on_press=self.go_solo)

        layout.add_widget(btn_host)
        layout.add_widget(btn_join)
        layout.add_widget(btn_solo)
        layout.add_widget(Label(size_hint_y=0.28))

        self.add_widget(layout)

    def _update_rect(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos

    def go_host(self, *args):
        self.manager.current = 'host'

    def go_join(self, *args):
        self.manager.current = 'join'

    def go_solo(self, *args):
        app = App.get_running_app()
        app.mode = 'solo'
        app.num_players = 2
        app.player_idx = 0
        app.game_state = GameState(2)
        app.game_state.start_game()
        self.manager.current = 'game'


# ─── SCREEN: HOST ────────────────────────────────────────────────────────────
class HostScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*BG_COLOR)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)

        layout = BoxLayout(orientation='vertical', padding=30, spacing=15)

        layout.add_widget(Label(text='BUAT ROOM', font_size=28, bold=True,
                                color=TEXT_LIGHT, size_hint_y=0.12))

        ip = get_local_ip()
        self.ip_label = Label(
            text=f'IP Kamu: [b]{ip}[/b]\n(Bagikan ke teman)',
            markup=True, font_size=18, color=(1, 1, 0.5, 1),
            size_hint_y=0.15
        )
        layout.add_widget(self.ip_label)

        layout.add_widget(Label(text='Jumlah Pemain:', color=TEXT_LIGHT,
                                font_size=18, size_hint_y=0.08))

        num_layout = BoxLayout(size_hint_y=0.12, spacing=10)
        self.num_btns = []
        for n in [2, 3, 4]:
            btn = make_btn(str(n), BTN_MAIN if n != 2 else BTN_PLAY)
            btn.num = n
            btn.bind(on_press=self.select_num)
            self.num_btns.append(btn)
            num_layout.add_widget(btn)
        self.selected_num = 2
        layout.add_widget(num_layout)

        self.status_label = Label(
            text='Menunggu teman konek...',
            color=(0.8, 1, 0.8, 1), font_size=16, size_hint_y=0.2
        )
        layout.add_widget(self.status_label)

        btn_start = make_btn('MULAI GAME', BTN_PLAY, font_size=20, size_hint_y=0.13)
        btn_start.bind(on_press=self.start_host)
        layout.add_widget(btn_start)

        btn_back = make_btn('← KEMBALI', (0.4, 0.4, 0.4, 1), font_size=16, size_hint_y=0.1)
        btn_back.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        layout.add_widget(btn_back)

        self.add_widget(layout)

    def _update_rect(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos

    def select_num(self, btn):
        self.selected_num = btn.num
        for b in self.num_btns:
            b.background_color = BTN_PLAY if b.num == self.selected_num else BTN_MAIN

    def start_host(self, *args):
        app = App.get_running_app()
        app.mode = 'host'
        app.num_players = self.selected_num
        app.player_idx = 0
        app.game_state = GameState(self.selected_num)

        app.server = GameServer()
        app.server.start(self.selected_num, app.on_server_action)

        if self.selected_num == 1:
            app.game_state.start_game()
            self.manager.current = 'game'
        else:
            self.status_label.text = (
                f'Server jalan!\nIP: {get_local_ip()}:9999\n'
                f'Menunggu {self.selected_num-1} teman...'
            )
            app.server.on_all_connected = self.on_all_connected

    def on_all_connected(self):
        Clock.schedule_once(lambda dt: self._start_game(), 0)

    def _start_game(self):
        app = App.get_running_app()
        app.game_state.start_game()
        state = app.game_state.to_dict(for_player=0)
        app.server.broadcast({'type': 'game_start', 'state': state})
        for pid in range(1, app.num_players):
            s = app.game_state.to_dict(for_player=pid)
            app.server.send_to(pid, {'type': 'game_start', 'state': s})
        self.manager.current = 'game'


# ─── SCREEN: JOIN ────────────────────────────────────────────────────────────
class JoinScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*BG_COLOR)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)

        layout = BoxLayout(orientation='vertical', padding=30, spacing=15)

        layout.add_widget(Label(text='GABUNG ROOM', font_size=28, bold=True,
                                color=TEXT_LIGHT, size_hint_y=0.12))

        layout.add_widget(Label(text='Masukkan IP Host:', color=TEXT_LIGHT,
                                font_size=18, size_hint_y=0.08))

        self.ip_input = TextInput(
            hint_text='contoh: 192.168.43.1',
            font_size=22, multiline=False,
            size_hint_y=0.12
        )
        layout.add_widget(self.ip_input)

        self.status_label = Label(
            text='', color=(1, 1, 0.5, 1), font_size=16, size_hint_y=0.2
        )
        layout.add_widget(self.status_label)

        btn_join = make_btn('KONEK', BTN_PLAY, font_size=20, size_hint_y=0.13)
        btn_join.bind(on_press=self.do_join)
        layout.add_widget(btn_join)

        btn_back = make_btn('← KEMBALI', (0.4, 0.4, 0.4, 1), font_size=16, size_hint_y=0.1)
        btn_back.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        layout.add_widget(btn_back)

        layout.add_widget(Label(size_hint_y=0.25))
        self.add_widget(layout)

    def _update_rect(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos

    def do_join(self, *args):
        ip = self.ip_input.text.strip()
        if not ip:
            self.status_label.text = 'Masukkan IP host dulu!'
            return
        self.status_label.text = f'Connecting ke {ip}...'
        app = App.get_running_app()
        app.mode = 'client'
        app.client = GameClient()
        try:
            app.client.connect(ip, on_message=app.on_client_message)
            self.status_label.text = 'Terhubung! Menunggu host mulai...'
        except Exception as e:
            self.status_label.text = f'Gagal konek: {e}'


# ─── SCREEN: GAME ────────────────────────────────────────────────────────────
class CardButton(Button):
    def __init__(self, card, **kwargs):
        super().__init__(**kwargs)
        self.card = card
        self.selected = False
        self.text = card.display()
        self.font_size = 18
        self.bold = True
        self.background_normal = ''
        self.background_color = CARD_BG
        self.color = TEXT_DARK
        self.size_hint = (None, None)
        self.size = (60, 85)

    def toggle_select(self):
        self.selected = not self.selected
        self.background_color = CARD_SEL if self.selected else CARD_BG


class GameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.card_buttons = []
        self.selected_cards = []
        self._build_ui()

    def _build_ui(self):
        with self.canvas.before:
            Color(*BG_COLOR)
            self.bg_rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_bg, pos=self._update_bg)

        root = BoxLayout(orientation='vertical', padding=8, spacing=6)

        # ── Info bar atas
        self.info_label = Label(
            text='', font_size=14, color=TEXT_LIGHT,
            size_hint_y=0.06, bold=True
        )
        root.add_widget(self.info_label)

        # ── Status pemain lain
        self.players_label = Label(
            text='', font_size=13, color=(0.8, 1, 0.8, 1),
            size_hint_y=0.08
        )
        root.add_widget(self.players_label)

        # ── Meja (kartu yang dimainkan)
        table_box = BoxLayout(orientation='vertical', size_hint_y=0.22)
        table_box.add_widget(Label(text='── MEJA ──', font_size=13,
                                   color=(1, 1, 0.5, 1), size_hint_y=0.3))
        self.table_scroll = ScrollView(size_hint_y=0.7)
        self.table_layout = BoxLayout(
            orientation='horizontal', spacing=6,
            size_hint_x=None, padding=5
        )
        self.table_layout.bind(minimum_width=self.table_layout.setter('width'))
        self.table_scroll.add_widget(self.table_layout)
        table_box.add_widget(self.table_scroll)
        root.add_widget(table_box)

        # ── Pesan game
        self.msg_label = Label(
            text='', font_size=13, color=(1, 0.9, 0.5, 1),
            size_hint_y=0.06
        )
        root.add_widget(self.msg_label)

        # ── Kartu tangan pemain
        hand_box = BoxLayout(orientation='vertical', size_hint_y=0.3)
        hand_box.add_widget(Label(text='── KARTU KAMU ──', font_size=13,
                                  color=(0.8, 1, 0.8, 1), size_hint_y=0.2))
        self.hand_scroll = ScrollView(size_hint_y=0.8)
        self.hand_layout = BoxLayout(
            orientation='horizontal', spacing=5,
            size_hint_x=None, padding=5
        )
        self.hand_layout.bind(minimum_width=self.hand_layout.setter('width'))
        self.hand_scroll.add_widget(self.hand_layout)
        hand_box.add_widget(self.hand_scroll)
        root.add_widget(hand_box)

        # ── Tombol aksi
        btn_row = BoxLayout(size_hint_y=0.1, spacing=10, padding=(10, 0))
        self.btn_play = make_btn('▶ MAIN', BTN_PLAY, font_size=18)
        self.btn_skip = make_btn('⏭ SKIP', BTN_SKIP, font_size=18)
        self.btn_play.bind(on_press=self.do_play)
        self.btn_skip.bind(on_press=self.do_skip)
        btn_row.add_widget(self.btn_play)
        btn_row.add_widget(self.btn_skip)
        root.add_widget(btn_row)

        self.add_widget(root)

    def _update_bg(self, *args):
        self.bg_rect.size = self.size
        self.bg_rect.pos = self.pos

    def on_enter(self):
        self.refresh_ui()

    def refresh_ui(self):
        app = App.get_running_app()
        gs = app.game_state
        if not gs or not gs.started:
            return

        pid = app.player_idx
        is_my_turn = gs.current_player == pid
        is_active = pid in gs.active_players

        # Info bar
        turn_txt = '🟢 GILIRAN KAMU!' if is_my_turn else f'Giliran Pemain {gs.current_player+1}'
        self.info_label.text = (
            f'{turn_txt}  |  Kartu kamu: {len(gs.hands[pid])}  |  '
            f'Aktif: {len(gs.active_players)} pemain'
        )

        # Status pemain lain
        others = []
        for i in range(gs.num_players):
            if i == pid:
                continue
            status = ''
            if i not in gs.active_players:
                rank = gs.rankings.index(i) + 1 if i in gs.rankings else '?'
                status = f'[Juara {rank}]'
            elif i in gs.stopped_players:
                status = '[STOP]'
            elif gs.current_player == i:
                status = '[GILIRAN]'
            others.append(f'P{i+1}:{len(gs.hands[i])}kartu {status}')
        self.players_label.text = '  '.join(others)

        # Meja
        self.table_layout.clear_widgets()
        if gs.table_cards:
            for card in gs.table_cards:
                lbl = Label(
                    text=card.display(), font_size=20, bold=True,
                    color=TEXT_DARK,
                    size_hint=(None, None), size=(60, 85)
                )
                with lbl.canvas.before:
                    Color(*CARD_BG)
                    RoundedRectangle(size=lbl.size, pos=lbl.pos, radius=[8])
                self.table_layout.add_widget(lbl)
            type_txt = f'[{gs.table_type}]' if gs.table_type else ''
            self.table_layout.add_widget(
                Label(text=type_txt, font_size=13, color=(1,1,0.5,1),
                      size_hint=(None, None), size=(70, 85))
            )
        else:
            self.table_layout.add_widget(
                Label(text='(meja kosong)', font_size=15,
                      color=(0.7, 0.9, 0.7, 1),
                      size_hint=(None, None), size=(150, 85))
            )

        # Pesan
        self.msg_label.text = gs.message

        # Kartu tangan
        self.hand_layout.clear_widgets()
        self.card_buttons = []
        self.selected_cards = []
        for card in sorted(gs.hands[pid], key=lambda c: (
            ['4','5','6','7','8','9','10','J','Q','K','A','2'].index(c.value),
            ['S','H','D','C'].index(c.suit)
        )):
            btn = CardButton(card)
            btn.bind(on_press=self.toggle_card)
            self.card_buttons.append(btn)
            self.hand_layout.add_widget(btn)

        # Enable/disable tombol
        self.btn_play.disabled = not (is_my_turn and is_active)
        self.btn_skip.disabled = not (is_my_turn and is_active)

        # Cek game over
        if gs.game_over:
            self.show_game_over()

    def toggle_card(self, btn):
        btn.toggle_select()
        if btn.selected:
            self.selected_cards.append(btn.card)
        else:
            self.selected_cards.remove(btn.card)

    def do_play(self, *args):
        if not self.selected_cards:
            self.msg_label.text = 'Pilih kartu dulu!'
            return
        app = App.get_running_app()
        if app.mode == 'solo':
            ok, msg = app.game_state.play_cards(app.player_idx, list(self.selected_cards))
            self.msg_label.text = msg
            self.refresh_ui()
        elif app.mode == 'host':
            ok, msg = app.game_state.play_cards(app.player_idx, list(self.selected_cards))
            self.msg_label.text = msg
            if ok:
                app.broadcast_state()
            self.refresh_ui()
        elif app.mode == 'client':
            cards_data = [c.to_dict() for c in self.selected_cards]
            app.client.send('play', {'cards': cards_data})

    def do_skip(self, *args):
        app = App.get_running_app()
        if app.mode == 'solo':
            ok, msg = app.game_state.skip_turn(app.player_idx)
            self.msg_label.text = msg
            self.refresh_ui()
        elif app.mode == 'host':
            ok, msg = app.game_state.skip_turn(app.player_idx)
            self.msg_label.text = msg
            if ok:
                app.broadcast_state()
            self.refresh_ui()
        elif app.mode == 'client':
            app.client.send('skip', {})

    def show_game_over(self):
        app = App.get_running_app()
        gs = app.game_state
        rankings = gs.get_rankings_display()
        content = BoxLayout(orientation='vertical', padding=20, spacing=10)
        content.add_widget(Label(text='🏆 GAME SELESAI!', font_size=24, bold=True))
        for r in rankings:
            content.add_widget(Label(text=r, font_size=18))
        btn_ok = make_btn('MAIN LAGI', BTN_PLAY, font_size=18, size_hint_y=None, height=50)
        popup = Popup(title='', content=content, size_hint=(0.8, 0.7),
                      auto_dismiss=False)
        btn_ok.bind(on_press=lambda x: (popup.dismiss(),
                                        setattr(self.manager, 'current', 'menu')))
        content.add_widget(btn_ok)
        popup.open()


# ─── APP ─────────────────────────────────────────────────────────────────────
class PokerApp(App):
    def build(self):
        self.mode = None          # 'solo', 'host', 'client'
        self.num_players = 2
        self.player_idx = 0
        self.game_state = None
        self.server = None
        self.client = None

        sm = ScreenManager()
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(HostScreen(name='host'))
        sm.add_widget(JoinScreen(name='join'))
        sm.add_widget(GameScreen(name='game'))
        return sm

    # ── Host: terima aksi dari client
    def on_server_action(self, player_idx, action, data):
        if not self.game_state:
            return
        gs = self.game_state
        if action == 'play':
            cards = [Card.from_dict(c) for c in data.get('cards', [])]
            ok, msg = gs.play_cards(player_idx, cards)
            if ok:
                self.broadcast_state()
                Clock.schedule_once(lambda dt: self._refresh_game(), 0)
        elif action == 'skip':
            ok, msg = gs.skip_turn(player_idx)
            if ok:
                self.broadcast_state()
                Clock.schedule_once(lambda dt: self._refresh_game(), 0)

    def broadcast_state(self):
        if not self.server or not self.game_state:
            return
        for pid in range(1, self.num_players):
            state = self.game_state.to_dict(for_player=pid)
            self.server.send_to(pid, {'type': 'state_update', 'state': state})

    # ── Client: terima update dari host
    def on_client_message(self, msg):
        msg_type = msg.get('type')
        if msg_type == 'welcome':
            self.player_idx = msg.get('player_idx', 1)
        elif msg_type in ('game_start', 'state_update'):
            state = msg.get('state', {})
            Clock.schedule_once(lambda dt: self._apply_state(state), 0)

    def _apply_state(self, state):
        if not self.game_state:
            self.game_state = GameState(state['num_players'])
            self.game_state.started = True
        gs = self.game_state
        gs.current_player = state['current_player']
        gs.table_cards = [Card.from_dict(c) for c in state['table_cards']]
        gs.table_type = state['table_type']
        gs.rankings = state['rankings']
        gs.active_players = state['active_players']
        gs.stopped_players = set(state.get('stopped_players', []))
        gs.game_over = state['game_over']
        gs.message = state.get('message', '')
        gs.hands = [[] for _ in range(gs.num_players)]
        gs.hands[self.player_idx] = [Card.from_dict(c) for c in state['hand']]
        # hand count untuk pemain lain
        for i, count in enumerate(state.get('hand_counts', [])):
            if i != self.player_idx:
                gs.hands[i] = [Card('S', '4')] * count  # dummy

        sm = self.root
        if sm.current != 'game':
            sm.current = 'game'
        self._refresh_game()

    def _refresh_game(self):
        sm = self.root
        game_screen = sm.get_screen('game')
        game_screen.refresh_ui()


if __name__ == '__main__':
    PokerApp().run()
