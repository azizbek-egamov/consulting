from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0019_remove_consultingcontract_passport_expiry_date_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="consultingcontract",
            name="passport_expiry_date",
            field=models.CharField(
                max_length=50,
                blank=True,
                null=True,
                verbose_name="Passport tugash sanasi",
            ),
        ),
        migrations.AddField(
            model_name="contractfamilymember",
            name="passport_expiry_date",
            field=models.CharField(
                max_length=50,
                blank=True,
                null=True,
                verbose_name="Passport tugash sanasi",
            ),
        ),
    ]

