from array import array

from fastmath import add_range, weighted_sum


values = array("d", [1.0, 2.0, 3.0])

print(f"add_range(100) = {add_range(100)}")
print(f"weighted_sum([1, 2, 3], 0.5) = {weighted_sum(values, 0.5)}")
