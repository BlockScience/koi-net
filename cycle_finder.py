from pprint import pp

from koi_net.core import FullNode

type edge_pair = tuple[str, str]


comps = FullNode._collect_comps()

full_adj, comp_types = FullNode._build_deps(comps)

build_order = FullNode._build_order(full_adj)

def numbered_node(node: str):
    return f"{node}_{build_order.index(node) + 1}"



if len(build_order) == len(full_adj):
    s = "digraph G {\n"
    for node, neighbors in full_adj.items():
        sub_s = numbered_node(node)
        if neighbors:
            sub_s += f"-> {', '.join(numbered_node(n) for n in neighbors)}"
        # sub_s = sub_s.replace("graph", "graph_") + ";"
        s += " " * 4 + sub_s + "\n"
    s += "}"

    print(s)
    quit()
    
# print("cycle detected")

cycle_nodes = set(full_adj.keys()) - set(build_order)

adj = {}
for n in list(cycle_nodes):
    adj[n] = set(full_adj[n]) & cycle_nodes
    # print(n, "->", cycle_adj[n])



def find_cycles(adj: dict[str, list[str]]) -> list[tuple[str]]:
    cycles = []
    for node in adj:
        visited = {node: False for node in adj}
        start = node
        
        def dfs(nodes):
            head = nodes[-1]
            
            if visited[head]:
                if head == start:
                    # unique cycle
                    if all(
                        len(nodes) != len(cycle_seq) or 
                        "".join(nodes[:-1]) not in "".join(cycle_seq[:-1]) * 2
                        for cycle_seq in cycles
                    ):
                        cycles.append(nodes)
                return
        
            visited[head] = True
            for child in adj[head]:
                dfs(nodes + (child,))
                
            visited[head] = False
        
        dfs((node,))
    return cycles


def get_edge_seq(node_seq: tuple) -> list[tuple[edge_pair]]:
    edges_seq = []
    for n, c in enumerate(node_seq):
        print(f"cycle {n}:\n", " -> ".join(c), end="\n\n")
        
        edges = tuple(
            (c[i], c[i+1]) 
            for i in range(len(c) - 1)
        )
            
        edges_seq.append(edges)
    return edges_seq



def get_edge_groups(edge_seq: list[tuple[edge_pair]]):
    """Returns a hashmap where each edge -> list of cycles it belongs to."""
    edge_cgroup_map: dict[edge_pair, list[int]] = {}
    for n, edges in enumerate(edge_seq):
        for edge in edges:
            edge_cgroup_map.setdefault(edge, [])
            edge_cgroup_map[edge].append(n)
            
    return edge_cgroup_map



# cycle groups -> edges

def get_cycle_groups(edge_group: dict[edge_pair, list[int]]):
    cgroup_edge_map: dict[tuple[int], list[edge_pair]] = {}

    print("edge membership in cycles")
    for edge, cycles in edge_group.items():
        
        cgroup_edge_map.setdefault(tuple(cycles), [])
        cgroup_edge_map[tuple(cycles)].append(edge)
        
        # if len(cycles) > most_cycles:
        #     most_cycles = len(cycles)
        #     key_edges = [edge]
        # elif len(cycles) == most_cycles:
        #     key_edges.append(edge)
        
        print(f"{edge[0]} -> {edge[1]}: {cycles}")
    
    return cgroup_edge_map

def gname(group: tuple[int]):
    return f"{len(group)}_{str(abs(hash(group)))[:5]}"

if __name__ == "__main__":
# def compute(adj):
    cycles_array = find_cycles(adj)
    cycles_edges = get_edge_seq(cycles_array)
    edge_groups = get_edge_groups(cycles_edges)
    cycle_groups = get_cycle_groups(edge_groups)
        
    solutions = []
    
    print("\nSTARTING CYCLE SOLVER")
    def recurse(
        cycle_groups: dict[tuple[int], list[edge_pair]],
        removed_edges: list[edge_pair] = []
    ):
        # (1, 2, 3) -> [(u, v), (w, y), ...]
        
        if solutions and len(removed_edges) > len(solutions[0]):
            print("EXCEEDED MIN SOLUTION DEPTH")
            return
        
        sorted_cycle_groups = sorted(cycle_groups.keys(), key=lambda k: len(k))
        
        print(f"There are {len(cycle_groups)} cycle group(s):\n")
        
        for group in reversed(sorted_cycle_groups):
            print(gname(group), [" -> ".join(edge) for edge in cycle_groups[group]])
        
        print(f"\nand {len(removed_edges)} removed edge(s):")
        print(", ".join(" -> ".join(edge) for edge in removed_edges))
        
        biggest_groups = []
        biggest_group_len = len(sorted_cycle_groups[-1])
        while len(group := sorted_cycle_groups.pop()) == biggest_group_len:
            biggest_groups.append(group)
            if not sorted_cycle_groups:
                break
        
        print("The biggest groups are: ", [gname(g) for g in biggest_groups])
        
        # add the edge to removed edges list
        # iterate through remaining groups, remove the cycles in the biggest group and recombine
        # for example after cycle 1 is removed, group (1,) is eliminated and group (1, 2) is merged with group (2,)
        
        for biggest_group in biggest_groups:
            edge_candidates = cycle_groups[biggest_group]
            
            for edge_candidate in edge_candidates:
                print("Edge candidate", " -> ".join(edge_candidate), ":", biggest_group)
                
                curr_cycle_groups = cycle_groups.copy()
                del curr_cycle_groups[biggest_group]
                
                next_cycle_groups = {}
                for cycle_group, edges in curr_cycle_groups.items():
                    # print("start", cycle_group)
                    
                    remaining_groups = tuple(set(cycle_group) - set(biggest_group))
                    # print("finish", remaining_groups)

                    if remaining_groups:
                        next_cycle_groups.setdefault(remaining_groups, [])
                        next_cycle_groups[remaining_groups].extend(edges)
                
                next_removed_edges = removed_edges + [edge_candidate]
                if next_cycle_groups:
                    recurse(next_cycle_groups, next_removed_edges)
                
                else:
                    solutions.append(next_removed_edges)
                    solutions.sort(key=lambda x: len(x))
                    print("SOLUTION", next_removed_edges)
                    return
    
    recurse(cycle_groups)

    print()
    for s in solutions:
        print(f"{len(s)} edge solution: {', '.join(' -> '.join(n for n in edge) for edge in s)}")