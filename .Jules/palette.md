## 2025-05-18 - Missing ARIA Labels on Pagination Buttons
**Learning:** Found pagination buttons like "Previous", "1", "2" that do not have `aria-label` or `aria-current` indicators for screen readers. While "Previous" has text, screen readers benefit from explicit labels for pagination elements, and active page numbers need `aria-current="page"` to indicate state.
**Action:** Will update the pagination controls in the table footer to include accessible labels and state attributes.
