# -*- coding: utf-8 -*-
"""
Pocket RPG Mobile - Android용 한 파일 Python/Kivy 게임
------------------------------------------------------
PC에서 테스트:
    pip install kivy
    python main.py

Android APK 빌드(권장: Linux/WSL):
    pip install buildozer
    buildozer init
    # buildozer.spec에서 requirements = python3,kivy 로 설정
    buildozer android debug

게임:
- 터치 방향키
- 마을 / 포켓몬센터 / 풀숲 / NPC
- 야생 포켓몬 / 포획
- 포켓몬 배틀
- 급소
- 타입 상성
- 로켓단
- 보스
- 배지
- 챔피언쉽
- 파티/물약/몬스터볼
"""

import random
import json
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, Ellipse, Line
from kivy.properties import StringProperty, NumericProperty

Window.clearcolor = (0.08, 0.12, 0.18, 1)

# ---------------- 데이터 ----------------

TYPE_ADV = {
    "불": {"풀", "벌레", "얼음"},
    "물": {"불", "바위", "땅"},
    "풀": {"물", "바위", "땅"},
    "전기": {"물"},
    "바위": {"불", "얼음", "벌레", "비행"},
    "땅": {"불", "전기", "바위"},
    "얼음": {"풀", "땅"},
    "벌레": {"풀"},
    "비행": {"풀", "벌레"},
    "독": {"풀"},
    "노말": set(),
}

TYPE_WEAK = {
    "불": {"물", "바위", "땅"},
    "물": {"전기", "풀"},
    "풀": {"불", "얼음", "벌레", "비행", "독"},
    "전기": {"땅"},
    "바위": {"물", "풀", "땅"},
    "땅": {"물", "풀", "얼음"},
    "얼음": {"불", "바위", "벌레"},
    "벌레": {"불", "바위", "비행"},
    "비행": {"전기", "바위", "얼음"},
    "독": {"땅", "바위"},
    "노말": {"바위"},
}

POKEMON = {
    "파이리": {"type":"불", "base":48, "moves":[("불꽃세례","불",16),("할퀴기","노말",12)]},
    "꼬부기": {"type":"물", "base":50, "moves":[("물대포","물",16),("몸통박치기","노말",12)]},
    "이상해씨": {"type":"풀", "base":49, "moves":[("덩굴채찍","풀",16),("몸통박치기","노말",12)]},
    "피카츄": {"type":"전기", "base":46, "moves":[("전기쇼크","전기",17),("전광석화","노말",12)]},
    "꼬리선": {"type":"노말", "base":42, "moves":[("몸통박치기","노말",13),("전광석화","노말",11)]},
    "구구": {"type":"비행", "base":44, "moves":[("쪼기","비행",14),("몸통박치기","노말",12)]},
    "꼬마돌": {"type":"바위", "base":55, "moves":[("돌떨구기","바위",17),("몸통박치기","노말",11)]},
    "모래두지": {"type":"땅", "base":47, "moves":[("땅고르기","땅",16),("할퀴기","노말",12)]},
    "주뱃": {"type":"독", "base":43, "moves":[("독침","독",15),("쪼기","비행",11)]},
}

WILD = ["꼬리선", "구구", "꼬마돌", "모래두지", "피카츄", "주뱃"]
STARTERS = ["파이리", "꼬부기", "이상해씨"]

def make_mon(name, level):
    d = POKEMON[name]
    hp = d["base"] + level * 5
    return {
        "name": name,
        "type": d["type"],
        "level": level,
        "max_hp": hp,
        "hp": hp,
        "exp": 0,
        "moves": d["moves"][:]
    }

def multiplier(move_type, target_type):
    if target_type in TYPE_ADV.get(move_type, set()):
        return 2.0
    if move_type in TYPE_WEAK.get(target_type, set()):
        return 0.5
    return 1.0

# ---------------- 맵 ----------------
# 0 길 / 1 벽 / 2 풀 / 3 센터 / 4 NPC / 5 로켓단 / 6 보스 / 7 챔피언
MAPS = {
    "마을": [
        "111111111111111111",
        "100000000000000001",
        "100030000400000001",
        "100000000000000001",
        "100000011111100001",
        "100000000000000001",
        "100000000000000001",
        "100000050000000001",
        "100000000000000001",
        "100000000000000001",
        "111111111111111111",
    ],
    "루트": [
        "111111111111111111",
        "100000000000000001",
        "100022220000000001",
        "100022220001111001",
        "100022220000000001",
        "100000000005000001",
        "100000000000000001",
        "100001111000000001",
        "100000000000060001",
        "100000000000000001",
        "111111111111111111",
    ],
    "챔피언": [
        "111111111111111111",
        "100000000000000001",
        "100070000000000001",
        "100000000000000001",
        "100001111100000001",
        "100000000000000001",
        "100000000000600001",
        "100000000000000001",
        "100000000000000001",
        "100000000000000001",
        "111111111111111111",
    ],
}

# ---------------- 맵 그리기 ----------------

class MapWidget(Widget):
    def __init__(self, game, **kwargs):
        super().__init__(**kwargs)
        self.game = game

    def draw(self):
        self.canvas.clear()
        grid = MAPS[self.game.place]
        cols = len(grid[0])
        rows = len(grid)
        tw = self.width / cols
        th = self.height / rows

        with self.canvas:
            for y, row in enumerate(grid):
                for x, c in enumerate(row):
                    if c == "1":
                        Color(0.12,0.20,0.17,1)
                    elif c == "2":
                        Color(0.20,0.52,0.25,1)
                    elif c == "3":
                        Color(0.85,0.85,0.92,1)
                    elif c == "4":
                        Color(0.85,0.58,0.25,1)
                    elif c == "5":
                        Color(0.55,0.20,0.50,1)
                    elif c == "6":
                        Color(0.70,0.18,0.18,1)
                    elif c == "7":
                        Color(0.90,0.75,0.20,1)
                    else:
                        Color(0.34,0.62,0.38,1)

                    Rectangle(pos=(x*tw, self.height-(y+1)*th), size=(tw+1,th+1))

                    if c == "2":
                        Color(0.12,0.35,0.15,1)
                        Ellipse(pos=(x*tw+tw*.35, self.height-(y+1)*th+th*.35),
                                size=(tw*.3,th*.3))

                    if c in "34567":
                        Color(1,1,1,1)
                        # 장소 아이콘
                        Rectangle(pos=(x*tw+tw*.30, self.height-(y+1)*th+th*.30),
                                  size=(tw*.4,th*.4))

            # 플레이어
            px = self.game.px * tw + tw/2
            py = self.height - (self.game.py+1)*th + th/2
            Color(0.15,0.30,0.95,1)
            Ellipse(pos=(px-tw*.23,py-th*.23), size=(tw*.46,th*.46))

            # 격자 경계
            Color(0,0,0,.15)
            for x in range(cols+1):
                Line(points=[x*tw,0,x*tw,self.height], width=1)
            for y in range(rows+1):
                Line(points=[0,y*th,self.width,y*th], width=1)

# ---------------- 메인 게임 ----------------

class Game(FloatLayout):
    message = StringProperty("새로운 모험을 시작하자!")
    hp_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.place = "마을"
        self.px, self.py = 2, 6
        self.money = 300
        self.balls = 8
        self.potions = 3
        self.badges = 0
        self.team = []
        self.battle = None
        self.menu_open = False

        # 맵
        self.map = MapWidget(self)
        self.add_widget(self.map)

        # 상단 HUD
        self.hud = Label(
            text="",
            size_hint=(1,None),
            height=dp(52),
            pos_hint={"top":1},
            color=(1,1,1,1),
            font_size=dp(15),
            halign="left",
            valign="middle",
            padding=(dp(10),0)
        )
        self.hud.bind(size=lambda *_: setattr(self.hud, "text_size", self.hud.size))
        self.add_widget(self.hud)

        # 메시지 박스
        self.msg = Label(
            text=self.message,
            size_hint=(.92,None),
            height=dp(64),
            pos_hint={"x":.04,"y":.16},
            color=(1,1,1,1),
            font_size=dp(14),
            halign="left",
            valign="middle",
            padding=(dp(12),dp(5))
        )
        self.msg.bind(size=lambda *_: setattr(self.msg, "text_size", self.msg.size))
        self.add_widget(self.msg)

        # 터치 D-pad
        dpad = FloatLayout(size_hint=(.38,.25), pos_hint={"x":.03,"y":.01})
        self.add_widget(dpad)

        for text, pos, callback in [
            ("▲", (.34,.55), lambda *_: self.move(0,-1)),
            ("▼", (.34,.02), lambda *_: self.move(0,1)),
            ("◀", (.02,.28), lambda *_: self.move(-1,0)),
            ("▶", (.66,.28), lambda *_: self.move(1,0)),
            ("A", (.67,.67), lambda *_: self.interact()),
        ]:
            b = Button(text=text, font_size=dp(25),
                       size_hint=(.32,.32), pos_hint={"x":pos[0],"y":pos[1]})
            b.bind(on_release=callback)
            dpad.add_widget(b)

        # 우측 기능 버튼
        self.menu_btn = Button(text="🎒\n가방", font_size=dp(13),
                               size_hint=(.17,.10), pos_hint={"right":.98,"y":.03})
        self.menu_btn.bind(on_release=lambda *_: self.show_menu())
        self.add_widget(self.menu_btn)

        self.save_btn = Button(text="💾", font_size=dp(22),
                               size_hint=(.12,.09), pos_hint={"right":.98,"top":.96})
        self.save_btn.bind(on_release=lambda *_: self.save_game())
        self.add_widget(self.save_btn)

        # 화면 시작
        Clock.schedule_once(lambda *_: self.starter_popup(), .3)
        Clock.schedule_interval(lambda *_: self.refresh(), .1)

    def refresh(self):
        self.map.draw()
        self.hud.text = (
            f"📍 {self.place}   💰 {self.money}   ⚪ {self.balls}   "
            f"💊 {self.potions}   🏅 {self.badges}"
        )
        self.msg.text = self.message

    def setmsg(self, text):
        self.message = text

    def starter_popup(self):
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        box.add_widget(Label(text="첫 포켓몬을 선택하세요!", font_size=dp(20)))
        for name in STARTERS:
            b = Button(text=f"{name}  [{POKEMON[name]['type']}]",
                       size_hint_y=None, height=dp(55))
            b.bind(on_release=lambda btn, n=name: self.choose_starter(n, popup))
            box.add_widget(b)
        popup = Popup(title="POCKET RPG", content=box,
                      size_hint=(.88,.65), auto_dismiss=False)
        popup.open()

    def choose_starter(self, name, popup):
        self.team = [make_mon(name,5)]
        popup.dismiss()
        self.setmsg(f"{name}과(와) 모험을 시작했다!")

    def can_move(self,x,y):
        g = MAPS[self.place]
        return 0 <= y < len(g) and 0 <= x < len(g[y]) and g[y][x] != "1"

    def move(self, dx, dy):
        if self.battle:
            return
        nx, ny = self.px+dx, self.py+dy
        if not self.can_move(nx,ny):
            self.setmsg("벽 때문에 갈 수 없다.")
            return
        self.px,self.py=nx,ny
        tile=MAPS[self.place][ny][nx]

        if tile=="2" and random.random()<.22:
            self.encounter()

    def interact(self):
        if self.battle:
            return

        tile = MAPS[self.place][self.py][self.px]

        if tile=="3":
            for m in self.team:
                m["hp"]=m["max_hp"]
            self.setmsg("🏥 포켓몬센터에서 파티가 모두 회복됐다!")
            return

        if tile=="4":
            self.setmsg("NPC: 북쪽 루트에 로켓단이 나타났다는 소문이 있어!")
            return

        if tile=="5":
            self.start_battle(make_mon("꼬마돌",10), boss=True, rocket=True)
            return

        if tile=="6":
            self.start_battle(make_mon("파이리",14), boss=True)
            return

        if tile=="7":
            if self.badges >= 3:
                self.start_battle(make_mon("피카츄",16), boss=True)
            else:
                self.setmsg(f"챔피언쉽은 배지 3개가 필요하다. 현재 {self.badges}개!")
            return

        # 지역 이동
        if self.place=="마을" and self.px>=14 and self.py>=8:
            self.place="루트"; self.px,self.py=2,2
            self.setmsg("🌿 루트에 도착했다! 풀숲에서 포켓몬을 찾아보자.")
        elif self.place=="루트" and self.px<=2 and self.py<=2:
            self.place="마을"; self.px,self.py=14,8
            self.setmsg("🏘️ 마을로 돌아왔다.")
        elif self.place=="루트" and self.px>=14 and self.py>=7:
            self.place="챔피언"; self.px,self.py=2,2
            self.setmsg("🏟️ 챔피언쉽 경기장에 도착했다!")

    # ---------------- 전투 ----------------

    def encounter(self):
        name=random.choice(WILD)
        level=random.randint(2,7)
        self.start_battle(make_mon(name,level))

    def start_battle(self, enemy, boss=False, rocket=False):
        if not self.team:
            self.setmsg("먼저 첫 포켓몬을 골라야 한다.")
            return
        self.battle={
            "enemy":enemy,
            "boss":boss,
            "rocket":rocket,
            "log":f"⚔️ {enemy['name']} Lv.{enemy['level']} 등장!",
            "done":False
        }
        self.battle_popup()

    def battle_popup(self):
        if not self.battle:
            return

        enemy=self.battle["enemy"]
        me=self.team[0]

        root=BoxLayout(orientation="vertical", spacing=dp(7), padding=dp(10))

        info=Label(
            text=self.battle["log"],
            size_hint_y=.24,
            font_size=dp(15),
            halign="left",
            valign="middle"
        )
        info.bind(size=lambda *_: setattr(info,"text_size",info.size))
        root.add_widget(info)

        status=Label(
            text=(
                f"🔴 적: {enemy['name']} Lv.{enemy['level']} "
                f"HP {enemy['hp']}/{enemy['max_hp']}\n"
                f"🔵 내 포켓몬: {me['name']} Lv.{me['level']} "
                f"HP {me['hp']}/{me['max_hp']}"
            ),
            size_hint_y=.22,
            font_size=dp(14)
        )
        root.add_widget(status)

        grid=GridLayout(cols=2, spacing=dp(7), size_hint_y=.42)

        attacks=me["moves"]
        for i,(mn,mt,pw) in enumerate(attacks):
            b=Button(text=f"⚔️ {mn}\n{mt} / 위력 {pw}", font_size=dp(13))
            b.bind(on_release=lambda btn,idx=i: self.battle_attack(idx,popup))
            grid.add_widget(b)

        catch=Button(text="⚪ 포획\n"+str(self.balls), font_size=dp(14))
        catch.bind(on_release=lambda *_: self.battle_catch(popup))
        grid.add_widget(catch)

        potion=Button(text="💊 물약\n"+str(self.potions), font_size=dp(14))
        potion.bind(on_release=lambda *_: self.battle_potion(popup))
        grid.add_widget(potion)

        run=Button(text="🏃 도망", font_size=dp(14))
        run.bind(on_release=lambda *_: self.battle_run(popup))
        grid.add_widget(run)

        root.add_widget(grid)

        popup=Popup(title="⚔️ POKÉMON BATTLE", content=root,
                    size_hint=(.94,.88), auto_dismiss=False)
        self.current_battle_popup=popup
        popup.open()

    def close_battle(self,popup):
        if popup:
            popup.dismiss()
        self.battle=None

    def battle_attack(self,idx,popup):
        if not self.battle: return
        me=self.team[0]
        enemy=self.battle["enemy"]
        mn,mt,pw=me["moves"][idx]
        mult=multiplier(mt,enemy["type"])
        critical=random.random()<.12
        dmg=max(1,int((pw+me["level"]*2)*mult*random.uniform(.85,1.15)))
        if critical: dmg*=2
        enemy["hp"]=max(0,enemy["hp"]-dmg)

        text=f"{mn}! {dmg} 데미지."
        if critical: text+=" 🎯 급소!"
        if mult==2: text+=" 💥 효과가 굉장했다!"
        if mult==.5: text+=" 효과가 별로였다."
        self.battle["log"]=text

        if enemy["hp"]<=0:
            self.win_battle(popup)
        else:
            self.enemy_attack()
            popup.dismiss()
            Clock.schedule_once(lambda *_: self.battle_popup(), .05)

    def enemy_attack(self):
        me=self.team[0]
        enemy=self.battle["enemy"]
        mn,mt,pw=random.choice(enemy["moves"])
        mult=multiplier(mt,me["type"])
        critical=random.random()<.10
        dmg=max(1,int((pw+enemy["level"]*2)*mult*random.uniform(.85,1.15)))
        if critical:dmg*=2
        me["hp"]=max(0,me["hp"]-dmg)
        self.battle["log"]+=f"\n{enemy['name']}의 {mn}! {dmg} 데미지."

        if me["hp"]<=0:
            me["hp"]=me["max_hp"]
            self.battle["log"]="💫 포켓몬이 쓰러졌다! 센터에서 회복했다."
            self.place="마을"
            self.px,self.py=2,6

    def win_battle(self,popup):
        me=self.team[0]
        enemy=self.battle["enemy"]
        gain=20+enemy["level"]*5
        me["exp"]+=gain
        while me["exp"]>=50:
            me["exp"]-=50
            me["level"]+=1
            me["max_hp"]+=5
            me["hp"]=me["max_hp"]

        if self.battle["boss"]:
            self.badges+=1
            self.money+=500
            self.setmsg(f"🏆 보스 격파! 배지 획득! 현재 배지 {self.badges}개")
        else:
            self.money+=gain
            self.setmsg(f"승리! EXP +{gain}")

        self.close_battle(popup)

    def battle_catch(self,popup):
        if not self.battle:return
        if self.battle["boss"]:
            self.battle["log"]="🚫 보스 포켓몬은 잡을 수 없다!"
            popup.dismiss(); Clock.schedule_once(lambda *_: self.battle_popup(),.05); return
        if self.balls<=0:
            self.battle["log"]="몬스터볼이 없다!"
            popup.dismiss(); Clock.schedule_once(lambda *_: self.battle_popup(),.05); return

        self.balls-=1
        enemy=self.battle["enemy"]
        ratio=1-enemy["hp"]/enemy["max_hp"]
        chance=.22+ratio*.62

        if random.random()<chance:
            self.team.append(enemy)
            self.setmsg(f"🎉 {enemy['name']}을(를) 잡았다! 파티 {len(self.team)}마리")
            self.close_battle(popup)
        else:
            self.battle["log"]="😱 포켓몬이 볼에서 빠져나왔다!"
            self.enemy_attack()
            popup.dismiss(); Clock.schedule_once(lambda *_: self.battle_popup(),.05)

    def battle_potion(self,popup):
        if not self.battle:return
        me=self.team[0]
        if self.potions<=0:
            self.battle["log"]="물약이 없다!"
        elif me["hp"]>=me["max_hp"]:
            self.battle["log"]="HP가 이미 가득하다!"
        else:
            self.potions-=1
            me["hp"]=min(me["max_hp"],me["hp"]+30)
            self.battle["log"]="💊 HP가 30 회복됐다."
            self.enemy_attack()

        popup.dismiss(); Clock.schedule_once(lambda *_: self.battle_popup(),.05)

    def battle_run(self,popup):
        if not self.battle:return
        if self.battle["boss"]:
            self.battle["log"]="🚫 보스전에서는 도망칠 수 없다!"
            popup.dismiss(); Clock.schedule_once(lambda *_: self.battle_popup(),.05)
            return
        if random.random()<.8:
            self.setmsg("🏃 무사히 도망쳤다!")
            self.close_battle(popup)
        else:
            self.battle["log"]="도망치지 못했다!"
            self.enemy_attack()
            popup.dismiss(); Clock.schedule_once(lambda *_: self.battle_popup(),.05)

    # ---------------- 메뉴/저장 ----------------

    def show_menu(self):
        root=BoxLayout(orientation="vertical", spacing=dp(7), padding=dp(10))
        root.add_widget(Label(
            text=f"🎒 가방   몬스터볼 {self.balls} / 물약 {self.potions}",
            size_hint_y=None,height=dp(45),font_size=dp(17)
        ))
        for i,m in enumerate(self.team):
            b=Button(
                text=f"{i+1}. {m['name']}  Lv.{m['level']}  "
                     f"{m['type']}  HP {m['hp']}/{m['max_hp']}",
                size_hint_y=None,height=dp(55)
            )
            root.add_widget(b)

        close=Button(text="닫기",size_hint_y=None,height=dp(50))
        root.add_widget(close)

        p=Popup(title="🎒 파티 / 가방",content=root,size_hint=(.92,.8))
        close.bind(on_release=p.dismiss)
        p.open()

    def save_game(self):
        data={
            "place":self.place,"px":self.px,"py":self.py,
            "money":self.money,"balls":self.balls,"potions":self.potions,
            "badges":self.badges,"team":self.team
        }
        try:
            Path(App.get_running_app().user_data_dir,"save.json").write_text(
                json.dumps(data,ensure_ascii=False),encoding="utf-8")
            self.setmsg("💾 저장 완료!")
        except Exception as e:
            self.setmsg("저장 실패: "+str(e))

    def load_game(self):
        try:
            p=Path(App.get_running_app().user_data_dir,"save.json")
            if not p.exists(): return
            d=json.loads(p.read_text(encoding="utf-8"))
            self.place=d["place"];self.px=d["px"];self.py=d["py"]
            self.money=d["money"];self.balls=d["balls"];self.potions=d["potions"]
            self.badges=d["badges"];self.team=d["team"]
            self.setmsg("💾 저장 데이터를 불러왔다!")
        except:
            pass

# ---------------- 앱 ----------------

class PocketRPGApp(App):
    title="Pocket RPG"

    def build(self):
        game=Game()
        self.game=game
        Clock.schedule_once(lambda *_: game.load_game(),1)
        return game

if __name__=="__main__":
    PocketRPGApp().run()
