from mimetypes import types_map
import numpy as np

types = ['v100', 'p100', 'k80']
prices = np.array([10, 20, 30])
steps_remain = np.array([60, 30])

throughout = np.array(
    [[1, 2, 4],
    [2, 3, 1]]
)
(m, n) = throughout.shape

time_remain_matrix = steps_remain[:, np.newaxis] / throughout
print(time_remain_matrix)
max_time_remain_sort_indexes = np.max(time_remain_matrix, axis=1).argsort()
print(max_time_remain_sort_indexes)
sort_throughputs = throughout[max_time_remain_sort_indexes]
sort_steps_remain = steps_remain[max_time_remain_sort_indexes]
print(sort_throughputs)

price_remain_matrix = np.multiply(sort_steps_remain[:, np.newaxis] / sort_throughputs, prices)
print("steps_remain[:, np.newaxis] / sort_throughputs: ", sort_steps_remain[:, np.newaxis] / sort_throughputs)
print("price_remain_matrix: ", price_remain_matrix)
min_time_remain_sort_indexes = np.argmin(price_remain_matrix, axis=1)
print(min_time_remain_sort_indexes)

# result = np.zeros_like(throughout)
results = []
for row_index in range(m):
    results.append((max_time_remain_sort_indexes[row_index], min_time_remain_sort_indexes[row_index]))

print("result: ", results)
