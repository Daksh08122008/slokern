## 2026-10-26 - Optimize visibleExperiments filtering
**Learning:** In React applications rendering lists that depend on text search filtering, computing the filter derived state on every render can cause performance issues, especially when constructing strings `${record.id} ${record.run} ${record.work} ${record.model}` inside the filter callback.
**Action:** Memoize the visible array using `useMemo`.
