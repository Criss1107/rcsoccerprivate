from base_player import BasePlayer
import sys
import random
from perception import World, dist_between

KICKABLE = 1.0 #alcance de pateo aprox
SHOOT_RANGE = 25.0 #distancia maxima a porteria para tirar
SEARCH_TURN = 60 #grados al buscar la pelota

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

class Attacker(BasePlayer):
    """FSM: SEARCH -> CHASE -> (SHOOT | PASS | DRIBBLE) ; SUPPORT si otro es mas cercano."""
    def decide(self, w: World):
        ball = w.ball
        if ball is None:
            self.set_state("SEARCH")
            return self.send(f"(turn {SEARCH_TURN})")
 
        #posesion: pelota al alcance
        if ball.dist <= KICKABLE:
            return self.with_ball(w)
 
        # --- Cooperacion: solo persigue el mas cercano a la pelota ---
        closer_mate = any(m.dist < ball.dist - 1.0 for m in w.mates
                          if dist_between(m, ball) < ball.dist)
        if closer_mate:
            self.set_state("SUPPORT")
            return self.support(w)
 
        self.set_state("CHASE")
        return self.go_to(ball, 100 if (w.stamina or 8000) > 1500 else 60)
 
    # ------------------------------------------------------------
    def with_ball(self, w: World):
        goal = w.opp_goal
        if goal is not None and goal.dist <= SHOOT_RANGE:
            self.set_state("SHOOT")
            self.m["kicks"] += 1
            self.m["shots"] += 1
            return self.send(f"(kick 100 {goal.dir:.0f})")
 
        # pase: companero adelantado (mas cerca de la porteria rival) y libre
        target = self.best_pass(w)
        if target is not None:
            self.set_state("PASS")
            self.m["kicks"] += 1
            self.m["passes"] += 1
            power = clamp(target.dist * 2.5 + 10, 30, 100)  # a calibrar
            return self.send(f"(kick {power:.0f} {target.dir:.0f})")
 
        self.set_state("DRIBBLE")
        self.m["kicks"] += 1
        d = goal.dir if goal is not None else 0
        return self.send(f"(kick 25 {d:.0f})")
 
    def best_pass(self, w: World):
        goal = w.opp_goal
        if goal is None:
            return None
        best, best_gap = None, 0.0
        for m in w.mates:
            if not (3 < m.dist < 35):
                continue
            # debe estar mas cerca de la porteria rival que yo
            gain = goal.dist - dist_between(m, goal)
            # libre: ningun rival cerca del companero
            free = all(dist_between(o, m) > 4.0 for o in w.opps)
            if free and gain > best_gap:
                best, best_gap = m, gain
        return best
 
    def support(self, w: World):
        """Sin pelota: orientarse a la pelota y avanzar hacia la porteria rival."""
        ball = w.ball
        if abs(ball.dir) > 25:
            return self.send(f"(turn {ball.dir:.0f})")
        if w.opp_goal is not None and w.opp_goal.dist > 20:
            return self.send("(dash 60)")
        return self.send("(turn 0)")
 
    def go_to(self, obj, power):
        if abs(obj.dir) > 10:
            return self.send(f"(turn {obj.dir:.0f})")
        return self.send(f"(dash {power})")

    """def play(self):
        Atacantes avanzan hacia la portería rival
        ACTIONS = ["turn_left", "turn_right", "dash", "kick"]
        action = random.choice(ACTIONS)
        if action == "turn_left":
            self.send("(turn -45)")
        elif action == "turn_right":
            self.send("(turn 45)")
        elif action == "dash":
            self.send("(dash 60)")
        elif action == "kick":
            self.send("(kick 80 0)")
"""

if __name__ == "__main__":
    number = int(sys.argv[1])
    role = sys.argv[2]
    player = Attacker(team_name="MYTEAMUD", number=number, role=role)
    player.start()
