from django.contrib import admin

from .models import AccountProblemsFilter


# securegroups smart filters are created in the Django admin, like corptools' own
@admin.register(AccountProblemsFilter)
class AccountProblemsFilterAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "reversed_logic", "include_corporation")
