from base_player import BasePlayer
import sys
from perception import World, dist_between

KICKABLE = 1.0
DEFENSE_LINE = 30.0   # distancia deseada a la propia porteria 
ENGAGE_RANGE = 15.0   # si la pelota esta mas cerca el defensa mas cercano la ataca
DEFENDER_NUMBERS = range(2, 6)
GLANCE_EVERY = 40     # ciclos sin ver la propia porteria antes de mirar atras
ADVANCE_CYCLES = 10   # ciclos que avanza tras comprobar que esta muy atras


def norm_angle(a):
    while a > 180:
        a -= 360
    while a <= -180:
        a += 360
    return a


class Defender(BasePlayer):
    """FSM: SEARCH, CLEAR (despeje), INTERCEPT (presion), COVER (mantener linea)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cycles_since_og = 0   # ciclos desde que vi mi porteria por ultima vez
        self.advance = 0           # ciclos restantes de avance hacia la linea

    def hold_line(self, w: World, ball_far: bool):
        og = w.own_goal
        if og is None:
            return False
        self.cycles_since_og = 0
        if og.dist > DEFENSE_LINE + 4:              # muy adelantado: replegar
            self.advance = 0
            self.go_to(og, 70)
            return True
        if og.dist < DEFENSE_LINE - 8 and ball_far:
            self.advance = ADVANCE_CYCLES           # muy atras: subir a la linea
            ahead = norm_angle(og.dir + 180)        # direccion opuesta a mi arco
            if abs(ahead) > 15:
                self.send(f"(turn {ahead:.0f})")
            else:
                self.send("(dash 50)")
            return True
        return False

    def decide(self, w: World):
        ball = w.ball
        self.cycles_since_og += 1

        if ball is None:
            # sin pelota a la vista, si veo mi porteria igual ajusto la linea
            if self.hold_line(w, ball_far=True):
                self.set_state("COVER")
                return
            if self.advance > 0:                    # seguir subiendo a la linea
                self.advance -= 1
                self.set_state("COVER")
                return self.send("(dash 50)")
            self.set_state("SEARCH")
            return self.send("(turn 60)")

        if ball.dist <= KICKABLE:
            self.set_state("CLEAR")
            self.m["kicks"] += 1
            self.m["clearances"] += 1
            # despeje hacia adelante (porteria rival) si se ve, si no al frente
            d = w.opp_goal.dir if w.opp_goal is not None else 0
            return self.send(f"(kick 100 {d:.0f})")

        #defensa mas cercano a la pelota 
        i_am_closest = not any(
            dist_between(m, ball) < ball.dist
            for m in w.mates
            if m.unum is None or m.unum in DEFENDER_NUMBERS
        )
        if ball.dist < ENGAGE_RANGE and i_am_closest:
            self.set_state("INTERCEPT")
            self.m["intercept_cycles"] += 1
            self.advance = 0
            return self.go_to(ball, 100)

        self.set_state("COVER")
        return self.cover(w)

    def face_ball(self, ball):
        if abs(ball.dir) > 15:
            return self.send(f"(turn {ball.dir:.0f})")

    def cover(self, w: World):
        ball = w.ball
        if self.hold_line(w, ball_far=ball.dist > ENGAGE_RANGE):
            return
        if w.own_goal is not None:                  # linea correcta mirar la pelota
            return self.face_ball(ball)

        # no veo mi porteria
        if self.advance > 0 and abs(ball.dir) <= 45:
            self.advance -= 1
            return self.send("(dash 50)")
        if self.cycles_since_og > GLANCE_EVERY:
            self.cycles_since_og = GLANCE_EVERY - 8   # reintenta pronto si no la ve
            return self.send("(turn 150)")            # mirar hacia atras
        return self.face_ball(ball)


if __name__ == "__main__":
    number = int(sys.argv[1])
    role = sys.argv[2]
    player = Defender(team_name="MYTEAMUD", number=number, role=role)
    player.start()
