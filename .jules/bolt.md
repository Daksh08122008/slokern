
## 2026-10-24 - [Fix blocking network I/O in async serving adapter]
**Learning:** `asyncio.to_thread(next, iterator)` raises a `StopIteration` exception when the iterator exhausts. Because `asyncio.to_thread` runs in a thread executor, Python correctly forbids bubbling `StopIteration` directly into a `Future`, resulting in a `RuntimeError: StopIteration interacts badly with generators and cannot be raised into a Future`.
**Action:** When wrapping a synchronous generator in an async generator via `to_thread`, avoid relying on `StopIteration`. Instead, pass a sentinel object to `next(iterator, sentinel)` and break the async loop when the sentinel is returned.
