from base_player import BasePlayer
import sys
import random
from perception import World, dist_between

KICKABLE = 1.0
DEFENSE_LINE = 30.0   # distancia deseada a la propia porteria (zona de defensa)
ENGAGE_RANGE = 15.0   # si la pelota esta mas cerca, el defensa mas cercano la ataca


class Defender(BasePlayer):
    """def play(self):
        Defensas se mueven y giran aleatoriamente
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
    """FSM: SEARCH, CLEAR (despeje), INTERCEPT (presion), COVER (mantener linea)."""
 
    def decide(self, w: World):
        ball = w.ball
        if ball is None:
            self.set_state("SEARCH")
            return self.send("(turn 60)")
 
        if ball.dist <= KICKABLE:
            self.set_state("CLEAR")
            self.m["kicks"] += 1
            # despeje hacia adelante (porteria rival) si se ve; si no, al frente
            d = w.opp_goal.dir if w.opp_goal is not None else 0
            return self.send(f"(kick 100 {d:.0f})")
 
        i_am_closest = not any(dist_between(m, ball) < ball.dist
                               and m.dist < ball.dist for m in w.mates)
        if ball.dist < ENGAGE_RANGE and i_am_closest:
            self.set_state("INTERCEPT")
            if abs(ball.dir) > 10:
                return self.send(f"(turn {ball.dir:.0f})")
            return self.send("(dash 100)")
 
        self.set_state("COVER")
        return self.cover(w)
 
    def cover(self, w: World):
        """Mantener distancia DEFENSE_LINE a la propia porteria, mirando la pelota."""
        og = w.own_goal
        if og is None:
            # buscar la porteria propia girando
            return self.send("(turn 60)")
        if og.dist > DEFENSE_LINE + 4:      # muy adelantado: replegar
            if abs(og.dir) > 15:
                return self.send(f"(turn {og.dir:.0f})")
            return self.send("(dash 70)")
        return self.send(f"(turn {w.ball.dir:.0f})")  # orientarse a la pelota

if __name__ == "__main__":
    number = int(sys.argv[1])
    role = sys.argv[2]
    player = Defender(team_name="MYTEAMUD", number=number, role=role)
    player.start()
