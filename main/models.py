from typing import Iterable
from types import SimpleNamespace
from django.db import models
from decimal import Decimal
from django.db.models import Sum, Max
from datetime import datetime, time
from django.utils import timezone
from django.contrib.auth.models import User

# Create your model

class City(models.Model):
    name = models.CharField(max_length=100, verbose_name="Shahar nomi")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqti")

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Shahar"
        verbose_name_plural = "Shaharlar"
        ordering = ['-created']

class Building(models.Model):
    city = models.ForeignKey(to=City, on_delete=models.SET_NULL, null=True, verbose_name="Shahar", related_name="buildings")
    name = models.CharField(max_length=150, verbose_name="Bino nomi")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqti")
    padez = models.IntegerField(verbose_name="Padezlar soni")
    padez_home = models.JSONField(verbose_name="Xonadonlar soni")
    floor = models.IntegerField(verbose_name="Qavatlar")
    status = models.BooleanField(verbose_name="Qo'shilgan", default=False)
    location = models.TextField(verbose_name="Bino joylashuvi", null=True, blank=True)
    olchami = models.IntegerField(verbose_name="O'lchami", null=True, blank=True)
    code = models.CharField(max_length=2, unique=True, null=True, blank=True, verbose_name="Bino shifri")

    def __str__(self):
        return self.name
        
    class Meta:
        verbose_name = "Bino"
        verbose_name_plural = "Binolar"
        ordering = ['-created']

class HomeInformation(models.Model):
    padez_number = models.IntegerField(verbose_name="Padez raqami")
    home_number = models.CharField(max_length=200, verbose_name="Uy raqami")
    home_floor = models.IntegerField(verbose_name="Qavat")
    xona = models.IntegerField(verbose_name="Xonalar soni")
    field = models.FloatField(verbose_name="Uy maydoni (m/kv)")
    price = models.PositiveIntegerField(verbose_name="Uy narxi")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqti")
    home_model_id = models.IntegerField(verbose_name="Home model ID", null=True)
    busy = models.BooleanField(verbose_name="Band", default=False)
    floor_plan = models.ImageField(upload_to='floor_plans/', null=True, blank=True, verbose_name="Loyiha rasmi")
    floor_plan_drawing = models.ImageField(upload_to='floor_plan_drawings/', null=True, blank=True, verbose_name="Chertoj rasmi")
    
    def __str__(self):
        return f"{self.home_number} - uy, {self.padez_number} - padez"
    
    class Meta:
        verbose_name = "Uy ma'lumoti"
        verbose_name_plural = "Uy ma'lumotlari"
        ordering = ['padez_number', 'home_floor', 'home_number']

class Home(models.Model):
    building = models.ForeignKey(to=Building, on_delete=models.CASCADE, verbose_name="Bino", related_name="homes")
    home = models.ForeignKey(to=HomeInformation, on_delete=models.CASCADE, verbose_name="Uy", related_name="home_instances")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")
    
    def __str__(self):
        return f"{self.building.name} - {self.home.home_number}"
    
    class Meta:
        verbose_name = "Uy"
        verbose_name_plural = "Uylar"
        ordering = ['-created']
        unique_together = ['building', 'home']

class ClientInformation(models.Model):
    first_name = models.CharField(max_length=100, verbose_name="Ism")
    last_name = models.CharField(max_length=100, verbose_name="Familiya")
    middle_name = models.CharField(max_length=100, verbose_name="Sharif", blank=True, null=True)
    full_name = models.CharField(max_length=150, verbose_name="To'liq ism", blank=True)  # Backward compatibility
    phone = models.CharField(max_length=255, verbose_name="Telefon raqam", null=True)
    phone2 = models.CharField(max_length=255, verbose_name="Telefon raqam 2", null=True, blank=True)
    passport_number = models.CharField(max_length=20, verbose_name="Passport raqami", blank=True, null=True)
    passport_issue_date = models.CharField(max_length=50, verbose_name="Passport berilgan sana", blank=True, null=True)
    passport_expiry_date = models.CharField(max_length=50, verbose_name="Passport tugash sanasi", blank=True, null=True)
    passport_issue_place = models.CharField(max_length=255, verbose_name="Passport bergan tashkilot", blank=True, null=True)
    birth_date = models.CharField(max_length=50, verbose_name="Tug'ilgan sana", blank=True, null=True)
    address = models.CharField(max_length=255, verbose_name="Yashash manzili", blank=True, null=True)
    email = models.EmailField(verbose_name="Elektron pochta", blank=True, null=True)
    password = models.CharField(max_length=255, verbose_name="Parol", blank=True, null=True, help_text="Mijoz uchun parol")
    heard = models.CharField(max_length=200, verbose_name="Qayerda eshitgan", default='Xech qayerda')
    created = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        name_parts = [self.last_name, self.first_name]
        if self.middle_name:
            name_parts.append(self.middle_name)
        return ' '.join(name_parts) if any(name_parts) else self.full_name or 'Noma\'lum'
    
    def save(self, *args, **kwargs):
        # full_name ni avtomatik to'ldirish
        name_parts = [self.last_name, self.first_name]
        if self.middle_name:
            name_parts.append(self.middle_name)
        self.full_name = ' '.join(name_parts) if any(name_parts) else ''
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Mijoz ma'lumoti"
        verbose_name_plural = "Mijoz ma'lumotlari"
        ordering = ['-created']

class Client(models.Model):
    """Shartnoma"""
    STATUS_CHOICES = [
        ('Rasmiylashtirilmoqda', 'Rasmiylashtirilmoqda'),
        ('Rasmiylashtirilgan', 'Rasmiylashtirilgan'),
        ('Bekor qilingan', 'Bekor qilingan'),
        ('Tugallangan', 'Tugallangan'),
    ]
    
    client = models.ForeignKey(to=ClientInformation, on_delete=models.SET_NULL, null=True, verbose_name="Mijoz", related_name="contracts")
    contract = models.PositiveIntegerField(verbose_name="Shartnoma raqami", null=True, blank=True)
    home = models.ForeignKey(to=Home, on_delete=models.SET_NULL, null=True, verbose_name="Uy", related_name="contracts")
    passport = models.CharField(max_length=15, verbose_name="Passport")
    passport_muddat = models.CharField(max_length=25, verbose_name="Berilgan vaqti", null=True)
    given = models.CharField(max_length=100, verbose_name="Berilgan joyi", null=True)
    location = models.CharField(max_length=255, verbose_name="Manzili", null=True)
    location2 = models.CharField(max_length=255, verbose_name="Manzili 2", null=True, blank=True)
    term = models.IntegerField(verbose_name="To'lov muddati (oy)")
    payment = models.PositiveIntegerField(verbose_name="Oldindan to'lov")
    home_price = models.PositiveIntegerField(verbose_name="Xonadon narxi", null=True, blank=True)
    pay_date = models.PositiveIntegerField(verbose_name="To'lov qilish sanasi", null=True, blank=True)
    residual = models.DecimalField(max_digits=50, decimal_places=0, editable=False, verbose_name="Qolgan to'lov")
    oylik_tolov = models.DecimalField(max_digits=50, decimal_places=0, editable=False, verbose_name="Oylik to'lov")
    count_month = models.IntegerField(editable=False, verbose_name="Qolgan oylar")
    residu = models.IntegerField(editable=False, null=True, verbose_name="Oydan qogan to'lov")
    status = models.CharField(max_length=20, verbose_name="Holati", choices=STATUS_CHOICES)
    debt = models.BooleanField(default=False, verbose_name="Qarzdor")
    created = models.DateTimeField(verbose_name="Yaratilgan vaqti", null=True)
    
    def __str__(self):
        return f"{self.contract}"
    
    class Meta:
        verbose_name = "Shartnoma"
        verbose_name_plural = "Shartnomalar"
        ordering = ['-created']
        
    def save(self, *args, **kwargs):
        # Shartnoma yaratilganda, uyni band qilish
        if not self.pk:  # Yangi obyekt yaratilayotgan bo'lsa
            if self.home and self.home.home:
                self.home.home.busy = True
                self.home.home.save()
                
        super().save(*args, **kwargs)


class ConsultingContract(models.Model):
    class StatusChoices(models.TextChoices):
        DRAFT = "draft", "Qoralama"
        PREPARATION = "preparation", "Hujjat tayyorlanmoqda"
        SUBMITTED = "submitted", "Taqdim etildi"
        COMPLETED = "completed", "Yakunlandi"
        CANCELLED = "cancelled", "Bekor qilindi"

    contract_number = models.PositiveIntegerField(unique=True, verbose_name="Shartnoma raqami")
    # DateField defaultiga timezone.now berilsa datetime qaytishi mumkin.
    # Shu uchun faqat date qaytaruvchi callable ishlatamiz.
    from datetime import date as _date
    contract_date = models.DateField(auto_now_add=True, verbose_name="Shartnoma sanasi")
    contract_location = models.CharField(max_length=150, default="Xiva", verbose_name="Shartnoma tuzilgan joy")

    # Mijoz ma'lumotlari ClientInformation modelida saqlanadi
    client = models.ForeignKey(to=ClientInformation, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Mijoz", related_name="consulting_contracts")
    
    # Eski maydonlar (backward compatibility uchun saqlanadi, lekin client orqali olinadi)
    client_first_name = models.CharField(max_length=100, verbose_name="Ism", blank=True)
    client_last_name = models.CharField(max_length=100, verbose_name="Familiya", blank=True)
    client_middle_name = models.CharField(max_length=100, verbose_name="Sharif", blank=True, null=True)
    client_full_name = models.CharField(max_length=255, verbose_name="Buyurtmachi ism familiyasi", blank=True)
    passport_number = models.CharField(max_length=20, verbose_name="Passport raqami", blank=True)
    passport_issue_date = models.CharField(max_length=50, verbose_name="Passport berilgan sana", blank=True, null=True)
    passport_expiry_date = models.CharField(max_length=50, verbose_name="Passport tugash sanasi", blank=True, null=True)
    passport_issue_place = models.CharField(max_length=255, verbose_name="Passport bergan tashkilot", blank=True, null=True)
    client_address = models.CharField(max_length=255, verbose_name="Buyurtmachining manzili", blank=True)
    phone_primary = models.CharField(max_length=20, verbose_name="Telefon raqam 1", blank=True)
    phone_secondary = models.CharField(max_length=20, verbose_name="Telefon raqam 2", blank=True, null=True)

    service_name = models.CharField(max_length=255, verbose_name="Xizmat nomi")
    service_country = models.CharField(max_length=150, default="Angliya", verbose_name="Xizmat davlati")
    visa_type = models.CharField(max_length=150, verbose_name="Visa turi yoki yo'nalish")
    service_description = models.TextField(verbose_name="Xizmat tavsifi", null=True, blank=True)

    total_service_fee = models.PositiveIntegerField(verbose_name="Umumiy xizmat summasi (so'm)")
    initial_payment_amount = models.PositiveIntegerField(verbose_name="Boshlang'ich to'lov", default=0)
    initial_payment_due_days = models.PositiveIntegerField(verbose_name="Boshlang'ich to'lov muddati (kun)", default=3)
    post_interview_payment_amount = models.PositiveIntegerField(verbose_name="Suhbatdan keyingi to'lov", default=0)
    post_interview_due_days = models.PositiveIntegerField(verbose_name="Suhbatdan keyingi to'lov muddati (kun)", default=3)
    refund_amount = models.PositiveIntegerField(verbose_name="Qaytariladigan summa (agar kerak bo'lsa)", default=0)
    service_duration_months = models.PositiveIntegerField(verbose_name="Xizmat davri (oy)", default=8)

    amount_paid = models.PositiveIntegerField(verbose_name="Haqiqiy to'langan summa", default=0)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PREPARATION)
    notes = models.TextField(blank=True, null=True, verbose_name="Qo'shimcha izohlar")
    
    # Passport/ID karta rasmlari (max 1 ta - zagran)
    passport_images = models.JSONField(default=list, blank=True, verbose_name="Zagran passport rasmlari", help_text="Maksimal 1 ta rasm")
    # VISA rasmlari (max 1 ta)
    visa_images = models.JSONField(default=list, blank=True, verbose_name="VISA rasmlari", help_text="Maksimal 1 ta rasm")
    
    # Ish yakunlanganidan keyin shartnoma rasmlari (max 3 ta)
    completed_contract_images = models.JSONField(default=list, blank=True, verbose_name="Yakunlangan shartnoma rasmlari", help_text="Maksimal 3 ta rasm")

    # Shartnomani yaratgan foydalanuvchi
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Yaratgan foydalanuvchi", related_name="created_contracts")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Konsalting shartnomasi"
        verbose_name_plural = "Konsalting shartnomalari"
        ordering = ['-created_at']

    def __str__(self):
        name_parts = [self.client_last_name, self.client_first_name]
        if self.client_middle_name:
            name_parts.append(self.client_middle_name)
        full_name = ' '.join(name_parts) if any(name_parts) else self.client_full_name or 'Noma\'lum'
        return f"#{self.contract_number} - {full_name}"

    @property
    def remaining_amount(self):
        remaining = (self.total_service_fee or 0) - (self.amount_paid or 0)
        return remaining if remaining > 0 else 0

    def as_legacy_contract(self):
        city_info = SimpleNamespace(name=self.service_country or "")
        building_info = SimpleNamespace(
            code=self.service_country or "",
            location=self.contract_location or "",
            olchami=self.service_duration_months or 0,
            padez='',
            city=city_info,
            name=self.service_name or "",
        )
        home_info = SimpleNamespace(
            padez_number='',
            home_number=self.visa_type or "",
            home_floor='',
            field=self.service_description or "",
            xona='',
        )
        home = SimpleNamespace(building=building_info, home=home_info)
        client_info = SimpleNamespace(
            full_name=self.client_full_name,
            phone=self.phone_primary,
            phone2=self.phone_secondary,
            iib='',
        )
        created_dt = datetime.combine(self.contract_date, time.min)
        created_dt = timezone.make_aware(created_dt, timezone.get_current_timezone())

        return SimpleNamespace(
            contract=self.contract_number,
            client=client_info,
            home=home,
            passport=self.passport_number,
            passport_muddat=self.passport_issue_date or '',
            given=self.passport_issue_place or '',
            location=self.client_address,
            location2='',
            payment=self.initial_payment_amount,
            home_price=self.total_service_fee,
            pay_date=self.initial_payment_due_days,
            count_month=self.service_duration_months,
            status=self.get_status_display(),
            residual=self.remaining_amount,
            created=created_dt,
        )


class ContractFamilyMember(models.Model):
    """Shartnoma bilan bog'langan ota-onasi, farzandlari va boshqa qarindoshlar"""
    RELATIONSHIP_CHOICES = [
        ('father', 'Ota'),
        ('mother', 'Ona'),
        ('son', 'O\'g\'il'),
        ('daughter', 'Qiz'),
        ('spouse', 'Turmush o\'rtog\'i'),
        ('brother', 'Aka/uka'),
        ('sister', 'Opa/singil'),
        ('other', 'Boshqa'),
    ]
    
    contract = models.ForeignKey(to=ConsultingContract, on_delete=models.CASCADE, verbose_name="Shartnoma", related_name="family_members")
    first_name = models.CharField(max_length=100, verbose_name="Ism")
    last_name = models.CharField(max_length=100, verbose_name="Familiya")
    middle_name = models.CharField(max_length=100, verbose_name="Sharif", blank=True, null=True)
    full_name = models.CharField(max_length=255, verbose_name="To'liq ism familiya", blank=True)  # Backward compatibility
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES, verbose_name="Qarindoshlik darajasi")
    passport_number = models.CharField(max_length=20, verbose_name="Passport raqami", blank=True, null=True)
    passport_issue_date = models.CharField(max_length=50, verbose_name="Passport berilgan sana", blank=True, null=True)
    passport_expiry_date = models.CharField(max_length=50, verbose_name="Passport tugash sanasi", blank=True, null=True)
    passport_issue_place = models.CharField(max_length=255, verbose_name="Passport bergan tashkilot", blank=True, null=True)
    birth_date = models.CharField(max_length=50, verbose_name="Tug'ilgan sana", blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name="Telefon raqam", blank=True, null=True)
    notes = models.TextField(blank=True, null=True, verbose_name="Qo'shimcha ma'lumotlar")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Shartnoma qarindoshi"
        verbose_name_plural = "Shartnoma qarindoshlari"
        ordering = ['-created_at']
    
    def __str__(self):
        name_parts = [self.last_name, self.first_name]
        if self.middle_name:
            name_parts.append(self.middle_name)
        full_name = ' '.join(name_parts) if any(name_parts) else self.full_name or 'Noma\'lum'
        return f"{self.get_relationship_display()} - {full_name}"
    
    def save(self, *args, **kwargs):
        # full_name ni avtomatik to'ldirish
        name_parts = [self.last_name, self.first_name]
        if self.middle_name:
            name_parts.append(self.middle_name)
        self.full_name = ' '.join(name_parts) if any(name_parts) else ''
        super().save(*args, **kwargs)


class Rasrochka(models.Model):
    client = models.ForeignKey(to=Client, on_delete=models.CASCADE, null=True, verbose_name="Mijoz", related_name="payments")
    month = models.IntegerField(verbose_name="Oy raqami")
    amount = models.IntegerField(verbose_name="To'lov miqdori")
    amount_paid = models.IntegerField(verbose_name="To'langan miqdor", default=0)
    qoldiq = models.IntegerField(verbose_name="Oy uchun qoldiq", editable=False)
    pay_date = models.DateTimeField(verbose_name="O'xirgi to'lov sanasi", null=True, blank=True)
    date = models.DateTimeField(verbose_name="To'lov sanasi")

    def save(self, *args, **kwargs):
        self.qoldiq = self.amount - self.amount_paid
        if not self.pay_date and self.amount_paid > 0:
            self.pay_date = timezone.now()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.client} - {self.month}-oy"
    
    class Meta:
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"
        ordering = ['client', 'month']

class ClientTrash(models.Model):
    client = models.ForeignKey(to=ClientInformation, on_delete=models.SET_NULL, null=True, verbose_name="Mijoz")
    home = models.ForeignKey(to=Home, on_delete=models.SET_NULL, null=True, verbose_name="Uy")
    passport = models.CharField(max_length=15, verbose_name="Passport")
    term = models.IntegerField(verbose_name="To'lov muddati (oy)")
    payment = models.PositiveIntegerField(verbose_name="Oldindan to'lov")
    residual = models.DecimalField(max_digits=50, decimal_places=0, editable=False, verbose_name="Qolgan to'lov")
    oylik_tolov = models.DecimalField(max_digits=50, decimal_places=0, editable=False, verbose_name="Oylik to'lov")
    count_month = models.IntegerField(editable=False, verbose_name="Qolgan oylar")
    status = models.CharField(max_length=20, verbose_name="Holati")
    debt = models.BooleanField(default=False, verbose_name="Qarzdor")
    created = models.DateTimeField(verbose_name="Yaratilgan vaqti")
    trash_created = models.DateTimeField(auto_now_add=True, verbose_name="Savatda yaratilgan")
    
    def __str__(self):
        return f"{self.client.full_name} - O'chirilgan"
    
    class Meta:
        verbose_name = "O'chirilgan shartnoma"
        verbose_name_plural = "O'chirilgan shartnomalar"
        ordering = ['-trash_created']

class ExpenseType(models.Model):
    name = models.CharField(max_length=200, verbose_name="Chiqim turi")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqti")

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Chiqim turi"
        verbose_name_plural = "Chiqim turlari"
        ordering = ['-created']

class Expense(models.Model):
    expense_type = models.ForeignKey(ExpenseType, on_delete=models.CASCADE, verbose_name="Chiqim turi")
    building = models.ForeignKey(Building, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Bino")
    amount = models.IntegerField(verbose_name="Summa")
    description = models.TextField(null=True, blank=True, verbose_name="Izoh")
    payment_type = models.CharField(max_length=50, choices=[
        ('Naqd', 'Naqd'),
        ('Plastik', 'Plastik'),
        ('Hisobdan o\'tkazish', 'Hisobdan o\'tkazish')
    ], default='Naqd', verbose_name="To'lov turi")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated = models.DateTimeField(auto_now=True, verbose_name="O'zgartirilgan sana")
    
    class Meta:
        verbose_name = "Chiqim"
        verbose_name_plural = "Chiqimlar"
        ordering = ['-created']

    def __str__(self):
        return f"{self.expense_type.name} - {self.amount:,} so'm"


class BotUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    language = models.CharField(max_length=20, default='uz_latin', choices=[
        ('uz_latin', 'O\'zbekcha (Lotin)'),
        ('uz_cyrillic', 'Ўзбекча (Кирил)'),
        ('russian', 'Русский'),
    ])
    created = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.first_name} ({self.telegram_id})"
    
    class Meta:
        verbose_name = "Bot Foydalanuvchisi"
        verbose_name_plural = "Bot Foydalanuvchilari"
        
class CallOperator(models.Model):
    full_name = models.CharField(max_length=150, verbose_name="Operator ismi")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqti")
    updated = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")
    
    class Meta:
        verbose_name = "Operator"
        verbose_name_plural = "Operatorlar"
        ordering = ['-created']
        
    def __str__(self):
        return self.full_name

# Yangi LeadStage modeli
class LeadStage(models.Model):
  name = models.CharField(max_length=100, verbose_name="Bosqich nomi")
  key = models.CharField(max_length=50, unique=True, verbose_name="Kalit (inglizcha)")
  color = models.CharField(max_length=7, default="#007bff", verbose_name="Rang (HEX)")
  description = models.TextField(blank=True, verbose_name="Tavsif")
  order = models.IntegerField(default=0, verbose_name="Tartib raqami")
  is_system_stage = models.BooleanField(default=False, verbose_name="Tizim bosqichi")

  class Meta:
      verbose_name = "Lead Bosqichi"
      verbose_name_plural = "Lead Bosqichlari"
      ordering = ['order']

  def __str__(self):
      return self.name

class Lead(models.Model):
  CALL_STATUS_CHOICES = [
      ('answered', 'Javob berildi'),
      ('not_answered', 'Javob berilmadi'),
      ('client_answered', 'Mijoz javob berdi'),
      ('client_not_answered', 'Mijoz javob bermadi'),
  ]

  phone_number = models.CharField(max_length=20, verbose_name="Telefon raqami")
  client_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Mijoz ismi")
  operator = models.ForeignKey(CallOperator, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Operator")
  call_status = models.CharField(max_length=20, choices=CALL_STATUS_CHOICES, blank=True, null=True, verbose_name="Qo'ng'iroq holati")
  call_duration = models.DurationField(blank=True, null=True, verbose_name="Qo'ng'iroq davomiyligi")
  notes = models.TextField(blank=True, null=True, verbose_name="Izohlar")
  audio_recording = models.FileField(upload_to='lead_audio/', blank=True, null=True, verbose_name="Audio yozuv")
  follow_up_date = models.DateTimeField(blank=True, null=True, verbose_name="Keyingi aloqa sanasi")
  is_converted = models.BooleanField(default=False, verbose_name="Mijozga aylangan")
  converted_client = models.ForeignKey(ClientInformation, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Aylantirilgan mijoz")
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)
  
  stage = models.ForeignKey(LeadStage, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Bosqich")

  class Meta:
      verbose_name = "Lead"
      verbose_name_plural = "Leadlar"
      ordering = ['-created_at']

  def __str__(self):
      return f"Lead {self.id} - {self.client_name or self.phone_number}"

  def get_duration_display(self):
      if self.call_duration:
          total_seconds = int(self.call_duration.total_seconds())
          hours = total_seconds // 3600
          minutes = (total_seconds % 3600) // 60
          seconds = total_seconds % 60
          return f"{hours:02}:{minutes:02}:{seconds:02}"
      return "00:00:00"

  def get_current_stage_key(self):
      """Leadning joriy holatiga qarab uning bosqich kalitini aniqlaydi.
      Bu funksiya har doim siz bergan 6 ta kalitdan birini qaytarishi kerak."""
      if self.is_converted:
          return 'converted'
      if self.follow_up_date and self.follow_up_date > timezone.now():
          return 'follow_up'
      if self.call_status == 'answered':
          return 'answered'
      if self.call_status == 'client_answered':
          return 'client_answered'
      if self.call_status == 'client_not_answered':
          return 'client_not_answered'
      # Agar yuqoridagi shartlarning hech biri bajarilmasa (masalan, yangi leadda call_status None bo'lsa),
      # uni 'not_answered' bosqichiga yo'naltiramiz. Bu sizning yangi bosqichlaringiz orasida
      # eng mos keladigan "boshlang'ich" holat hisoblanadi.
      return 'not_answered'

  def save(self, *args, **kwargs):
      # stage maydoni endi save() metodida avtomatik belgilanmaydi.
      # U view funksiyalarida aniq belgilanishi kerak.
      # Agar stage mavjud bo'lmasa (masalan, yangi lead yaratilganda va stage berilmagan bo'lsa),
      # uni get_current_stage_key() orqali belgilash mumkin.
      if not self.stage_id: # Agar stage hali belgilanmagan bo'lsa
          current_stage_key = self.get_current_stage_key()
          try:
              self.stage = LeadStage.objects.get(key=current_stage_key)
          except LeadStage.DoesNotExist:
              # Agar belgilangan stage topilmasa, 'not_answered' ga qaytaramiz
              self.stage = LeadStage.objects.get(key='not_answered')
      super().save(*args, **kwargs)