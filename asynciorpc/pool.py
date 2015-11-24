from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from asynciorpc.config import CONFIG

# use threadpool for IO-intensive job
tpool = ThreadPoolExecutor(max_workers=CONFIG['threadpool_size'])

# use threadpool for CPU-intensive job
ppool = ProcessPoolExecutor(max_workers=CONFIG['processpool_size'])