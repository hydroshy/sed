# JobManager Performance Optimization Plan

## Current Performance Issues (từ logs):

1. **Multiple Job Objects**: 
   - `<picamera2.job.Job object at 0x7fff...>` - Nhiều instances được tạo
   - Memory overhead và context switching

2. **Frequent Execution**:
   - Job chạy mỗi ~15ms (66 FPS)
   - DetectTool chỉ cần ~10-15 FPS cho real-time
   - Wasted computation

3. **Frame Processing Redundancy**:
   - BGR→RGB conversion repeated
   - Frame copying overhead
   - No frame caching

## Optimization Strategies:

### 🎯 **Level 1: Smart Frame Skipping**
```python
class JobManager:
    def __init__(self):
        self.last_detection_time = 0
        self.detection_interval = 1.0 / 15.0  # 15 FPS for detection
        self.frame_cache = {}
        
    def should_run_detection(self):
        current_time = time.time()
        if current_time - self.last_detection_time >= self.detection_interval:
            self.last_detection_time = current_time
            return True
        return False
```

### 🎯 **Level 2: Job Instance Pooling**
```python
class JobManager:
    def __init__(self):
        self.job_pool = {}  # Reuse job instances
        self.context_cache = {}  # Cache contexts
        
    def get_pooled_job(self, job_name):
        if job_name not in self.job_pool:
            self.job_pool[job_name] = Job(job_name)
        return self.job_pool[job_name]
```

### 🎯 **Level 3: Pipeline Parallelization**
```python
# Parallel tool execution cho independent tools
async def run_tools_parallel(self, tools, image, context):
    tasks = []
    for tool in tools:
        if tool.can_run_parallel():
            tasks.append(asyncio.create_task(tool.process_async(image, context)))
    
    results = await asyncio.gather(*tasks)
    return results
```

### 🎯 **Level 4: Memory Optimization**
```python
class Job:
    def __init__(self):
        self.image_buffer_pool = ImageBufferPool(max_size=5)
        self.result_cache = LRUCache(max_size=10)
        
    def run_optimized(self, image, context):
        # Reuse buffers
        buffer = self.image_buffer_pool.get_buffer(image.shape, image.dtype)
        # Process in-place when possible
        result = self.process_inplace(buffer, context)
        return result
```

## Implementation Priority:

1. **Smart Frame Skipping** (Easy, 50% CPU reduction)
2. **Job Instance Pooling** (Medium, 30% memory reduction) 
3. **Frame Caching** (Medium, 20% speed improvement)
4. **Pipeline Parallelization** (Hard, 40% speed improvement)

## Expected Results:
- **CPU Usage**: 60% reduction 
- **Memory**: 40% reduction
- **Latency**: 30% improvement
- **Stability**: Fewer job object conflicts