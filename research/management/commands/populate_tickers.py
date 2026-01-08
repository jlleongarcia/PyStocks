"""
Management command to populate the database with all available stock tickers.
Uses get-all-tickers library to get comprehensive list of US stocks.
"""
from django.core.management.base import BaseCommand
from research.models import Stock
from get_all_tickers.get_tickers import get_tickers


class Command(BaseCommand):
    help = 'Populate database with all available stock tickers from US exchanges'

    def add_arguments(self, parser):
        parser.add_argument(
            '--exchange',
            type=str,
            default='ALL',
            help='Filter by exchange: NYSE, NASDAQ, AMEX, or ALL (default: ALL)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of tickers to import (for testing)'
        )

    def handle(self, *args, **options):
        exchange_filter = options['exchange'].upper()
        limit = options.get('limit')
        
        self.stdout.write('Fetching ticker list...')
        
        # Get all tickers from the library
        try:
            # Get tickers from NYSE, NASDAQ, and AMEX
            all_tickers = []
            
            if exchange_filter in ['ALL', 'NYSE']:
                nyse_tickers = get_tickers(NYSE=True, NASDAQ=False, AMEX=False)
                for ticker in nyse_tickers:
                    all_tickers.append({'symbol': ticker, 'exchange': 'NYSE'})
                self.stdout.write(f'  Found {len(nyse_tickers)} NYSE tickers')
            
            if exchange_filter in ['ALL', 'NASDAQ']:
                nasdaq_tickers = get_tickers(NYSE=False, NASDAQ=True, AMEX=False)
                for ticker in nasdaq_tickers:
                    all_tickers.append({'symbol': ticker, 'exchange': 'NASDAQ'})
                self.stdout.write(f'  Found {len(nasdaq_tickers)} NASDAQ tickers')
            
            if exchange_filter in ['ALL', 'AMEX']:
                amex_tickers = get_tickers(NYSE=False, NASDAQ=False, AMEX=True)
                for ticker in amex_tickers:
                    all_tickers.append({'symbol': ticker, 'exchange': 'AMEX'})
                self.stdout.write(f'  Found {len(amex_tickers)} AMEX tickers')
            
            if limit:
                all_tickers = all_tickers[:limit]
                self.stdout.write(f'  Limited to {limit} tickers')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error fetching tickers: {e}'))
            return
        
        self.stdout.write(f'\nImporting {len(all_tickers)} tickers into database...')
        
        created_count = 0
        updated_count = 0
        error_count = 0
        
        for i, ticker_data in enumerate(all_tickers, 1):
            try:
                symbol = ticker_data['symbol']
                exchange = ticker_data['exchange']
                
                # Create or update stock with minimal info
                # Price data will be fetched on-demand when user views the stock
                stock, created = Stock.objects.update_or_create(
                    symbol=symbol,
                    defaults={
                        'exchange': exchange,
                        'currency': 'USD',  # Default for US stocks
                        # name, sector, industry will be filled when price data is fetched
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                
                # Progress indicator every 100 stocks
                if i % 100 == 0:
                    self.stdout.write(f'  Progress: {i}/{len(all_tickers)} ({created_count} new, {updated_count} updated)')
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.WARNING(f'  ✗ {symbol}: {str(e)[:50]}')
                )
        
        # Summary
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS(f'✓ Import complete!'))
        self.stdout.write(f'  Created: {created_count}')
        self.stdout.write(f'  Updated: {updated_count}')
        if error_count > 0:
            self.stdout.write(self.style.WARNING(f'  Errors: {error_count}'))
        self.stdout.write(f'  Total stocks in DB: {Stock.objects.count()}')
        self.stdout.write('=' * 50)
