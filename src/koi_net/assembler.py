from collections import defaultdict, deque
import inspect
from enum import StrEnum
import math
from pprint import pp
from typing import Any, Protocol, Self
from dataclasses import make_dataclass

import structlog
from pydantic import BaseModel

from .entrypoints.base import EntryPoint

log = structlog.stdlib.get_logger()


class CompType(StrEnum):
    FACTORY = "FACTORY"
    OBJECT = "OBJECT"


class NodeContainer(Protocol):
    """Dummy 'shape' for node containers built by assembler."""
    entrypoint = EntryPoint

def gname(group: tuple[int]):
    return f"{len(group)}_{str(abs(hash(group)))[:5]}"

def ledge(edges: tuple[tuple[str, str]]):
    return ", ".join(f"({e[0]} -> {e[1]})" for e in edges)

class NodeAssembler:
    # Self annotation lying to type checker to reflect typing set in node blueprints
    def __new__(self) -> Self:
        """Returns assembled node container."""
        
        comps = self._collect_comps()
        adj, comp_types = self._build_deps(comps)
        build_order = self._build_order(adj)
        
        if len(build_order) != len(adj):
            # cycles in dependency graph
            node_seqs = self._find_cycles(adj)
            cge_map = self._find_cycle_groups(node_seqs)
            solutions = self._solve_cycles(cge_map)
            
            print(f"Found {len(solutions)} solutions:")
            for edges in solutions:
                print(", ".join(" -> ".join(edge) for edge in edges))
            
            uniq_solutions = {frozenset(sol) for sol in solutions}
            
            # cores = defaultdict(set)
            # for i, s1 in enumerate(uniq_solutions):
            #     for j, s2 in enumerate(uniq_solutions):
            #         if i >= j:
            #             continue
                    
            #         inter = s1 & s2
            #         if len(inter) >= 2:
            #             cores[frozenset(inter)].add(s1)
            #             cores[frozenset(inter)].add(s2)
            
            edge_sol_map = {}
            
            print(len(uniq_solutions))
            for sol in uniq_solutions:
                print(sol)
                # for edge in sol:
                    
            
            # print()
            # for intersection, solutions in cores.items():
            #     print(ledge(intersection), "...", " OR ".join(ledge(s - intersection) for s in solutions))
                
            # breakpoint()
            return solutions
        
        components = self._build_comps(build_order, adj, comp_types)
        node = self._build_node(components)
        
        return node
        
        old = list(comps.keys())
        new = build_order
        
        result = []
        
        for idx, item in enumerate(new):
            old_idx = old.index(item)
            if old_idx == idx:
                result.append(f"{idx}. {item}")
            else:
                result.append(f"{idx}. {item} (moved from {old_idx})")

        # print("\n".join(result))
        
        return node
    
    @classmethod
    def _collect_comps(cls):
        comps: dict[str, Any] = {}
        # adds components from base classes, including cls)
        for base in inspect.getmro(cls)[:-1]:
            for k, v in vars(base).items():
                # excludes built in, private, and `None` attributes
                if k.startswith("_") or v is None:
                    continue
                comps[k] = v
        return comps
    
    @classmethod
    def _build_deps(cls, comps) -> tuple[dict[str, list[str]], dict[str, CompType]]:
        """Returns dependency graph for components defined in `cls_build_order`.
        
        Graph representation is a dict where each key is a component name,
        and the value is tuple containing the component type, and a list
        of dependency component names.
        """
        
        comp_types = {}
        dep_graph = {}
        for comp_name in comps:
            try:
                comp = getattr(cls, comp_name)
            except AttributeError:
                raise Exception(f"Component '{comp_name}' not found in class definition")
            
            if not callable(comp):
                comp_types[comp_name] = CompType.OBJECT
                dep_names = []
            
            elif isinstance(comp, type) and issubclass(comp, BaseModel):
                comp_types[comp_name] = CompType.OBJECT
                dep_names = []
            
            else:
                sig = inspect.signature(comp)
                comp_types[comp_name] = CompType.FACTORY
                dep_names = list(sig.parameters)
                
            dep_graph[comp_name] = dep_names
            
        return dep_graph, comp_types
    
    @classmethod
    def _find_cycle(cls, adj) -> list[str]:
        visited = set()
        stack = []
        on_stack = set()
        
        def dfs(node):
            visited.add(node)
            stack.append(node)
            on_stack.add(node)
            
            for nxt in adj[node]:
                if nxt not in visited:
                    cycle = dfs(nxt)
                    if cycle:
                        return cycle
                
                elif nxt in on_stack:
                    idx = stack.index(nxt)
                    return stack[idx:] + [nxt]
                
            stack.pop()
            on_stack.remove(node)
            return None
        
        for node in adj:
            if node not in visited:
                cycle = dfs(node)
                if cycle:
                    return cycle
                
        return None
    
    @classmethod
    def _find_cycles(cls, adj: dict[str, list[str]]) -> list[tuple[str]]:
        cycles = []
        for node in adj:
            visited = {node: False for node in adj}
            start = node
            
            def dfs(nodes):
                head = nodes[-1]
                
                if visited[head]:
                    if head == start:
                        # check it is a unique cycle
                        if all(
                            # cycles different lengths
                            len(nodes) != len(cycle_seq) or
                            # cycles not equivalent
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
    
    @classmethod
    def _find_cycle_groups(cls, node_seqs: list[tuple[str]]):
        # converts list of node sequences to edge sequences
        # cycle # -> list of edges
        edge_seqs = [
            tuple(
                (nodes[j], nodes[j+1])
                for j in range(len(nodes) - 1)
            )
            for nodes in node_seqs
        ]
        
        for i, edge_seq in enumerate(edge_seqs):
            print(i, ":", ", ".join(" -> ".join(edge) for edge in edge_seq))
        
        # mapping of edge -> group of cycles it belongs to
        edge_cycle_group_map: dict[tuple[str, str], list[int]] = {}
        for i, edges in enumerate(edge_seqs):
            for edge in edges:
                edge_cycle_group_map.setdefault(edge, [])
                edge_cycle_group_map[edge].append(i)
        
        cycle_group_edges_map: dict[tuple[int], list[frozenset[str, str]]] = {}
        for edge, cycles in edge_cycle_group_map.items():
            cycle_group = frozenset(cycles)
            
            cycle_group_edges_map.setdefault(cycle_group, [])
            cycle_group_edges_map[cycle_group].append(edge)
        
        return cycle_group_edges_map
    
    @classmethod
    def _solve_cycles(cls, cge_map: dict[frozenset[int], list[tuple[str, str]]]):
        print("STARTING CYCLE SOLVER")
        
        solutions = []
        min_solution = math.inf
        def recurse(
            cge_map: dict[frozenset[int], list[tuple[str, str]]],
            removed_edges: tuple[tuple[str, str]] = ()
        ):
            cge_map = dict(sorted(
                cge_map.items(),
                key=lambda i: len(i[0]),
                reverse=True
            ))
            
            nonlocal min_solution
            
            # for group, edges in cge_map.items():
            #     print(gname(group), ledge(edges))
            
            # quit()
            
            # print(f"There are {len(cge_map)} cycle group(s):\n")
            
            # max_cgs = []
            # for group in cge_map.keys():
            #     if max_cgs and len(group) < len(max_cgs[0]):
            #         break
                
            #     max_cgs.append(group)
                
            # print(max_cgs)
            
            for max_group in cge_map:
                for edge in cge_map[max_group]:
                    next_removed_edges = removed_edges + (edge,)
                    
                    if len(next_removed_edges) > min_solution:
                        # print("TOO LONG:", ledge(next_removed_edges))
                        continue
                    
                    curr_cge_map = cge_map.copy()
                    del curr_cge_map[max_group]
                    
                    next_cge_map: dict[frozenset[int], list[tuple[str, str]]] = {}
                    for curr_group, edges in curr_cge_map.items():
                        new_group = curr_group - max_group
                        
                        # print(",".join(map(str,curr_group)), "->", ",".join(map(str, new_group)))
                        
                        if not new_group:
                            continue
                        
                        next_cge_map.setdefault(new_group, [])
                        next_cge_map[new_group].extend(edges)
                    
                    # print(next_cge_map)
                    
                    # print(next_removed_edges)
                    if next_cge_map:
                        recurse(next_cge_map, next_removed_edges)
                    else:
                        if len(next_removed_edges) < min_solution:
                            solutions.clear()
                            solutions.append(next_removed_edges)
                            min_solution = len(next_removed_edges)
                            print(f"NEW MIN {min_solution}:", ledge(next_removed_edges))
                        elif len(next_removed_edges) == min_solution:
                            solutions.append(next_removed_edges)

                            # print("EQUAL", ledge(next_removed_edges))
                            
        recurse(cge_map)
        return solutions
    
    @classmethod
    def _build_order(cls, adj) -> list[str]:
        # adj list: n -> outgoing neighbors
        
        # reverse adj list: n -> incoming neighbors
        r_adj: dict[str, list[str]] = {}
        
        # computes reverse adjacency list
        for node in adj:
            r_adj.setdefault(node, [])
            for n in adj[node]:
                r_adj.setdefault(n, [])
                r_adj[n].append(node)
        
        out_degree: dict[str, int] = {
            n: len(neighbors) 
            for n, neighbors in adj.items()
        }
        
        queue = deque()
        for node in out_degree:
            if out_degree[node] == 0:
                queue.append(node)
        
        ordered: list[str] = []
        while queue:
            n = queue.popleft()
            ordered.append(n)
            for next_n in r_adj[n]:
                out_degree[next_n] -= 1
                if out_degree[next_n] == 0:
                    queue.append(next_n)
                    
        
        
        # if len(ordered) != len(adj):
        #     cycle_nodes = set(adj.keys()) - set(ordered)
        #     cycle_adj = {}
        #     for n in list(cycle_nodes):
        #         cycle_adj[n] = set(adj[n]) & cycle_nodes
        #         print(n, "->", cycle_adj[n])
                
        #     cycle = cls._find_cycle(cycle_adj)
        
        #     print("FOUND CYCLE")
        #     print(" -> ".join(cycle))
            
        print(len(ordered), "/", len(adj))
        
        return ordered
        
    @classmethod
    def _visualize(cls) -> str:
        """Returns representation of dependency graph in Graphviz DOT language."""
        dep_graph = cls._build_deps()
        
        s = "digraph G {\n"
        for node, neighbors in dep_graph.items():
            sub_s = node
            if neighbors:
                sub_s += f"-> {', '.join(neighbors)}"
            sub_s = sub_s.replace("graph", "graph_") + ";"
            s += " " * 4 + sub_s + "\n"
        s += "}"
        return s
        
    @classmethod
    def _build_comps(
        cls,
        build_order: list[str],
        adj: dict[str, list[str]],
        comp_type: dict[str, CompType]
    ) -> dict[str, Any]:
        """Returns assembled components from dependency graph."""
        
        components: dict[str, Any] = {}
        for comp_name in build_order:
        # for comp_name, (comp_type, dep_names) in dep_graph.items():
            comp = getattr(cls, comp_name, None)
            
            if comp_type[comp_name] == CompType.OBJECT:
                components[comp_name] = comp
            
            elif comp_type[comp_name] == CompType.FACTORY:
                # builds depedency dict for current component
                dependencies = {}
                for dep in adj[comp_name]:
                    if dep not in components:
                        raise Exception(f"Couldn't find required component '{dep}'")
                    dependencies[dep] = components[dep]
                components[comp_name] = comp(**dependencies)
                
        return components

    @classmethod
    def _build_node(cls, components: dict[str, Any]) -> NodeContainer:
        """Returns node container from components."""
        
        NodeContainer = make_dataclass(
            cls_name="NodeContainer",
            fields=[
                (name, type(component)) 
                for name, component
                in components.items()
            ],
            frozen=True
        )
        
        return NodeContainer(**components)
