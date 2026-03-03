# Auto-Fetch Stock Feature

## Overview
When adding a transaction, the system now automatically fetches and adds stocks to the database if they don't already exist. This eliminates the need for users to manually add stocks to the Research API before creating transactions.

## How It Works

### User Experience
1. **User adds transaction** with a stock symbol (e.g., "NVDA")
2. **System checks** if stock exists in database
3. **If not found**: Automatically fetches from Yahoo Finance and adds to database
4. **If found**: Uses existing data
5. **If invalid**: Shows friendly error message

### Technical Flow
```python
# Called before creating transaction
success, message, stock = PortfolioCalculationService.ensure_stock_exists(symbol)

if not success:
    # Show error to user
    return error_response(message)

# Continue with transaction creation
```

## Scenarios Handled

### ✅ Scenario 1: Stock Exists in Database
**Example**: AAPL (already in database)
- **Action**: Uses existing stock data
- **Response**: Transaction created immediately
- **User sees**: Success message

### ✅ Scenario 2: Valid Stock Not in Database
**Example**: PLTR (not in database but exists on Yahoo Finance)
- **Action**: Automatically fetches from Yahoo Finance and saves
- **Response**: Stock added, transaction created
- **User sees**: Success message (seamless experience)
- **Logged**: "Stock PLTR added to database"

### ✅ Scenario 3: Invalid Stock Symbol
**Example**: INVALIDXYZ123
- **Action**: Attempts to fetch, fails
- **Response**: Transaction rejected
- **User sees**: "Stock symbol 'INVALIDXYZ123' not found. Please verify the symbol is correct."

### ⚠️ Scenario 4: Network/API Errors
**Example**: Yahoo Finance API is down
- **Action**: Catches exception
- **Response**: Transaction rejected
- **User sees**: "Error fetching stock 'SYMBOL': [error details]"

### ⚠️ Scenario 5: Rate Limiting
**Example**: Too many requests to Yahoo Finance
- **Action**: Exception caught
- **Response**: Transaction rejected
- **User sees**: Error message with details

### ✅ Scenario 6: Concurrent Requests
**Example**: Two users add same stock simultaneously
- **Action**: Django's `get_or_create` handles with database lock
- **Response**: One creates, one uses existing
- **User sees**: Both succeed

### ✅ Scenario 7: Case Insensitivity
**Example**: User types "aapl" instead of "AAPL"
- **Action**: Automatically converts to uppercase
- **Response**: Finds/creates with correct symbol
- **User sees**: Works seamlessly

## Implementation Details

### Files Modified

1. **portfolio/services.py**
   - Added `ensure_stock_exists()` method
   - Checks database first (fast path)
   - Falls back to Yahoo Finance API (slow path)

2. **portfolio/views.py**
   - Frontend form: `transaction_create_view()`
   - API endpoint: `PortfolioTransactionsView.post()`
   - Legacy API: `TransactionCreateView.post()`
   - All validate stock before creating transaction

### What Gets Fetched

When auto-fetching, the system retrieves:
- ✅ Symbol (e.g., "NVDA")
- ✅ Company name (e.g., "NVIDIA Corporation")
- ✅ Sector (e.g., "Technology")
- ✅ Industry (e.g., "Semiconductors")
- ✅ Exchange (e.g., "NMS")
- ✅ Currency (e.g., "USD")
- ✅ Country (e.g., "United States")

**Note**: Only basic stock info is fetched (fast). Historical prices, dividends, and financial metrics are NOT fetched automatically to keep transactions fast.

## User Experience Examples

### Success Case (New Stock)
```
User enters: PLTR, 100 shares @ $25.50
System: [Silently fetches PLTR from Yahoo Finance]
User sees: "Transaction for PLTR added successfully!"
```

### Error Case (Invalid Symbol)
```
User enters: FAKEXYZ, 100 shares @ $25.50
System: [Attempts fetch, fails]
User sees: "Stock symbol 'FAKEXYZ' not found. Please verify the symbol is correct."
```

### Success Case (Existing Stock)
```
User enters: AAPL, 10 shares @ $175.00
System: [Finds AAPL in database instantly]
User sees: "Transaction for AAPL added successfully!"
```

## Testing

Tested scenarios:
- ✅ Stock exists in database (AAPL)
- ✅ Stock doesn't exist but valid (PLTR, RBLX)
- ✅ Invalid stock symbol (INVALIDXYZ123)
- ✅ End-to-end transaction creation
- ✅ Position updates
- ✅ Buy yield fetching

## Future Enhancements

Potential improvements:
1. **Background fetching**: Queue historical data fetch for background processing
2. **Caching**: Cache validation results for common symbols
3. **Bulk validation**: Validate multiple symbols at once
4. **Auto-update**: Periodically refresh stock data for active holdings
5. **Symbol suggestions**: Show similar symbols if exact match fails

## Maintenance Notes

- **Performance**: First transaction for a new stock takes 1-2 seconds (API call)
- **Subsequent transactions**: Instant (database lookup)
- **Error handling**: All errors are caught and user-friendly
- **Logging**: All fetch attempts are logged for debugging
- **Production ready**: Safe for commercial use
