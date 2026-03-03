"""
Management command to populate common symbol redirects in the database
Handles ticker changes and helps users find stocks by old symbols
"""
from django.core.management.base import BaseCommand
from research.models import SymbolRedirect


class Command(BaseCommand):
    help = 'Populate database with common symbol redirects (ticker changes)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing redirects before populating',
        )

    def handle(self, *args, **options):
        # Common symbol redirects (old_symbol, new_symbol, reason)
        COMMON_REDIRECTS = [
            # Major rebrands
            ('FB', 'META', 'Rebranded from Facebook to Meta Platforms (2021)'),
            ('GOOGL', 'GOOG', 'Alphabet Class A shares'),
            ('TWTR', 'X', 'Acquired and rebranded to X Corp (2023)'),
            
            # Mergers and acquisitions
            ('ATVI', 'MSFT', 'Acquired by Microsoft (2023)'),
            ('FIT', 'GOOG', 'Acquired by Google/Alphabet (2021)'),
            
            # Ticker changes
            ('BABA', 'BABA', 'Alibaba Group - verify current listing'),
            ('TSM', 'TSM', 'Taiwan Semiconductor - verify current listing'),
            
            # Historical tickers that changed
            ('AAPL.O', 'AAPL', 'Apple - use AAPL for NASDAQ listing'),
            ('MSFT.O', 'MSFT', 'Microsoft - use MSFT for NASDAQ listing'),
            ('TSLA.O', 'TSLA', 'Tesla - use TSLA for NASDAQ listing'),
        ]

        if options['clear']:
            count = SymbolRedirect.objects.count()
            SymbolRedirect.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Cleared {count} existing redirects\n'))

        self.stdout.write('Populating symbol redirects...\n')
        
        created = 0
        updated = 0
        skipped = 0

        for old_symbol, new_symbol, reason in COMMON_REDIRECTS:
            redirect, was_created = SymbolRedirect.objects.update_or_create(
                old_symbol=old_symbol,
                defaults={
                    'new_symbol': new_symbol,
                    'reason': reason,
                    'is_active': True,
                }
            )
            
            if was_created:
                created += 1
                self.stdout.write(f'  ✓ Created: {old_symbol} → {new_symbol}')
            else:
                if redirect.new_symbol != new_symbol or redirect.reason != reason:
                    updated += 1
                    self.stdout.write(f'  ↻ Updated: {old_symbol} → {new_symbol}')
                else:
                    skipped += 1
                    self.stdout.write(f'  - Skipped: {old_symbol} → {new_symbol} (already exists)')

        self.stdout.write(f'\n{"="*60}')
        self.stdout.write(self.style.SUCCESS(
            f'\nSummary:\n'
            f'  Created: {created}\n'
            f'  Updated: {updated}\n'
            f'  Skipped: {skipped}\n'
            f'  Total:   {created + updated + skipped}'
        ))
        self.stdout.write(f'{"="*60}\n')
        
        self.stdout.write(self.style.SUCCESS('\n✓ Symbol redirects populated successfully!'))
        self.stdout.write('\nYou can add more redirects via the Django admin panel.')
