from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('research', '0006_symbolredirect'),
    ]

    operations = [
        migrations.DeleteModel(name='WatchlistItem'),
        migrations.DeleteModel(name='Watchlist'),
        migrations.DeleteModel(name='SymbolRedirect'),
    ]
