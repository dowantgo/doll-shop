from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0002_alter_paymenttransaction_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymenttransaction',
            name='reconcile_attempts',
            field=models.PositiveIntegerField(default=0, verbose_name='Reconcile attempts'),
        ),
        migrations.AddField(
            model_name='paymenttransaction',
            name='last_reconcile_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Last reconcile time'),
        ),
        migrations.AddField(
            model_name='paymenttransaction',
            name='last_reconcile_status',
            field=models.CharField(blank=True, default='', max_length=32, verbose_name='Last reconcile status'),
        ),
        migrations.AddField(
            model_name='paymenttransaction',
            name='last_reconcile_error',
            field=models.TextField(blank=True, default='', verbose_name='Last reconcile error'),
        ),
    ]
