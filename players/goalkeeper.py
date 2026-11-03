from base_player import BasePlayer
import sys
from perception import World

KICKABLE = 1.0
CATCHABLE = 2.0        # catchable_area_l por defecto del servidor
PENALTY_DEPTH = 16.0   # profundidad aprox del area grande 
HOME_RADIUS = 5.0      # distancia maxima a la propia porteria al esperar
SALLY_RANGE = 12.0     # si la pelota esta mas cerca el portero sale a buscarla


def norm_angle(a):
    while a > 180:
        a -= 360
    while a <= -180:
        a += 360
    return a


class Goalkeeper(BasePlayer):
    """FSM: SEARCH -> POSITION -> CATCH / CLEAR -> RETURN."""

    def decide(self, w: World):
        ball, og = w.ball, w.own_goal

        if ball is None:
            if og is not None and og.dist > HOME_RADIUS:
                self.set_state("RETURN")
                return self.go_to(og, 60)
            self.set_state("SEARCH")
            return self.send("(turn 60)")

        in_area = og is not None and og.dist < PENALTY_DEPTH

        # pelota al alcance de los pies: despejar lejos de la porteria propia
        if ball.dist <= KICKABLE:
            self.set_state("CLEAR")
            self.m["kicks"] += 1
            self.m["clearances"] += 1
            if w.opp_goal is not None:
                d = w.opp_goal.dir
            elif og is not None:
                d = norm_angle(og.dir + 180)   # lado contrario a mi porteria
            else:
                d = 0
            return self.send(f"(kick 100 {d:.0f})")

        # pelota atrapable dentro del area entoncee atajar
        if ball.dist <= CATCHABLE and in_area:
            self.set_state("CATCH")
            self.m["catches"] += 1
            return self.send(f"(catch {ball.dir:.0f})")

        # pelota cercana y yo cerca de mi arco salir a buscarla
        if ball.dist < SALLY_RANGE and in_area:
            self.set_state("POSITION")
            return self.go_to(ball, 100)

        # lejos: volver a la porteria si me aleje si no mirar la pelota
        if og is not None and og.dist > HOME_RADIUS:
            self.set_state("RETURN")
            return self.go_to(og, 60)

        self.set_state("POSITION")
        if abs(ball.dir) > 10:
            return self.send(f"(turn {ball.dir:.0f})")
        # alineado con la pelota y en su sitio


if __name__ == "__main__":
    number = int(sys.argv[1])
    role = sys.argv[2]
    player = Goalkeeper(team_name="MYTEAMUD", number=number, role=role)
    player.start()
