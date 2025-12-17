# mcmf.py
import networkx as nx
from dfinit import euclid_dist

def solve_min_cost_driver_relocation(df, per_hex_out_caps):
    supply = {
        r.HexID: int(r.Drivers - r.Riders)
        for _, r in df.iterrows()
        if r.Drivers > r.Riders
    }
    demand = {
        r.HexID: int(r.Riders - r.Drivers)
        for _, r in df.iterrows()
        if r.Riders > r.Drivers
    }

    if not supply or not demand:
        return []

    G = nx.DiGraph()
    SRC, SNK = "source", "sink"
    G.add_node(SRC)
    G.add_node(SNK)

    for s, amt in supply.items():
        cap = min(per_hex_out_caps.get(s, amt), amt)
        if cap > 0:
            G.add_edge(SRC, s, capacity=cap, weight=0)

    for d, need in demand.items():
        G.add_edge(d, SNK, capacity=need, weight=0)

    for s in supply:
        for d in demand:
            G.add_edge(s, d,
                       capacity=9999,
                       weight=int(round(euclid_dist(s, d))))

    try:
        flow = nx.max_flow_min_cost(G, SRC, SNK)
    except Exception:
        return []

    moves = []
    for s in supply:
        for d in demand:
            m = int(flow.get(s, {}).get(d, 0))
            if m > 0:
                moves.append((s, d, m))

    return moves
