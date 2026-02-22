import numpy as np
import gymnasium as gym
from gymnasium import spaces

class SimpleLineEnv(gym.Env):
    """
    1D line world:
    - Start at position 0
    - Goal at position (length - 1)
    - Actions: 0 = left, 1 = right
    """
    metadata = {"render_modes": ["human"]}

    def __init__(self, length=5, max_steps=20):
        super().__init__()
        self.length = length
        self.max_steps = max_steps

        self.action_space = spaces.Discrete(2)
        self.observation_space = spaces.Box(
            low=0, high=length - 1, shape=(1,), dtype=np.int32
        )

        self.pos = 0
        self.steps = 0

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.pos = 0
        self.steps = 0
        return np.array([self.pos], dtype=np.int32), {}

    def step(self, action):
        self.steps += 1

        if action == 0:
            self.pos = max(0, self.pos - 1)
        elif action == 1:
            self.pos = min(self.length - 1, self.pos + 1)

        terminated = (self.pos == self.length - 1)
        truncated = (self.steps >= self.max_steps)
        reward = 1.0 if terminated else -0.01

        obs = np.array([self.pos], dtype=np.int32)
        return obs, reward, terminated, truncated, {}

    def render(self):
        line = ["-"] * self.length
        line[self.pos] = "A"
        line[-1] = "G"
        print("".join(line))


# quick usage example
if __name__ == "__main__":
    env = SimpleLineEnv()
    obs, _ = env.reset()
    done = False
    while not done:
        action = env.action_space.sample()
        obs, reward, terminated, truncated, _ = env.step(action)
        env.render()
        done = terminated or truncated
    print("Finished.")
