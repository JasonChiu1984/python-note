"""LeetCode practice companion: original teaching implementations.
Python 3.10+; standard library only. Run: python3 python_leetcode_practice.py
The tests include documented extensions outside official problem contracts.
"""
from __future__ import annotations

import unittest
import itertools
from collections import deque, OrderedDict
from dataclasses import dataclass
from heapq import heappop, heappush

# LeetCode #1: https://leetcode.com/problems/two-sum/
def two_sum(nums: list[int], target: int) -> list[int]:
    seen: dict[int, int] = {}
    for index, value in enumerate(nums):
        needed = target - value
        if needed in seen:
            return [seen[needed], index]
        seen[value] = index
    raise ValueError("no pair adds up to target")


# LeetCode #20: https://leetcode.com/problems/valid-parentheses/
def valid_parentheses(s: str) -> bool:
    pairs = {")": "(", "]": "[", "}": "{"}
    stack: list[str] = []
    for char in s:
        if char in "([{":
            stack.append(char)
        elif char in pairs:
            if not stack or stack.pop() != pairs[char]:
                return False
        else:
            return False
    return not stack


# LeetCode #704: https://leetcode.com/problems/binary-search/
def binary_search(nums: list[int], target: int) -> int:
    left, right = 0, len(nums)
    while left < right:
        mid = (left + right) // 2
        if nums[mid] < target:
            left = mid + 1
        else:
            right = mid
    if left < len(nums) and nums[left] == target:
        return left
    return -1


# LeetCode #3: https://leetcode.com/problems/longest-substring-without-repeating-characters/
def longest_unique(s: str) -> int:
    last: dict[str, int] = {}
    left = best = 0
    for right, char in enumerate(s):
        if char in last:
            left = max(left, last[char] + 1)
        last[char] = right
        best = max(best, right - left + 1)
    return best


# LeetCode #56: https://leetcode.com/problems/merge-intervals/
def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:
    merged: list[list[int]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return merged


# LeetCode #102: https://leetcode.com/problems/binary-tree-level-order-traversal/
@dataclass
class TreeNode:
    val: int
    left: TreeNode | None = None
    right: TreeNode | None = None

def level_order(root: TreeNode | None) -> list[list[int]]:
    if root is None:
        return []
    queue = deque([root])
    result: list[list[int]] = []
    while queue:
        layer: list[int] = []
        for _ in range(len(queue)):
            node = queue.popleft()
            layer.append(node.val)
            if node.left is not None:
                queue.append(node.left)
            if node.right is not None:
                queue.append(node.right)
        result.append(layer)
    return result


# LeetCode #322: https://leetcode.com/problems/coin-change/
def coin_change(coins: list[int], amount: int) -> int:
    if amount < 0 or any(coin <= 0 for coin in coins):
        raise ValueError("amount must be >= 0; coins must be > 0")
    unreachable = amount + 1
    dp = [0] + [unreachable] * amount
    for subtotal in range(1, amount + 1):
        for coin in coins:
            if coin <= subtotal:
                dp[subtotal] = min(dp[subtotal], dp[subtotal - coin] + 1)
    return -1 if dp[amount] == unreachable else dp[amount]


# LeetCode #146: https://leetcode.com/problems/lru-cache/
class LRUCache:
    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self.data: OrderedDict[int, int] = OrderedDict()

    def get(self, key: int) -> int:
        if key not in self.data:
            return -1
        self.data.move_to_end(key)
        return self.data[key]

    def put(self, key: int, value: int) -> None:
        self.data[key] = value
        self.data.move_to_end(key)
        if len(self.data) > self.capacity:
            self.data.popitem(last=False)


# Original transfer cases, independent of any online judge.
def count_target_subarrays(values: list[int], target: int) -> int:
    """Count nonempty contiguous intervals with sum target; negative values allowed."""
    prefix = count = 0
    frequencies = {0: 1}
    for value in values:
        prefix += value
        count += frequencies.get(prefix - target, 0)
        frequencies[prefix] = frequencies.get(prefix, 0) + 1
    return count


def min_batch_capacity(weights: list[int], batches: int) -> int:
    """Minimum capacity for at most batches nonempty, ordered, contiguous groups."""
    if not weights or any(weight <= 0 for weight in weights) or batches < 1:
        raise ValueError("require positive weights and batches, with at least one item")

    def feasible(capacity: int) -> bool:
        groups, load = 1, 0
        for weight in weights:
            if load + weight > capacity:
                groups += 1
                load = 0
            load += weight
        return groups <= batches

    low, high = max(weights), sum(weights)
    while low < high:
        middle = (low + high) // 2
        if feasible(middle):
            high = middle
        else:
            low = middle + 1
    return low


def dependency_order(tasks: list[str], edges: list[tuple[str, str]]) -> list[str]:
    """Return an order respecting each directed edge (before, after); reject cycles."""
    indegree = dict.fromkeys(tasks, 0)
    if len(indegree) != len(tasks):
        raise ValueError("task identifiers must be unique")
    followers: dict[str, list[str]] = {task: [] for task in tasks}
    for before, after in edges:
        if before not in indegree or after not in indegree:
            raise ValueError("edge endpoints must be declared tasks")
        followers[before].append(after)
        indegree[after] += 1
    ready = deque(task for task in tasks if indegree[task] == 0)
    ordered = []
    while ready:
        before = ready.popleft()
        ordered.append(before)
        for after in followers[before]:
            indegree[after] -= 1
            if indegree[after] == 0:
                ready.append(after)
    if len(ordered) != len(tasks):
        raise ValueError("dependency cycle")
    return ordered


def shortest_distances(
    graph: dict[str, list[tuple[str, int]]], source: str
) -> dict[str, int]:
    """Return distances to reachable vertices; integer edge weights must be nonnegative."""
    vertices = set(graph)
    for neighbors in graph.values():
        for vertex, weight in neighbors:
            if weight < 0:
                raise ValueError("Dijkstra requires nonnegative weights")
            vertices.add(vertex)
    if source not in vertices:
        raise ValueError("unknown source")
    distance = {source: 0}
    pending = [(0, source)]
    while pending:
        total, here = heappop(pending)
        if total != distance[here]:
            continue
        for neighbor, weight in graph.get(here, []):
            proposal = total + weight
            if neighbor not in distance or proposal < distance[neighbor]:
                distance[neighbor] = proposal
                heappush(pending, (proposal, neighbor))
    return distance


class PracticeTests(unittest.TestCase):
    def test_1_example(self):
        assert two_sum([8, 1, 6, 4], 10) == [2, 3]
        assert two_sum([5, 5], 10) == [0, 1]
        assert two_sum([-4, 9, 2], -2) == [0, 2]

    def test_20_example(self):
        assert valid_parentheses("{[()]}") is True
        assert valid_parentheses("{(})") is False
        assert valid_parentheses("]") is False
        assert valid_parentheses("((") is False
        assert valid_parentheses("") is True  # 教材擴充

    def test_704_example(self):
        assert binary_search([-8, -2, 4, 9, 13], 9) == 3
        assert binary_search([-8, -2, 4, 9, 13], 20) == -1
        assert binary_search([7], 7) == 0
        assert binary_search([], 1) == -1  # 教材擴充

    def test_3_example(self):
        assert longest_unique("abba") == 2
        assert longest_unique("dvdf") == 3
        assert longest_unique("zzzz") == 1
        assert longest_unique("") == 0
        assert longest_unique("台北台南") == 3  # 教材延伸

    def test_56_example(self):
        source = [[9, 11], [2, 5], [5, 8], [3, 4]]
        before = [row[:] for row in source]
        answer = merge_intervals(source)
        assert answer == [[2, 8], [9, 11]]
        assert source == before
        answer[0][0] = -99
        assert source == before  # 內層串列也沒有共用
        assert merge_intervals([[6, 6]]) == [[6, 6]]

    def test_102_example(self):
        root = TreeNode(10, TreeNode(6, right=TreeNode(8)),
                        TreeNode(14, left=TreeNode(12)))
        assert level_order(root) == [[10], [6, 14], [8, 12]]
        assert level_order(None) == []
        assert level_order(TreeNode(0)) == [[0]]

    def test_322_example(self):
        assert coin_change([1, 4, 6], 8) == 2
        assert coin_change([4, 6], 7) == -1
        assert coin_change([3, 7], 0) == 0
        assert coin_change([2, 2, 5], 9) == 3

    def test_146_example(self):
        cache = LRUCache(2)
        cache.put(7, 70)
        cache.put(9, 90)
        assert cache.get(7) == 70
        cache.put(4, 40)
        assert cache.get(9) == -1
        cache.put(7, 0)
        assert cache.get(7) == 0
        assert list(cache.data) == [4, 7]

    def test_two_sum_no_solution(self):
        with self.assertRaises(ValueError):
            two_sum([2, 6], 1)

    def test_two_sum_distinct_indices(self):
        for nums in itertools.product(range(-2, 3), repeat=4):
            for target in range(-3, 4):
                possible = any(nums[i] + nums[j] == target
                               for i in range(len(nums))
                               for j in range(i + 1, len(nums)))
                if possible:
                    i, j = two_sum(list(nums), target)
                    self.assertNotEqual(i, j)
                    self.assertEqual(nums[i] + nums[j], target)
                else:
                    with self.assertRaises(ValueError):
                        two_sum(list(nums), target)

    def test_brackets_invalid_character(self):
        self.assertFalse(valid_parentheses("(a)"))

    def test_binary_bounds(self):
        nums = [-5, 0, 7, 12]
        for target in range(-7, 15):
            expected = nums.index(target) if target in nums else -1
            self.assertEqual(binary_search(nums, target), expected)
        self.assertEqual(binary_search([2, 2, 2], 2), 0)

    def test_window_against_brute_force(self):
        for size in range(7):
            for chars in itertools.product("abc", repeat=size):
                s = "".join(chars)
                expected = max((j - i for i in range(size + 1)
                                for j in range(i, size + 1)
                                if len(set(s[i:j])) == j - i), default=0)
                self.assertEqual(longest_unique(s), expected)

    def test_merge_nested_empty_and_touching(self):
        self.assertEqual(merge_intervals([]), [])
        self.assertEqual(merge_intervals([[2, 9], [3, 5], [9, 12]]), [[2, 12]])
        self.assertEqual(merge_intervals([[1, 1], [1, 1]]), [[1, 1]])

    def test_tree_chain(self):
        root = TreeNode(1, right=TreeNode(2, right=TreeNode(3)))
        self.assertEqual(level_order(root), [[1], [2], [3]])

    def test_coin_invalid_inputs(self):
        for coins, amount in [([0, 2], 3), ([-1], 2), ([2], -1)]:
            with self.assertRaises(ValueError):
                coin_change(coins, amount)

    def test_coin_against_bfs(self):
        # An independent shortest-path oracle for small, finite test cases.
        for coins in ([1, 4, 6], [3, 5], [2, 7], [4, 6]):
            for amount in range(25):
                queue = deque([(0, 0)])
                visited = {0}
                expected = -1
                while queue:
                    value, count = queue.popleft()
                    if value == amount:
                        expected = count
                        break
                    for coin in coins:
                        nxt = value + coin
                        if nxt <= amount and nxt not in visited:
                            visited.add(nxt)
                            queue.append((nxt, count + 1))
                self.assertEqual(coin_change(list(coins), amount), expected)

    def test_lru_capacity_one(self):
        cache = LRUCache(1)
        cache.put(2, 3)
        cache.put(2, 4)
        self.assertEqual(cache.get(2), 4)
        cache.put(9, 6)
        self.assertEqual(cache.get(2), -1)
        self.assertEqual(cache.get(9), 6)

    def test_lru_update_refreshes(self):
        cache = LRUCache(2)
        cache.put(1, 10)
        cache.put(2, 20)
        cache.put(1, 30)
        cache.put(3, 40)
        self.assertEqual(cache.get(2), -1)
        self.assertEqual(cache.get(1), 30)
        self.assertEqual(len(cache.data), 2)

    def test_lru_invalid_capacity(self):
        for capacity in (0, -1):
            with self.assertRaises(ValueError):
                LRUCache(capacity)


class ResearchTests(unittest.TestCase):
    def test_prefix_boundary_and_repeated_sums(self):
        self.assertEqual(count_target_subarrays([], 0), 0)
        self.assertEqual(count_target_subarrays([0, 0, 0], 0), 6)
        self.assertEqual(count_target_subarrays([1, -1, 1], 0), 2)

    def test_prefix_exhaustive_against_interval_enumeration(self):
        for size in range(6):
            for values in itertools.product((-1, 0, 1), repeat=size):
                for target in range(-2, 3):
                    oracle = sum(
                        sum(values[i:j]) == target
                        for i in range(size)
                        for j in range(i + 1, size + 1)
                    )
                    self.assertEqual(count_target_subarrays(list(values), target), oracle)

    def test_capacity_rejects_inputs_and_preserves_order(self):
        for weights, batches in (([], 1), ([0], 1), ([-1], 2), ([3], 0)):
            with self.subTest(weights=weights, batches=batches), self.assertRaises(ValueError):
                min_batch_capacity(weights, batches)
        values = [7, 2, 5, 10, 8]
        self.assertEqual(min_batch_capacity(values, 2), 18)
        self.assertEqual(values, [7, 2, 5, 10, 8])
        self.assertEqual(min_batch_capacity([2], 10), 2)

    def test_capacity_against_all_cut_sets(self):
        for size in range(1, 6):
            for weights in itertools.product((1, 2, 3), repeat=size):
                for batches in range(1, size + 1):
                    oracle = min(
                        max(sum(weights[left:right]) for left, right in zip(cuts, cuts[1:]))
                        for groups in range(1, batches + 1)
                        for internal in itertools.combinations(range(1, size), groups - 1)
                        for cuts in [(0, *internal, size)]
                    )
                    self.assertEqual(min_batch_capacity(list(weights), batches), oracle)

    def test_dependency_rejects_cycle_unknown_and_duplicates(self):
        self.assertEqual(dependency_order([], []), [])
        self.assertEqual(dependency_order(["a", "b"], [("a", "b"), ("a", "b")]), ["a", "b"])
        for tasks, edges in (
            (["a"], [("a", "a")]),
            (["a"], [("a", "x")]),
            (["a", "a"], []),
        ):
            with self.subTest(tasks=tasks, edges=edges), self.assertRaises(ValueError):
                dependency_order(tasks, edges)

    def test_dependency_against_permutation_oracle(self):
        tasks = ["a", "b", "c"]
        possible = list(itertools.permutations(tasks, 2))
        for flags in itertools.product((False, True), repeat=len(possible)):
            edges = [edge for edge, enabled in zip(possible, flags) if enabled]
            oracle = {
                order for order in itertools.permutations(tasks)
                if all(order.index(a) < order.index(b) for a, b in edges)
            }
            if oracle:
                self.assertIn(tuple(dependency_order(tasks, edges)), oracle)
            else:
                with self.assertRaisesRegex(ValueError, "cycle"):
                    dependency_order(tasks, edges)

    def test_shortest_paths_rejects_negative_and_unknown_source(self):
        with self.assertRaisesRegex(ValueError, "nonnegative"):
            shortest_distances({"s": [], "x": [("y", -1)]}, "s")
        with self.assertRaisesRegex(ValueError, "unknown"):
            shortest_distances({"s": []}, "t")
        self.assertEqual(shortest_distances({"a": [("b", 1)]}, "b"), {"b": 0})

    def test_shortest_paths_stale_entries_zero_and_unreachable(self):
        graph = {"s": [("a", 10), ("b", 1)], "b": [("a", 1)], "a": [("c", 0)], "x": []}
        self.assertEqual(shortest_distances(graph, "s"), {"s": 0, "a": 2, "b": 1, "c": 2})
        self.assertNotIn("x", shortest_distances(graph, "s"))

    def test_shortest_paths_against_bounded_edge_relaxation(self):
        nodes = ["a", "b", "c"]
        pairs = list(itertools.permutations(nodes, 2))
        inf = float("inf")
        for weights in itertools.product((None, 0, 2), repeat=len(pairs)):
            graph = {v: [] for v in nodes}
            for (before, after), weight in zip(pairs, weights):
                if weight is not None:
                    graph[before].append((after, weight))
            oracle = {node: (0 if node == "a" else inf) for node in nodes}
            for _ in range(len(nodes) - 1):
                previous = oracle.copy()
                for before, edges in graph.items():
                    for after, weight in edges:
                        oracle[after] = min(oracle[after], previous[before] + weight)
            self.assertEqual(shortest_distances(graph, "a"),
                             {node: d for node, d in oracle.items() if d != inf})


if __name__ == "__main__":
    unittest.main(verbosity=2)
