import math


class UCBBandit:
    def __init__(self, arms):
        self.arms = arms
        self.counts = [0] * len(arms)
        self.values = [0.0] * len(arms)
        self.total_count = 0
        self.reward_history = []

    def select_arm(self):
        # Ensure each arm is tried once
        for i, c in enumerate(self.counts):
            if c == 0:
                return i

        ucb_scores = []
        for i in range(len(self.arms)):
            bonus = math.sqrt(
                2 * math.log(self.total_count) / self.counts[i]
            )
            ucb_scores.append(self.values[i] + bonus)

        return ucb_scores.index(max(ucb_scores))

    def update(self, arm_idx, reward):
        self.total_count += 1
        self.counts[arm_idx] += 1
        self.reward_history.append(reward)

        n = self.counts[arm_idx]
        value = self.values[arm_idx]
        self.values[arm_idx] = value + (reward - value) / n

    @property
    def average_reward(self):
        if not self.reward_history:
            return 0.0
        return sum(self.reward_history) / len(self.reward_history)
