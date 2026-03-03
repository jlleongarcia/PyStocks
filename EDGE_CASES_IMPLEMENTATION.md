# Edge Cases Implementation: Symbol Disambiguation & Redirect

## Overview
Two advanced features have been implemented to handle complex real-world scenarios when users add transactions:

1. **Symbol Disambiguation** - Prioritizes US exchanges when symbols exist on multiple exchanges
2. **Symbol Redirects** - Handles ticker changes (FB → META, TWTR → X, etc.)

---

## Edge Case 1: Symbol Disambiguation

### Problem
Some stock symbols exist on multiple international exchanges:
- **INTC** - Intel on NASDAQ (US)
- **INTC.L** - Intel on London Stock Exchange
- **INTC.TO** - Intel on Toronto Stock Exchange

Users typically want the US listing, but yfinance might return any of them.

### Solution
When fetching stock data, the system now:
1. **Prefers US exchanges** (NYSE, NASDAQ) by default
2. **Strips exchange suffixes** (.L, .TO, etc.) and tries US version first
3. **Falls back** to non-US listings if US not available

### Implementation

**File**: `research/services.py`

```python
def fetch_stock_info(self, symbol: str, prefer_us_exchanges: bool = True):
    # If symbol has exchange suffix (e.g., 'INTC.L')
    if prefer_us_exchanges and '.' in symbol:
        base_symbol = symbol.split('.')[0]
        # Try US version first
        us_info = self.fetch_stock_info(base_symbol, prefer_us_exchanges=False)
        if us_info and us_info.get('exchange') in ['NMS', 'NYQ', 'NYSE', 'NASDAQ']:
            return us_info
```

### User Experience

**Scenario 1**: User enters `INTC`
```
✓ Fetches Intel from NASDAQ (US)
✓ No confusion, instant result
```

**Scenario 2**: User enters `INTC.L` (London)
```
✓ System detects exchange suffix
✓ Tries US version first (INTC)
✓ If US exists, uses it (preferred)
✓ Otherwise, uses London listing
```

### US Exchange Codes
The system recognizes these as US exchanges:
- `NMS` - NASDAQ (National Market System)
- `NYQ` - NYSE (New York Stock Exchange)
- `NYSE` - New York Stock Exchange
- `NASDAQ` - NASDAQ Stock Market

---

## Edge Case 2: Symbol Redirects (Ticker Changes)

### Problem
Companies change their ticker symbols for various reasons:
- **Rebranding**: FB → META (Facebook → Meta Platforms)
- **Acquisitions**: TWTR → X (Twitter acquired and rebranded)
- **Mergers**: ATVI → MSFT (Activision acquired by Microsoft)

Users might try to use old symbols they remember.

### Solution
A new `SymbolRedirect` model maps old symbols to current ones:

```python
class SymbolRedirect(models.Model):
    old_symbol = "FB"
    new_symbol = "META"
    reason = "Rebranded from Facebook to Meta Platforms (2021)"
    is_active = True
```

When a symbol isn't found, the system:
1. **Checks for redirects** in database
2. **Uses new symbol** if redirect exists
3. **Informs user** about the change
4. **Creates transaction** with correct symbol

### Database Model

**File**: `research/models.py`

```python
class SymbolRedirect(models.Model):
    old_symbol = CharField(max_length=10, unique=True)
    new_symbol = CharField(max_length=10)
    reason = CharField(max_length=200)  # Why it changed
    exchange_hint = CharField(max_length=50)  # For disambiguation
    is_active = BooleanField(default=True)
```

### Pre-populated Redirects

Common ticker changes are pre-loaded:

| Old Symbol | New Symbol | Reason |
|------------|------------|--------|
| FB | META | Rebranded from Facebook to Meta (2021) |
| TWTR | X | Acquired and rebranded to X Corp (2023) |
| ATVI | MSFT | Acquired by Microsoft (2023) |
| FIT | GOOG | Acquired by Google/Alphabet (2021) |
| GOOGL | GOOG | Alphabet Class A shares |
| AAPL.O | AAPL | Use AAPL for NASDAQ listing |
| MSFT.O | MSFT | Use MSFT for NASDAQ listing |
| TSLA.O | TSLA | Use TSLA for NASDAQ listing |

### User Experience

**Scenario 1**: User enters `FB` (first time)
```
1. System checks database: "FB" not found
2. Checks redirects: FB → META
3. Fetches META from Yahoo Finance
4. Saves META to database
5. Returns: "Stock FB redirected to META (Rebranded...) and added to database"
6. Transaction created with symbol: META
```

**Scenario 2**: User enters `FB` (META already in DB)
```
1. System checks database: "FB" not found
2. Checks redirects: FB → META
3. Finds META in database
4. Returns: "Symbol FB has changed to META (Rebranded...)"
5. Transaction created with symbol: META
```

**Scenario 3**: Invalid redirect
```
1. User enters: "OLDXYZ"
2. Checks database: not found
3. Checks redirects: "OLDXYZ" → "NEWXYZ"
4. Tries to fetch "NEWXYZ": not found
5. Returns: "Symbol OLDXYZ redirects to NEWXYZ, but NEWXYZ was not found"
```

---

## Implementation Details

### Flow Diagram

```
User enters symbol (e.g., "FB")
         ↓
┌────────────────────────┐
│ Check if exists in DB  │
└────────┬───────────────┘
         │ Not found
         ↓
┌────────────────────────┐
│ Check symbol redirects │
└────────┬───────────────┘
         │ Found: FB → META
         ↓
┌────────────────────────┐
│ Check if META in DB    │
└────────┬───────────────┘
         │ Not found
         ↓
┌────────────────────────┐
│ Fetch META from API    │
│ (with US preference)   │
└────────┬───────────────┘
         │ Success
         ↓
┌────────────────────────┐
│ Save META to database  │
└────────┬───────────────┘
         │
         ↓
┌────────────────────────┐
│ Create transaction     │
│ Symbol: META          │
└────────────────────────┘
```

### Files Modified

1. **research/models.py**
   - Added `SymbolRedirect` model

2. **research/admin.py**
   - Registered `SymbolRedirect` in admin panel

3. **research/services.py**
   - Enhanced `fetch_stock_info()` with US exchange preference

4. **portfolio/services.py**
   - Updated `ensure_stock_exists()` to check redirects

5. **research/management/commands/populate_symbol_redirects.py**
   - Management command to populate common redirects

---

## Management Commands

### Populate Symbol Redirects

```bash
# Add common redirects to database
docker-compose exec web python manage.py populate_symbol_redirects

# Clear and repopulate
docker-compose exec web python manage.py populate_symbol_redirects --clear
```

### Adding Custom Redirects

**Via Django Admin**:
1. Go to Admin Panel → Research → Symbol Redirects
2. Click "Add Symbol Redirect"
3. Enter old symbol, new symbol, and reason
4. Save

**Via Django Shell**:
```python
from research.models import SymbolRedirect

SymbolRedirect.objects.create(
    old_symbol='OLDTICKER',
    new_symbol='NEWTICKER',
    reason='Company rebranded in 2025',
    is_active=True
)
```

---

## Testing

### Test Symbol Redirects

```bash
docker-compose exec web python manage.py shell
```

```python
from portfolio.services import PortfolioCalculationService

# Test FB → META redirect
success, message, stock = PortfolioCalculationService.ensure_stock_exists('FB')
print(message)  # "Symbol FB has changed to META (Rebranded...)"
print(stock.symbol)  # "META"
```

### Test Exchange Disambiguation

```python
# Test US exchange preference
success, message, stock = PortfolioCalculationService.ensure_stock_exists('INTC')
print(stock.exchange)  # "NMS" (NASDAQ)
```

---

## User Messages

The system provides clear messages for different scenarios:

### Success Messages
- **Stock exists**: `"Stock AAPL found in database"`
- **Stock auto-fetched**: `"Stock NVDA added to database"`
- **Redirect (first time)**: `"Stock FB redirected to META (Rebranded...) and added to database"`
- **Redirect (exists)**: `"Symbol FB has changed to META (Rebranded...)"`

### Error Messages
- **Invalid symbol**: `"Stock symbol 'INVALIDXYZ' not found. Please verify..."`
- **Invalid redirect**: `"Symbol FB redirects to META, but META was not found..."`
- **API error**: `"Error fetching stock 'AAPL': [error details]"`

---

## Admin Panel Features

### Symbol Redirects Admin
- **List view**: Shows all redirects with status
- **Filters**: Active/Inactive, Exchange hint, Created date
- **Search**: By old symbol, new symbol, or reason
- **Bulk actions**: Activate/deactivate multiple redirects

### Managing Redirects
- Mark redirects as inactive when no longer needed
- Add exchange hints for disambiguation
- Edit reasons for clarity

---

## Production Considerations

### Performance
- ✅ **Fast path**: Database lookup (microseconds)
- ⚠️ **Slow path**: API fetch (1-2 seconds for new stocks)
- ✅ **Redirect check**: Database query (fast)

### Scalability
- Redirects are indexed for fast lookup
- No API calls needed if redirect target exists
- Caching opportunities for future enhancement

### Maintenance
- Review and update redirects annually
- Add new redirects as they occur
- Deactivate outdated redirects instead of deleting

### Monitoring
- All redirects are logged
- Failed fetches are logged with details
- API errors are caught and reported

---

## Future Enhancements

### Potential Improvements
1. **Auto-detect redirects**: Use Yahoo Finance's redirect responses
2. **Reverse lookup**: Find all old symbols for current one
3. **Bulk import**: Import redirects from external sources
4. **Notification**: Alert users when symbol changes
5. **Suggestion system**: "Did you mean META?" for FB

### Planned Features
- Historical symbol tracking
- Multiple redirect chains (A → B → C)
- Confidence scoring for redirects
- User-submitted redirect suggestions

---

## Examples in Action

### Example 1: Legacy Facebook Stock

**User Action**: Enters "FB" in transaction form

**System Response**:
1. Checks DB: "FB" not found
2. Finds redirect: FB → META
3. Checks DB: "META" found
4. Message: "*Symbol FB has changed to META (Rebranded from Facebook to Meta Platforms (2021))*"
5. Transaction created with: **META**

### Example 2: International Intel Stock

**User Action**: Enters "INTC.L" (London)

**System Response**:
1. Detects exchange suffix: ".L"
2. Tries US version: "INTC"
3. Fetches INTC from NASDAQ
4. Saves with exchange: "NMS"
5. Transaction created with: **INTC**

### Example 3: Acquired Company

**User Action**: Enters "ATVI" (Activision, acquired by Microsoft)

**System Response**:
1. Checks DB: "ATVI" not found
2. Finds redirect: ATVI → MSFT
3. Checks DB: "MSFT" found
4. Message: "*Symbol ATVI has changed to MSFT (Acquired by Microsoft (2023))*"
5. Transaction created with: **MSFT**

---

## Troubleshooting

### Redirect Not Working
1. Check if redirect exists: Admin → Symbol Redirects
2. Verify `is_active = True`
3. Check logs for error messages

### Wrong Exchange
1. Verify symbol doesn't have suffix (.L, .TO, etc.)
2. Check `exchange` field in Stock model
3. Update redirect with `exchange_hint` if needed

### Symbol Not Found After Redirect
1. Verify new symbol is valid on Yahoo Finance
2. Check if new symbol needs its own redirect
3. Review error logs for API issues

---

## Conclusion

These edge case implementations make the system:
- ✅ **More user-friendly**: Users can use old symbols they remember
- ✅ **Smarter**: Prioritizes correct exchanges automatically  
- ✅ **More robust**: Handles real-world ticker changes gracefully
- ✅ **Production-ready**: Comprehensive error handling and logging

The system now handles complex scenarios that would confuse users in other portfolio trackers!
