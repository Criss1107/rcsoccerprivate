from base_player import BasePlayer
import sys
from perception import World, dist_between

KICKABLE = 1.0       # alcance de pateo aprox
SHOOT_RANGE = 25.0   # distancia maxima a la porteria para tirar
SEARCH_TURN = 60     # grados al buscar la pelota
RECEIVER = 7         # receptor designado tras un saque inicial propio
RECEIVER_CYCLES = 120


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class Attacker(BasePlayer):
    """FSM: SEARCH -> CHASE -> (SHOOT | PASS | DRIBBLE) ; SUPPORT si otro es mas cercano."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wait = 0   # ciclos de espera tras patear en una jugada parada

    def decide(self, w: World):
        ball = w.ball
        if self.wait > 0:
            self.wait -= 1
        if ball is None:
            self.set_state("SEARCH")
            return self.send(f"(turn {SEARCH_TURN})")

        # posesion pelota al alcance
        if ball.dist <= KICKABLE:
            self.m["possession_cycles"] += 1
            if self.wait > 0:
                # el cobrador no puede tocar la pelota dos veces seguidas en un saque o si es falta se queda quieto hasta que la toque otro jugador
                self.set_state("SUPPORT")
                return self.send(f"(turn {ball.dir:.0f})")
            if not self.play_mode.startswith("play_on"):
                self.wait = 60   # saque inicial o jugada parada: un solo toque
            return self.with_ball(w)

        if self.wait > 0:
            self.set_state("SUPPORT")
            return self.support(w)

        #Cooperacion solo persigue el companero mas cercano a la pelota 
        # (distancia companero-pelota por ley de cosenos)
        closer_mate = any(dist_between(m, ball) < ball.dist - 1.0 for m in w.mates)
        # despues de nuestro saque, el receptor designado va por la pelota aunque el cobrador este mas cerca: asi otro jugador la toca primero (sin falta)
        receiver = (self.number == RECEIVER and
                    self.m["cycles"] - self.kickoff_cycle < RECEIVER_CYCLES)
        if closer_mate and not receiver:
            self.set_state("SUPPORT")
            return self.support(w)

        self.set_state("CHASE")
        return self.go_to(ball, 100 if (w.stamina or 8000) > 1500 else 60)

    def with_ball(self, w: World):
        goal = w.opp_goal
        if goal is not None and goal.dist <= SHOOT_RANGE:
            self.set_state("SHOOT")
            self.m["kicks"] += 1
            self.m["shots"] += 1
            return self.send(f"(kick 100 {goal.dir:.0f})")

        # pase compañero adelantado (mas cerca de la porteria rival) y libre
        target = self.best_pass(w)
        if target is not None:
            self.set_state("PASS")
            self.m["kicks"] += 1
            self.m["passes"] += 1
            power = clamp(target.dist * 2.5 + 10, 30, 100)  # a calibrar
            return self.send(f"(kick {power:.0f} {target.dir:.0f})")

        if not self.play_mode.startswith("play_on"):
            # saque inicial / jugada parada sin pase posible: patada larga hacia adelante para que otro jugador la toque primero (evita la falta)
            self.set_state("KICKOFF")
            self.m["kicks"] += 1
            d = goal.dir if goal is not None else 0
            return self.send(f"(kick 100 {d:.0f})")

        self.set_state("DRIBBLE")
        if goal is None:
            # sin ver la porteria rival e ntonces girar hasta encontrarla
            return self.send("(turn 45)")
        self.m["kicks"] += 1
        return self.send(f"(kick 30 {goal.dir:.0f})")

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
        """Sin pelota orientarse a la pelota y avanzar hacia la porteria rival."""
        ball = w.ball
        if abs(ball.dir) > 25:
            return self.send(f"(turn {ball.dir:.0f})")
        if w.opp_goal is None or w.opp_goal.dist > 20:
            return self.send("(dash 60)")
        return self.send(f"(turn {ball.dir:.0f})")


if __name__ == "__main__":
    number = int(sys.argv[1])
    role = sys.argv[2]
    player = Attacker(team_name="MYTEAMUD", number=number, role=role)
    player.start()
