from pprint import pp
from koi_net.core import FullNode

type edge_pair = tuple[str, str]


comps = FullNode._collect_comps()

full_adj, comp_types = FullNode._build_deps(comps)

build_order = FullNode._build_order(full_adj)

if len(build_order) == len(full_adj):
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

if __name__ == "__main__":
# def compute(adj):
    cycles_array = find_cycles(adj)
    cycles_edges = get_edge_seq(cycles_array)
    edge_groups = get_edge_groups(cycles_edges)
    cycle_groups = get_cycle_groups(edge_groups)
    
    print("\nbiggest cycle group edges:")
    
    while True:
        sorted_cycle_groups = sorted(cycle_groups.keys(), key=lambda k: len(k))
        
        # print(sorted_cycle_groups)
        
        biggest_group = sorted_cycle_groups.pop()
        
        # print(biggest_group)
        
        # add the edge to removed edges list
        # iterate through remaining groups, remove the cycles in the biggest group and recombine
        # for example after cycle 1 is removed, group (1,) is eliminated and group (1, 2) is merged with group (2,)
        
        edge_candidates = cycle_groups[biggest_group]
        
        # print(edge_candidates)
        
        removed_edge = edge_candidates.pop()
        
        print(removed_edge, "->", biggest_group)
        
        del cycle_groups[biggest_group]
        
        next_cycle_groups: dict[tuple[int], list[tuple[str, str]]] = {}
        for cycle_group, edges in cycle_groups.items():
            remaining_groups = tuple(set(cycle_group) - set(biggest_group))
            # print(remaining_groups)
            if not remaining_groups:
                pass
                # print("deleted cycle group", cycle_group)
            
            else:
                # print("remaining groups", remaining_groups)
                
                next_cycle_groups.setdefault(remaining_groups, [])
                next_cycle_groups[remaining_groups].extend(edges)
                
        cycle_groups = next_cycle_groups
            
        
        if not cycle_groups:
            break
        
        # remaining_cycles = set(range(len(cycles_array)))
        # cgroup_edge_list = list(cycle_groups.items())

    # while True:
    #     cgroup_edge_list.sort(key=lambda x: len(x[0]))
        
    #     optimal_edge_group = cgroup_edge_list.pop()

    # compute(adj)