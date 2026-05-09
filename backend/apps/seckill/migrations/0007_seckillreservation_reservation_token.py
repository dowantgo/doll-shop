from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('seckill', '0006_seckillactivity_idx_seckill_group_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='seckillreservation',
            name='reservation_token',
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=128,
                null=True,
                verbose_name='Reservation token',
            ),
        ),
    ]
