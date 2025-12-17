# main.py
import time
import matplotlib.pyplot as plt
from dfinit import *
from rl_policy import Policy
from train_and_evaluate import HexEnv, Forecaster, train, evaluate

env = HexEnv(df_init, Forecaster(), seed=SEED)
state_dim = env.state_vector().shape[0]
policy = Policy(state_dim)

t0 = time.time()
logs = train(env, policy)
print(f"Training time: {time.time() - t0:.2f}s")

eval_env = HexEnv(df_init, Forecaster(), seed=SEED + 7)
df_moves = evaluate(eval_env, policy)

before = df_init.rename(columns={
    "Riders": "Riders_before",
    "Drivers": "Drivers_before"
})
after = eval_env.df.rename(columns={
    "Riders": "Riders_after",
    "Drivers": "Drivers_after"
})

merged = before.merge(after, on="HexID")

print("\nFinal driver-only relocation results (before → after):")
print(merged.to_markdown(index=False))

balanced_before = sum(
    before.Drivers_before == before.Riders_before
)
balanced_after = sum(
    after.Drivers_after == after.Riders_after
)

print(f"\nBalanced zones before: {balanced_before} / {len(before)}")
print(f"Balanced zones after:  {balanced_after} / {len(after)}")

print("\nMoves performed each timestep:")
print(df_moves.to_markdown(index=False))

plt.figure(figsize=(6, 3))
plt.plot(logs)
plt.title("Training reward per episode")
plt.grid(True)
# plt.show()
