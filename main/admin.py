from django.contrib import admin
from main.models import * 

# Register your models here

admin.site.register(City)
admin.site.register(Building)
admin.site.register(Home)
admin.site.register(HomeInformation)
admin.site.register(ClientInformation)
admin.site.register(Client)
admin.site.register(Rasrochka)

# @admin.register(ExpenseType)
# class ExpenseTypeAdmin(admin.ModelAdmin):
#     list_display = ['name', 'created']
#     search_fields = ['name']

# @admin.register(Expense)
# class ExpenseAdmin(admin.ModelAdmin):
#     list_display = ['expense_type', 'amount', 'payment_type', 'provider', 'created']
#     list_filter = ['expense_type', 'payment_type', 'created']
#     search_fields = ['expense_type__name', 'provider', 'description']
#     date_hierarchy = 'created'

# class AdminClient(admin.ModelAdmin):
#     list_display = ["full_name", "telefon", "city", "building", "home", "passport", "term", "payment", "residual", "oylik_tolov", "count_month", "status"]
