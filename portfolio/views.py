"""
Portfolio API Views
Comprehensive views for portfolio management with financial metrics integration
"""
import logging
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from datetime import datetime, date as date_type

from research.services import PriceCacheService
from .models import Portfolio, Transaction, Position, Dividend
from .serializers import (
    PortfolioSerializer, PortfolioSummarySerializer, TransactionSerializer,
    PositionSerializer, PositionDetailSerializer, DividendSerializer,
    BrokerSummarySerializer, DividendIncomeHistorySerializer
)
from .services import FXLotService, FXRateService, PortfolioCalculationService

logger = logging.getLogger(__name__)


class PortfolioListCreateView(APIView):
    """List and create portfolios"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all portfolios for authenticated user"""
        portfolios = Portfolio.objects.filter(user=request.user)
        serializer = PortfolioSerializer(portfolios, many=True)
        return Response({
            'count': portfolios.count(),
            'portfolios': serializer.data
        })
    
    def post(self, request):
        """Create new portfolio"""
        serializer = PortfolioSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PortfolioDetailView(APIView):
    """Get, update, delete portfolio"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Get portfolio details"""
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        serializer = PortfolioSerializer(portfolio)
        return Response(serializer.data)
    
    def put(self, request, pk):
        """Update portfolio"""
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        serializer = PortfolioSerializer(portfolio, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """Delete portfolio"""
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        portfolio.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PortfolioSummaryView(APIView):
    """Get comprehensive portfolio summary with all metrics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Get portfolio summary including positions and calculated metrics"""
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        summary = PortfolioCalculationService.calculate_portfolio_summary(portfolio)
        serializer = PortfolioSummarySerializer(summary)
        return Response(serializer.data)


class PortfolioPositionsView(APIView):
    """Get portfolio positions"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Get all positions for a portfolio"""
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        positions = portfolio.positions.all()
        serializer = PositionSerializer(positions, many=True)
        return Response({
            'count': positions.count(),
            'positions': serializer.data
        })


class PositionDetailView(APIView):
    """Get detailed position information with metrics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, portfolio_id, symbol):
        """Get position details including financial metrics"""
        portfolio = get_object_or_404(Portfolio, pk=portfolio_id, user=request.user)
        position = get_object_or_404(Position, portfolio=portfolio, symbol=symbol.upper())
        
        # Get detailed position data with metrics
        position_data = PortfolioCalculationService.get_position_detail(position)
        
        # Get transaction history for this position
        transactions = position.get_transactions()
        transaction_serializer = TransactionSerializer(transactions, many=True)
        
        # Combine data
        response_data = {
            'position': position_data,
            'transactions': transaction_serializer.data,
            'transactions_count': transactions.count()
        }
        
        return Response(response_data)


class PortfolioTransactionsView(APIView):
    """Get and create portfolio transactions"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Get all transactions for a portfolio"""
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        transactions = portfolio.transactions.all()
        serializer = TransactionSerializer(transactions, many=True)
        return Response({
            'count': transactions.count(),
            'transactions': serializer.data
        })
    
    def post(self, request, pk):
        """Create new transaction for a portfolio"""
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        
        # Validate and ensure stock exists
        symbol = request.data.get('symbol', '').strip().upper()
        if not symbol:
            return Response(
                {'error': 'Stock symbol is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, message, stock = PortfolioCalculationService.ensure_stock_exists(symbol)
        if not success:
            return Response(
                {'error': message, 'symbol': symbol},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add portfolio to request data
        data = request.data.copy()
        data['portfolio'] = portfolio.id
        data['symbol'] = symbol  # Use validated uppercase symbol
        
        serializer = TransactionSerializer(data=data)
        if serializer.is_valid():
            transaction = serializer.save()
            
            # Update position based on transaction
            PortfolioCalculationService.update_position_from_transaction(transaction)
            
            # Fetch and store buy yield if applicable
            if transaction.transaction_type == 'BUY':
                PortfolioCalculationService.fetch_and_store_buy_yield(transaction)
            
            # Include redirect URL in response
            response_data = serializer.data
            response_data['redirect_url'] = f'/portfolio/{portfolio.id}/'
            response_data['portfolio_id'] = portfolio.id
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TransactionCreateView(APIView):
    """Create transaction (legacy endpoint)"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Create transaction"""
        # Verify user owns the portfolio
        portfolio_id = request.data.get('portfolio')
        portfolio = None
        if portfolio_id:
            portfolio = get_object_or_404(Portfolio, pk=portfolio_id, user=request.user)
        
        # Validate and ensure stock exists
        symbol = request.data.get('symbol', '').strip().upper()
        if not symbol:
            return Response(
                {'error': 'Stock symbol is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, message, stock = PortfolioCalculationService.ensure_stock_exists(symbol)
        if not success:
            return Response(
                {'error': message, 'symbol': symbol},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update request data with validated symbol
        data = request.data.copy()
        data['symbol'] = symbol
        
        serializer = TransactionSerializer(data=data)
        if serializer.is_valid():
            transaction = serializer.save()
            
            # Update position based on transaction
            PortfolioCalculationService.update_position_from_transaction(transaction)
            
            # Fetch and store buy yield if applicable
            if transaction.transaction_type == 'BUY':
                PortfolioCalculationService.fetch_and_store_buy_yield(transaction)
            
            # Include redirect URL in response if portfolio is known
            response_data = serializer.data
            if portfolio:
                response_data['redirect_url'] = f'/portfolio/{portfolio.id}/'
                response_data['portfolio_id'] = portfolio.id
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DividendListView(APIView):
    """List and create dividends"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all dividends for user's portfolios"""
        portfolios = Portfolio.objects.filter(user=request.user)
        dividends = Dividend.objects.filter(portfolio__in=portfolios)
        
        # Filter by portfolio if specified
        portfolio_id = request.query_params.get('portfolio')
        if portfolio_id:
            dividends = dividends.filter(portfolio_id=portfolio_id)
        
        # Filter by year if specified
        year = request.query_params.get('year')
        if year:
            dividends = dividends.filter(payment_date__year=year)
        
        serializer = DividendSerializer(dividends, many=True)
        return Response({
            'count': dividends.count(),
            'dividends': serializer.data
        })
    
    def post(self, request):
        """Create new dividend record"""
        # Verify user owns the portfolio
        portfolio_id = request.data.get('portfolio')
        if portfolio_id:
            get_object_or_404(Portfolio, pk=portfolio_id, user=request.user)
        
        serializer = DividendSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DividendIncomeHistoryView(APIView):
    """Get dividend income history for a portfolio"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Get dividend income history"""
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        
        # Get year from query params (default to current year)
        year = request.query_params.get('year', datetime.now().year)
        try:
            year = int(year)
        except ValueError:
            year = datetime.now().year
        
        history = PortfolioCalculationService.calculate_dividend_income_history(portfolio, year)
        serializer = DividendIncomeHistorySerializer(history)
        return Response(serializer.data)


class BrokerSummaryView(APIView):
    """Get portfolio breakdown by broker"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Get broker summary for a portfolio"""
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        broker_summary = PortfolioCalculationService.calculate_broker_summary(portfolio)
        serializer = BrokerSummarySerializer(broker_summary, many=True)
        return Response({
            'count': len(broker_summary),
            'brokers': serializer.data
        })


# ============================================================================
# Frontend Template Views
# ============================================================================

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages


@login_required
def portfolio_list_view(request):
    """Frontend view: List all portfolios"""
    from research.services import PriceCacheService

    portfolios = list(Portfolio.objects.filter(user=request.user).prefetch_related('positions'))

    # Single batch price lookup for every symbol across all portfolios
    all_symbols = list({pos.symbol for p in portfolios for pos in p.positions.all()})
    price_data = PriceCacheService.get_prices(all_symbols) if all_symbols else {}

    for portfolio in portfolios:
        positions = list(portfolio.positions.all())
        portfolio.positions_count = len(positions)

        total_invested = sum(float(pos.total_cost) for pos in positions)
        current_value = sum(
            (price_data[pos.symbol]['price'] if pos.symbol in price_data
             else (float(pos.current_price) if pos.current_price else float(pos.average_cost)))
            * float(pos.quantity)
            for pos in positions
        )
        gain_loss = current_value - total_invested
        portfolio.live_total_value      = round(current_value, 2)
        portfolio.live_total_invested   = round(total_invested, 2)
        portfolio.live_total_return     = round(gain_loss, 2)
        portfolio.live_return_pct       = round(gain_loss / total_invested * 100, 2) if total_invested else 0

    return render(request, 'portfolio/portfolio_list.html', {
        'portfolios': portfolios
    })


@login_required
def portfolio_detail_view(request, pk):
    """Frontend view: Portfolio detail with summary"""
    portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)

    summary = PortfolioCalculationService.calculate_portfolio_summary(portfolio)

    # Build unified chronological ledger (transactions + dividend receipts)
    position_avg = {p['symbol']: p['average_cost'] for p in summary['positions']}
    ledger = []

    for tx in portfolio.transactions.order_by('-transaction_date'):
        qty = float(tx.quantity)
        price = float(tx.price)
        commission = float(tx.commission)
        tx_date = tx.transaction_date.date() if hasattr(tx.transaction_date, 'date') else tx.transaction_date

        if tx.transaction_type == 'BUY':
            ledger.append({
                'date': tx_date, 'type': 'buy', 'label': 'Buy',
                'symbol': tx.symbol,
                'price': price, 'quantity': qty,
                'commission': commission,
                'total': price * qty + commission,
                'extra': f"{float(tx.buy_yield):.2f}%" if tx.buy_yield else None,
                'extra_class': 'positive',
            })
        elif tx.transaction_type == 'SELL':
            avg = position_avg.get(tx.symbol)
            pnl = round((price - avg) * qty - commission, 2) if avg else None
            ledger.append({
                'date': tx_date, 'type': 'sell', 'label': 'Sell',
                'symbol': tx.symbol,
                'price': price, 'quantity': qty,
                'commission': commission,
                'total': price * qty - commission,
                'extra': f"${pnl:+,.2f}" if pnl is not None else None,
                'extra_class': 'positive' if (pnl or 0) >= 0 else 'negative',
            })
        elif tx.transaction_type == 'DIV':
            ledger.append({
                'date': tx_date, 'type': 'div', 'label': 'Dividend',
                'symbol': tx.symbol,
                'price': price, 'quantity': qty,
                'commission': commission,
                'total': price * qty - commission,
                'extra': None, 'extra_class': None,
            })
        elif tx.transaction_type == 'SPOF':
            ledger.append({
                'date': tx_date, 'type': 'spof', 'label': 'Spin-Off',
                'symbol': tx.symbol,
                'price': price, 'quantity': qty,
                'commission': 0, 'total': price * qty,
                'extra': None, 'extra_class': None,
            })
        elif tx.transaction_type == 'INT':
            ledger.append({
                'date': tx_date, 'type': 'int', 'label': 'Interest',
                'symbol': tx.symbol or '—',
                'price': None, 'quantity': None,
                'commission': 0, 'total': price,
                'extra': None, 'extra_class': None,
            })
        elif tx.transaction_type == 'DEP':
            ledger.append({
                'date': tx_date, 'type': 'dep', 'label': 'Deposit',
                'symbol': tx.symbol or '—',
                'price': None, 'quantity': None,
                'commission': 0, 'total': price,
                'extra': None, 'extra_class': None,
            })
        elif tx.transaction_type == 'WIT':
            ledger.append({
                'date': tx_date, 'type': 'wit', 'label': 'Withdrawal',
                'symbol': tx.symbol or '—',
                'price': None, 'quantity': None,
                'commission': 0, 'total': price,
                'extra': None, 'extra_class': None,
            })
        elif tx.transaction_type == 'EXC':
            ledger.append({
                'date': tx_date, 'type': 'exc', 'label': 'Exchange',
                'symbol': tx.symbol or '—',
                'price': price, 'quantity': qty,
                'commission': commission, 'total': price * qty,
                'extra': None, 'extra_class': None,
            })

    for div in portfolio.dividends.all():
        effective_date = div.payment_date or div.ex_dividend_date
        qty = float(div.quantity) if div.quantity else None
        div_per_share = round(float(div.amount) / qty, 4) if qty else None
        ledger.append({
            'date': effective_date, 'type': 'div', 'label': 'Dividend',
            'symbol': div.symbol,
            'price': div_per_share, 'quantity': qty,
            'commission': 0, 'total': float(div.amount),
            'extra': None, 'extra_class': None,
        })

    ledger.sort(key=lambda x: x['date'] or date_type.min, reverse=True)

    return render(request, 'portfolio/portfolio_detail.html', {
        'portfolio': portfolio,
        'summary': summary,
        'ledger': ledger,
    })


@login_required
@require_http_methods(["GET", "POST"])
def portfolio_create_view(request):
    """Frontend view: Create new portfolio"""
    from .models import CURRENCY_CHOICES
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        is_active = request.POST.get('is_active') == 'on'
        native_currency = request.POST.get('native_currency', 'EUR')

        if name:
            portfolio = Portfolio.objects.create(
                user=request.user,
                name=name,
                description=description,
                is_active=is_active,
                native_currency=native_currency,
            )
            messages.success(request, f'Portfolio "{portfolio.name}" created successfully!')
            return redirect('portfolio:portfolio_detail_view', pk=portfolio.id)
        else:
            messages.error(request, 'Portfolio name is required.')

    return render(request, 'portfolio/portfolio_form.html', {
        'portfolio': None,
        'currency_choices': CURRENCY_CHOICES,
    })


@login_required
@require_http_methods(["GET", "POST"])
def portfolio_edit_view(request, pk):
    """Frontend view: Edit portfolio"""
    from .models import CURRENCY_CHOICES
    portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)

    if request.method == 'POST':
        portfolio.name = request.POST.get('name', portfolio.name)
        portfolio.description = request.POST.get('description', '')
        portfolio.is_active = request.POST.get('is_active') == 'on'
        portfolio.native_currency = request.POST.get('native_currency', portfolio.native_currency)
        portfolio.save()

        messages.success(request, f'Portfolio "{portfolio.name}" updated successfully!')
        return redirect('portfolio:portfolio_detail_view', pk=portfolio.id)

    return render(request, 'portfolio/portfolio_form.html', {
        'portfolio': portfolio,
        'currency_choices': CURRENCY_CHOICES,
    })


@login_required
@require_http_methods(["GET", "POST"])
def transaction_create_view(request, portfolio_id):
    """Frontend view: Add transaction to portfolio"""
    portfolio = get_object_or_404(Portfolio, pk=portfolio_id, user=request.user)

    CASH_TYPES  = {'INT', 'DEP', 'WIT'}
    STOCK_TYPES = {'BUY', 'SELL', 'DIV', 'SPOF'}
    # Types that need FX processing (all except DEP / WIT)
    FX_TYPES    = {'BUY', 'SELL', 'DIV', 'INT', 'EXC'}

    if request.method == 'POST':
        try:
            tx_type = request.POST.get('transaction_type', '').upper()
            symbol  = request.POST.get('symbol', '').strip().upper()

            if tx_type in STOCK_TYPES:
                if not symbol:
                    messages.error(request, 'Stock symbol is required.')
                    return render(request, 'portfolio/transaction_form.html', {
                        'portfolio': portfolio,
                        'today': datetime.now().strftime('%Y-%m-%d')
                    })
                success, message, stock = PortfolioCalculationService.ensure_stock_exists(symbol)
                if not success:
                    messages.error(request, message)
                    return render(request, 'portfolio/transaction_form.html', {
                        'portfolio': portfolio,
                        'today': datetime.now().strftime('%Y-%m-%d')
                    })
                resolved_symbol = stock.symbol
                stock_currency = stock.currency or 'USD'
            else:
                resolved_symbol = symbol
                stock_currency = ''

            commission_value = request.POST.get('commission', '').strip() or '0'
            quantity_raw     = request.POST.get('quantity', '').strip()
            quantity_value   = Decimal(quantity_raw) if quantity_raw else Decimal('1')
            tx_date_str      = request.POST.get('transaction_date', '')

            # ── EXC-specific fields ──────────────────────────────────────────
            from_currency      = request.POST.get('from_currency', '').strip().upper()
            from_amount_raw    = request.POST.get('from_amount', '').strip()
            to_currency        = request.POST.get('to_currency', '').strip().upper()
            to_amount_raw      = request.POST.get('to_amount', '').strip()
            commission_cur     = request.POST.get('commission_currency', '').strip().upper()

            from_amount = Decimal(from_amount_raw) if from_amount_raw else None
            to_amount   = Decimal(to_amount_raw)   if to_amount_raw   else None

            # ── Resolve transaction currency ─────────────────────────────────
            if tx_type == 'EXC':
                tx_currency = to_currency or from_currency
            elif tx_type in STOCK_TYPES:
                tx_currency = stock_currency
            else:
                # INT: user may specify via symbol field or leave blank
                tx_currency = request.POST.get('transaction_currency', '').strip().upper() or portfolio.native_currency

            # ── FX rate resolution ───────────────────────────────────────────
            manual_fx  = request.POST.get('fx_rate', '').strip()
            fx_rate    = None
            fx_source  = ''
            native_amt = None

            if tx_type in FX_TYPES and tx_currency and tx_currency != portfolio.native_currency:
                tx_date_obj = datetime.strptime(tx_date_str, '%Y-%m-%d').date() if tx_date_str else date_type.today()

                if tx_type == 'EXC' and from_amount and to_amount:
                    # Derive rate directly from the user's own amounts
                    # 1 to_currency = (from_amount / to_amount) native
                    native_cur = portfolio.native_currency
                    if from_currency == native_cur:
                        fx_rate   = from_amount / to_amount
                        fx_source = 'computed'
                    elif to_currency == native_cur:
                        fx_rate   = to_amount / from_amount
                        fx_source = 'computed'
                    else:
                        # Neither side is native — fetch from Frankfurter
                        fx_rate, fx_source = FXRateService.get_rate(tx_currency, portfolio.native_currency, tx_date_obj)
                    native_amt = from_amount  # what was paid in native (or closest proxy)
                elif manual_fx:
                    fx_rate   = Decimal(manual_fx)
                    fx_source = 'manual'
                else:
                    fx_rate, fx_source = FXRateService.get_rate(tx_currency, portfolio.native_currency, tx_date_obj)

                if fx_rate and tx_type != 'EXC':
                    price_val = Decimal(request.POST.get('price', '0') or '0')
                    total_in_stock_cur = quantity_value * price_val
                    if tx_type == 'BUY':
                        total_in_stock_cur += Decimal(commission_value)
                    else:
                        total_in_stock_cur -= Decimal(commission_value)
                    native_amt = total_in_stock_cur * fx_rate

                if fx_source == 'unavailable':
                    messages.warning(
                        request,
                        f"No FX rate found for {tx_currency}/{portfolio.native_currency} around "
                        f"{tx_date_str}. Please enter it manually in the FX Rate field and resubmit."
                    )
                    return render(request, 'portfolio/transaction_form.html', {
                        'portfolio': portfolio,
                        'today': datetime.now().strftime('%Y-%m-%d'),
                        'fx_warning': True,
                        'post': request.POST,
                    })

            transaction = Transaction.objects.create(
                portfolio=portfolio,
                symbol=resolved_symbol,
                transaction_type=tx_type,
                quantity=quantity_value,
                price=Decimal(request.POST.get('price', '0') or '0'),
                commission=Decimal(commission_value),
                transaction_date=tx_date_str,
                broker=request.POST.get('broker', ''),
                notes=request.POST.get('notes', ''),
                # FX fields
                transaction_currency=tx_currency,
                fx_rate=fx_rate,
                native_amount=native_amt,
                fx_rate_source=fx_source,
                # EXC-only
                from_currency=from_currency,
                from_amount=from_amount,
                to_currency=to_currency,
                to_amount=to_amount,
                commission_currency=commission_cur,
            )

            if tx_type in STOCK_TYPES:
                PortfolioCalculationService.update_position_from_transaction(transaction)

            if transaction.transaction_type == 'BUY':
                PortfolioCalculationService.fetch_and_store_buy_yield(transaction)

            # Process FX lots
            if tx_type in FX_TYPES:
                try:
                    FXLotService.process_transaction(transaction)
                except Exception as fx_err:
                    logger.warning("FX lot processing failed for tx %s: %s", transaction.id, fx_err)

            from datetime import date as _date
            from django.core.cache import cache as _cache
            _today = _date.today().isoformat()
            _cache.delete(f"price_range_{portfolio.id}_{_today}")
            if transaction.symbol:
                PriceCacheService.invalidate(transaction.symbol)

            messages.success(request, f'Transaction recorded successfully!')
            return redirect('portfolio:portfolio_detail_view', pk=portfolio.id)

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"ERROR in transaction_create_view: {error_details}")
            messages.error(request, f'Error adding transaction: {str(e)}')

    return render(request, 'portfolio/transaction_form.html', {
        'portfolio': portfolio,
        'today': datetime.now().strftime('%Y-%m-%d'),
    })


@login_required
@require_http_methods(["POST"])
def portfolio_sync_dividends(request, pk):
    """Refresh research dividend data from yfinance, then auto-record qualifying payments."""
    portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
    result = PortfolioCalculationService.auto_record_dividends(portfolio)
    if result['created'] > 0:
        messages.success(request, f"{result['created']} dividend payment(s) recorded automatically.")
    else:
        messages.info(request, "No new dividends to record — everything is already up to date.")
    if result.get('refresh_errors'):
        messages.warning(
            request,
            f"Could not refresh data for: {', '.join(result['refresh_errors'])}. "
            "Those symbols may show stale dividends."
        )
    return redirect('portfolio:portfolio_detail_view', pk=pk)


@login_required
@require_http_methods(["POST"])
def portfolio_delete_view(request, pk):
    """Delete a portfolio and all its data after user confirmation."""
    portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
    name = portfolio.name
    portfolio.delete()
    messages.success(request, f'Portfolio "{name}" has been deleted.')
    return redirect('portfolio:portfolio_list_view')


@login_required
def position_detail_view(request, portfolio_id, symbol):
    """Frontend view: Position detail with transactions"""
    portfolio = get_object_or_404(Portfolio, pk=portfolio_id, user=request.user)
    position = get_object_or_404(Position, portfolio=portfolio, symbol=symbol.upper())

    position_data = PortfolioCalculationService.get_position_detail(position)
    transactions = position.get_transactions()

    return render(request, 'portfolio/position_detail.html', {
        'portfolio': portfolio,
        'position': position_data,
        'transactions': transactions
    })


@login_required
def tax_report_view(request, pk):
    """Frontend view: Annual tax report — stock P&L + FX P&L in native currency."""
    from .services import TaxReportService
    portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)

    available_years = TaxReportService.available_years(portfolio)
    current_year = date_type.today().year
    if not available_years:
        available_years = [current_year]

    try:
        year = int(request.GET.get('year', available_years[0]))
    except (ValueError, IndexError):
        year = current_year

    report = TaxReportService.calculate(portfolio, year)

    return render(request, 'portfolio/tax_report.html', {
        'portfolio': portfolio,
        'report': report,
        'available_years': available_years,
        'selected_year': year,
    })
