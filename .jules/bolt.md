
## 2026-10-24 - [Fix blocking network I/O in async serving adapter]
**Learning:** `asyncio.to_thread(next, iterator)` raises a `StopIteration` exception when the iterator exhausts. Because `asyncio.to_thread` runs in a thread executor, Python correctly forbids bubbling `StopIteration` directly into a `Future`, resulting in a `RuntimeError: StopIteration interacts badly with generators and cannot be raised into a Future`.
**Action:** When wrapping a synchronous generator in an async generator via `to_thread`, avoid relying on `StopIteration`. Instead, pass a sentinel object to `next(iterator, sentinel)` and break the async loop when the sentinel is returned.
## 2026-10-26 - Optimize visibleExperiments filtering
**Learning:** In React applications rendering lists that depend on text search filtering, computing the filter derived state on every render can cause performance issues, especially when constructing strings `${record.id} ${record.run} ${record.work} ${record.model}` inside the filter callback.
**Action:** Memoize the visible array using `useMemo`.
## 2026-10-27 - [Optimize visibleExperiments filtering in React]
**Learning:** Even within memoized React hooks, O(N) string building operations (like concatenating record fields to search them) inside `.filter()` callbacks can cause noticeable lag on large lists. If there are other O(1) checks (like checking an enum status), they should always be evaluated first to short-circuit the expensive work.
**Action:** Order boolean conditions in filters from cheapest to most expensive, and lift invariants (like `.toLowerCase()` on the search term) out of the iteration loop entirely.
