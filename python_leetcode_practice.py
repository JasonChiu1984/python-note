"""LeetCode practice companion: original teaching implementations.
Python 3.10+; standard library only. Run: python3 python_leetcode_practice.py
The tests include documented extensions outside official problem contracts.
"""
from __future__ import annotations

import unittest
import itertools
from collections import deque, OrderedDict
from dataclasses import dataclass

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
