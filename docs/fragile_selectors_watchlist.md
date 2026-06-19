# Fragile Selectors Watchlist  
*Last Reviewed: 2025-09-25*

## High-Risk Elements

### 1. Score/Result Containers
**Example:**  
```xpath
//div[@class='score']
//div[contains(@class, 'scoreCell')]
```
**Why fragile:** Flashscore frequently renames or restructures score-related containers, sometimes nesting them deeper.

### 2. Team Names
**Example:**  
```xpath
//div[@class='participantName']
//div[contains(@class,'team')]
```
**Why fragile:** Classes like `participantName`, `teamName` get obfuscated or swapped.

### 3. Tabs (Main & Sub-tabs)
**Example:**  
```xpath
//div[@class='tabs']//a[text()='Summary']
```
**Why fragile:** Tab navigation is very dynamic, labels change (Summary → Overview), and sometimes tabs are rendered as `<button>` instead of `<a>`.

### 4. Match Event Rows
*(Goals, Fouls, Substitutions, etc.)*  
**Example:**  
```xpath
//div[contains(@class,'eventRow')]
```
**Why fragile:** Events are deeply nested and rely on obfuscated class names that get regenerated often.

### 5. Odds/Betting Markets
**Example:**  
```xpath
//div[contains(@class,'oddsCell')]
```
**Why fragile:** Betting sections are among the most volatile parts of the DOM; they change structure and class names frequently.

### 6. Date & Time Containers
**Example:**  
```xpath
//div[contains(@class,'startTime')]
```
**Why fragile:** Sometimes replaced with `<span>` or moved into a different parent container.

---

## Warning Signs of Breaking Selectors

- ❌ Empty values (element not found)
- ⏱️ Timeout while waiting for a supposedly "crucial" element
- 🔄 Wrong data captured (shifted cells)

---

## Watch Strategy

1. **Priority Monitoring**
   - Always monitor tab navigation and team/score blocks first — they break most often

2. **Robust Selection**
   - Use `contains(@class, ...)` or `normalize-space(text())` instead of hard class matches where possible
   - Prefer data attributes over class names when available
   - Use relative paths instead of absolute ones

3. **Monitoring**
   - Keep an internal log of last working timestamp for each locator
   - Set up alerts for selector failures
   - Regularly review and update selectors as part of maintenance

4. **Defensive Coding**
   - Implement fallback selectors for critical elements
   - Add validation checks for scraped data
   - Use try-catch blocks with meaningful error messages
