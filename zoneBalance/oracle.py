# oracle.py
import numpy as np

class Oracle:
    @staticmethod
    def final_balance(env):
        env.dispatch_summary = []
        while True:
            surplus_idx = np.where(env.state < 0)[0]
            deficit_idx = np.where(env.state > 0)[0]
            if len(surplus_idx) == 0 or len(deficit_idx) == 0:
                break
            moved = False
            for s in surplus_idx:
                for d in deficit_idx:
                    if s == d:
                        continue
                    if env.state[s] < 0 and env.state[d] > 0:
                        num = min(-env.state[s], env.state[d])
                        if num > 0:
                            env.drivers[s] -= num
                            env.drivers[d] += num
                            env.dispatch_summary.append((int(s), int(d), int(num)))
                            moved = True
                            env.state = env.riders - env.drivers
            if not moved:
                break
        return env.state, env.drivers, env.dispatch_summary
