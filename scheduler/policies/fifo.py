import os, sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

import copy
import random

import job_id_pair
from policy import Policy, PolicyWithPacking

class FIFOPolicy(Policy):
    def __init__(self, mode='base', seed=None, packing_threshold=1.5):
        super().__init__()
        self._name = 'FIFO'
        self._invalid_allocation_zero = True
        self._mode = mode
        self._allocation = {}
        self._scale_factors = {}
        if mode == 'base':
            self._rng = random.Random()
            if seed is not None:
                self._rng.seed(seed)
        elif mode == 'packing':
            self._packing_threshold = packing_threshold

    def _pack(self, queue, throughputs, scale_factors):
        while len(queue) > 0:
            # Only make a packing decision if combined normalized
            # throughput would provide a signficant gain.
            max_packed_throughput = self._packing_threshold
            job_id_to_pack_with = None
            job_id_to_schedule = queue.pop(0)

            # Find the already scheduled job with which the next job on
            # the queue will pack best with.
            for scheduled_job_id in self._allocation:
                assert scheduled_job_id != job_id_to_schedule
                assert scheduled_job_id in throughputs
                if scheduled_job_id.is_pair(): # DEBUG(xlc): 已经被packing的任务就不参与了
                    continue
                if (scale_factors[scheduled_job_id] !=\
                        scale_factors[job_id_to_schedule]):
                    continue
                worker_type = self._allocation[scheduled_job_id]
                merged_job_id = \
                        job_id_pair.JobIdPair(scheduled_job_id[0],
                                              job_id_to_schedule[0])
                packed_throughput = throughputs[merged_job_id][worker_type]
                normalized_packed_throughput = 0.0
                for i, single_job_id in enumerate(merged_job_id.singletons()):
                    if packed_throughput[i] <= 0.0:
                        continue
                    isolated_throughput = \
                            throughputs[single_job_id][worker_type]
                    normalized_packed_throughput += \
                            packed_throughput[i] / isolated_throughput
                if normalized_packed_throughput > max_packed_throughput: # DEBUG(xlc): 找最大的吞吐量
                    max_packed_throughput = normalized_packed_throughput
                    job_id_to_pack_with = scheduled_job_id
            if job_id_to_pack_with is None:
                # Terminate when we cannot find a job to pack with.
                # This respects the FIFO property of no jobs being able
                # to jump ahead in the queue.
                break
            else:
                # Transfer the allocation for the single job to the
                # packed job.
                self._output = None
                merged_job_id = \
                        job_id_pair.JobIdPair(job_id_to_pack_with[0],
                                              job_id_to_schedule[0])
                worker_type = self._allocation[job_id_to_pack_with]
                del self._allocation[job_id_to_pack_with]
                self._allocation[merged_job_id] = worker_type # DEBUG(xlc): 直接调度到packing任务的位置即可


    def get_allocation(self, throughputs, scale_factors, cluster_spec):
        available_workers = copy.deepcopy(cluster_spec)
        queue = []

        # Update the internal representation of scale_factors.
        for job_id in scale_factors:
            self._scale_factors[job_id] = scale_factors[job_id]

        # Reset the allocation when running in performance-aware mode.
        if self._mode != 'base': # DEBUG(xlc): 只有对于'base'的操作才是最准确的非抢占式FIFO, 其他方法都是每次贪心解决
            self._allocation = {}

        # Add all jobs that have not been allocated already to the queue.
        # Jobs should be added in order of arrival (i.e. according to Job ID). # DEBUG(xlc): JobId 本身就可以指示先到先服务的情况
        for job_id in sorted(list(throughputs.keys())):
            if job_id not in self._allocation and not job_id.is_pair():
                queue.append(job_id)

        # Find all completed jobs and schedule jobs off the queue to replace
        # them. Also determine how many workers are available.
        # NOTE: In performance-aware mode, this loop should be a no-op
        # because the allocation is reset.
        for scheduled_job_id in sorted(list(self._allocation.keys())):
            worker_type = self._allocation[scheduled_job_id]
            # Check if job has completed. DEBUG(xlc): 只有对那些完成了的任务, 才会执行这个操作
            if scheduled_job_id not in throughputs:
                # If only one job in a pair of co-located jobs completed, then
                # add the other job back to the queue.
                for single_job_id in scheduled_job_id.singletons(): # DEBUG(xlc): 如果执行完成的任务是pack任务, 就增加到队列
                    if single_job_id in throughputs:
                        queue.append(single_job_id)
                        queue.sort()
                if len(queue) > 0:
                    job_id_to_schedule = queue[0]
                    if (scale_factors[job_id_to_schedule] <=
                            available_workers[worker_type]):
                        worker_type = self._allocation[scheduled_job_id]
                        if throughputs[job_id_to_schedule][worker_type] > 0.0:
                            queue.pop(0)
                            self._allocation[job_id_to_schedule] = worker_type # DEBUG(xlc): 从队列里面将任务放到当前完成的任务位置里
                            available_workers[worker_type] -= \
                                scale_factors[job_id_to_schedule]
                del self._allocation[scheduled_job_id]
                del self._scale_factors[scheduled_job_id]
            else:
                # Job has not completed, subtract its allocated workers
                # from available_workers.
                available_workers[worker_type] -= \
                    scale_factors[scheduled_job_id]

        # Find all available workers.
        available_worker_types = []
        for worker_type in available_workers:
            if available_workers[worker_type] > 0:
                available_worker_types.append(worker_type)
        available_worker_types.sort()

        # Allocate resources to as many jobs as possible. DEBUG(xlc): 在这里好像是, 在完成FIFO之后, 还处理了未完全分配的机器
        while len(queue) > 0 and len(available_worker_types) > 0:
            job_id_to_schedule = queue.pop(0)
            scale_factor = scale_factors[job_id_to_schedule]
            available_worker_types_with_scale_factor = []
            original_available_worker_types_mapping = []
            for i, worker_type in enumerate(available_worker_types):
                if available_workers[worker_type] >= scale_factor:
                    available_worker_types_with_scale_factor.append(worker_type)
                    original_available_worker_types_mapping.append(i)
            if len(available_worker_types_with_scale_factor) == 0: # DEBUG(xlc): 当第一个任务无法被资源满足的时候, 就弹出准备packing
                break
            if self._mode == 'base': # DEBUG(xlc): 随机给一个worker进行分配, 感觉这里应该是最优者优先才对吧
                worker_type_idx = self._rng.randrange(
                        len(available_worker_types_with_scale_factor))
                worker_type = available_worker_types_with_scale_factor[worker_type_idx] # FIX(xlc): 增加了这一行, 真正做到随机
            else:
                # Find the worker_type with best performance for this job.
                worker_type = None
                worker_type_idx = None
                max_throughput = -1
                for i, x in enumerate(available_worker_types_with_scale_factor):
                    throughput = throughputs[job_id_to_schedule][x]
                    if throughput > max_throughput:
                        max_throughput = throughput
                        worker_type = x
                        worker_type_idx = i
            if throughputs[job_id_to_schedule][worker_type] > 0.0:
                self._allocation[job_id_to_schedule] = worker_type
                available_workers[worker_type] -= scale_factors[job_id_to_schedule]
                if available_workers[worker_type] == 0:
                    worker_type_idx =\
                        original_available_worker_types_mapping[worker_type_idx]
                    available_worker_types.pop(worker_type_idx)

        if self._mode == 'packing':
            self._pack(queue, throughputs, scale_factors) # DEBUG(xlc): 只有当queue不为空, 资源存在限制才会packing

        # Construct output allocation. # DEBUG(xlc): one-hot矩阵, 只有FIFO命中的项目才会被设置为1
        final_allocation = {}
        for job_id in throughputs:
            final_allocation[job_id] = \
                    {worker_type: 0.0 for worker_type in cluster_spec}
        for job_id, worker_type in self._allocation.items():
            final_allocation[job_id][worker_type] = 1.0

        return final_allocation

class FIFOPolicyWithPerf(Policy):
    def __init__(self, packing=False):
        super().__init__()
        self._name = 'FIFO_Perf'
        self._packing = packing
        self._policy = FIFOPolicy(mode='perf')

    def get_allocation(self, throughputs, scale_factors, cluster_spec):
        return self._policy.get_allocation(throughputs, scale_factors,
                                           cluster_spec)

class FIFOPolicyWithPacking(PolicyWithPacking):
    def __init__(self, packing_threshold=1.5):
        super().__init__()
        self._name = 'FIFO_Packing'
        self._policy = FIFOPolicy(mode='packing',
                                  packing_threshold=packing_threshold)

    def get_allocation(self, throughputs, scale_factors, cluster_spec):
        return self._policy.get_allocation(throughputs, scale_factors,
                                           cluster_spec)
