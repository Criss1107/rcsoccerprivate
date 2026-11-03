import json
import os
import re
import signal
import socket
import sys
import time
from collections import defaultdict

from perception import World, parse_see, parse_sense_body_stamina

SERVER_HOST = "localhost"
SERVER_PORT = 6000
BUFFER_SIZE = 8192
PROTOCOL_VERSION = 15
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")

_INIT = re.compile(r"\(init\s+([lr])\s+(\d+)\s+(\w+)")
_REFEREE = re.compile(r"\(hear\s+\d+\s+referee\s+([a-zA-Z_]+)")

IDLE_MODES = ("before_kick_off", "goal_l", "goal_r", "half_time",
              "time_over", "time_up", "extra_half_time")


class BasePlayer:
    def __init__(self, team_name, number, role):
        self.team_name = team_name
        self.number = number          # numero asignado por manager.py (define la posicin inicial)
        self.unum = number            # numero real asignado por el servidor (se actualiza en init)
        self.role = role
        self.side = "l"
        self.play_mode = "before_kick_off"
        self.stamina = None
        self.running = True
        self.verbose = bool(os.environ.get("PLAYER_DEBUG"))
        self.kickoff_cycle = -10**9   

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", 0))  
        self.server_addr = (SERVER_HOST, SERVER_PORT)

        self.state = None
        self.m = defaultdict(int)     # cycles, kicks, passes, shots, state_changes, ...
        self.state_cycles = defaultdict(int)
        self.latency_sum = 0.0
        self.latency_max = 0.0
        self.t_start = time.time()

    def send(self, msg):
        """Envia un comando al puerto del servidor dedicado a este jugador."""
        self.sock.sendto(msg.encode(), self.server_addr)
        if self.verbose:
            print(f"-> {msg}", flush=True)

    def receive(self, timeout=1.0):
        """Devuelve (mensaje, direccion). ("", None) si hay timeout."""
        self.sock.settimeout(timeout)
        try:
            data, addr = self.sock.recvfrom(BUFFER_SIZE)
            return data.decode(errors="ignore").strip("\x00\r\n "), addr
        except socket.timeout:
            return "", None
        except OSError as e:
            print(f"socket error: {e}", flush=True)
            return "", None

    def start_position(self):
        """Posicion inicial por rol (siempre en la propia mitad: x < 0)."""
        positions_map = {
            1: (-50, 0),       # Goalkeeper
            2: (-35, -20),     # Defenders
            3: (-35, -7),
            4: (-35, 7),
            5: (-35, 20),
            6: (-15, -22),     # Attackers
            7: (-15, 0),
            8: (-15, 22),
            9: (-6, -12),
            10: (-6, 12),
            11: (-2, 0),
        }
        return positions_map.get(self.number, (-20, 0))

    def move_to_start(self):
        x, y = self.start_position()
        self.send(f"(move {x} {y})")

    def init_connection(self, attempts=15):
        goalie = " (goalie)" if self.role == "goalkeeper" else ""
        init_msg = f"(init {self.team_name} (version {PROTOCOL_VERSION}){goalie})"

        for _ in range(attempts):
            self.sock.sendto(init_msg.encode(), (SERVER_HOST, SERVER_PORT))
            msg, addr = self.receive(timeout=1.0)
            if msg.startswith("(init"):
                m = _INIT.match(msg)
                if m:
                    self.side, self.unum, self.play_mode = m.group(1), int(m.group(2)), m.group(3)
                self.server_addr = addr   # <- puerto dedicado del servidor
                self.log(f"conectado: lado={self.side} unum={self.unum} modo={self.play_mode}")
                self.move_to_start()
                return True
            if msg.startswith("(error"):
                self.log(f"el servidor rechazo el init: {msg}")
                return False
        self.log("sin respuesta del servidor (esta corriendo rcssserver?)")
        return False

    def log(self, text):
        print(f"[{self.role.upper()} #{self.unum}] {text}", flush=True)

    def set_state(self, name):
        if name != self.state:
            self.state = name
            self.m["state_changes"] += 1
            self.log(f"estado -> {name}")
        self.state_cycles[name] += 1

    def decide(self, w: World):
        self.set_state("IDLE")
        self.send("(turn 30)")

    def go_to(self, obj, power):
        if abs(obj.dir) > 10:
            return self.send(f"(turn {obj.dir:.0f})")
        return self.send(f"(dash {power})")

    def on_hear(self, msg):
        m = _REFEREE.match(msg)
        if not m:
            return
         # 'move' solo es valido en estos modos
        mode = m.group(1)
        self.play_mode = mode
        if mode.startswith(f"kick_off_{self.side}"):
            self.kickoff_cycle = self.m["cycles"]
        if mode == "before_kick_off" or mode.startswith(("goal_l", "goal_r")):
            self.move_to_start()         

    def on_see(self, msg):
        t0 = time.perf_counter()
        w = parse_see(msg, self.team_name, self.side)
        w.stamina = self.stamina
        if self.verbose:
            b, og = w.ball, w.own_goal
            print(f"   see: ball={b and (round(b.dist, 1), round(b.dir))} "
                  f"own_goal={og and (round(og.dist, 1), round(og.dir))} "
                  f"mates={len(w.mates)} modo={self.play_mode}", flush=True)
        if not self.play_mode.startswith(IDLE_MODES):
            self.decide(w)
        dt = (time.perf_counter() - t0) * 1000.0
        self.m["cycles"] += 1
        self.latency_sum += dt
        self.latency_max = max(self.latency_max, dt)
        if self.m["cycles"] % 100 == 0:
            self.save_metrics()

    #metricas
    def save_metrics(self):
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            cycles = self.m["cycles"]
            data = {
                "team": self.team_name, "role": self.role, "unum": self.unum,
                "side": self.side, "seconds": round(time.time() - self.t_start, 1),
                "counters": dict(self.m),
                "state_cycles": dict(self.state_cycles),
                "latency_ms_mean": round(self.latency_sum / cycles, 3) if cycles else 0.0,
                "latency_ms_max": round(self.latency_max, 3),
            }
            with open(os.path.join(LOG_DIR, f"player_{self.unum}.json"), "w") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            print(f"no se pudo guardar metricas: {e}", flush=True)

    def stop(self, *_):
        self.running = False

    def action_loop(self):
        while self.running:
            msg, _ = self.receive(timeout=1.0)
            if not msg:
                continue
            if msg.startswith("(see"):
                self.on_see(msg)
            elif msg.startswith("(sense_body"):
                s = parse_sense_body_stamina(msg)
                if s is not None:
                    self.stamina = s
            elif msg.startswith("(hear"):
                self.on_hear(msg)

    def start(self):
        # manager.py usa terminate()
        signal.signal(signal.SIGTERM, self.stop)   
        if not self.init_connection():
            sys.exit(1)
        try:
            self.action_loop()
        except KeyboardInterrupt:
            pass
        finally:
            self.save_metrics()
            try:
                self.send("(bye)")
            except OSError:
                pass
            self.log("fin")
