# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0021_add_birth_date_to_client_information'),
    ]

    operations = [
        migrations.AlterField(
            model_name='clientinformation',
            name='birth_date',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name="Tug'ilgan sana"),
        ),
        migrations.AlterField(
            model_name='contractfamilymember',
            name='birth_date',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name="Tug'ilgan sana"),
        ),
    ]



