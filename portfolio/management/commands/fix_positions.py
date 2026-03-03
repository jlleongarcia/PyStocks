"""
Management command to recalculate all portfolio positions from transactions
"""
from django.core.management.base import BaseCommand
from portfolio.models import Portfolio, Position, Transaction
from portfolio.services import PortfolioCalculationService


class Command(BaseCommand):
    help = 'Recalculate all portfolio positions from transactions'

    def handle(self, *args, **options):
        self.stdout.write('Starting position recalculation...\n')
        
        # Delete all positions with zero values
        zero_positions = Position.objects.filter(quantity=0, average_cost=0)
        count = zero_positions.count()
        zero_positions.delete()
        self.stdout.write(f'Deleted {count} invalid positions\n')
        
        # Process all transactions in chronological order
        transactions = Transaction.objects.all().order_by('transaction_date', 'id')
        self.stdout.write(f'Processing {transactions.count()} transactions...\n')
        
        processed = 0
        errors = 0
        
        for transaction in transactions:
            try:
                # Update/create position
                position = PortfolioCalculationService.update_position_from_transaction(transaction)
                
                # Fetch buy yield for BUY transactions
                if transaction.transaction_type == 'BUY':
                    PortfolioCalculationService.fetch_and_store_buy_yield(transaction)
                
                processed += 1
                self.stdout.write(f'  ✓ {transaction.symbol}: {transaction.transaction_type} {transaction.quantity} @ ${transaction.price}')
                
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f'  ✗ Error processing transaction {transaction.id}: {e}'))
        
        # Display summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'\nProcessed: {processed} transactions'))
        if errors > 0:
            self.stdout.write(self.style.ERROR(f'Errors: {errors}'))
        
        # Show final positions
        self.stdout.write('\n=== Portfolio Summary ===')
        for portfolio in Portfolio.objects.all():
            positions = portfolio.positions.all()
            self.stdout.write(f'\n{portfolio.name} (ID: {portfolio.id}):')
            self.stdout.write(f'  Transactions: {portfolio.transactions.count()}')
            self.stdout.write(f'  Positions: {positions.count()}')
            for pos in positions:
                self.stdout.write(f'    • {pos.symbol}: {pos.quantity} shares @ ${pos.average_cost}')
        
        self.stdout.write(self.style.SUCCESS('\n✓ Position recalculation complete!'))
