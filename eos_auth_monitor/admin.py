from django.contrib import admin

from .models import CharacterProblemsFilter


# securegroups smart filters are created in the Django admin, like corptools' own
@admin.register(CharacterProblemsFilter)
class CharacterProblemsFilterAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "reversed_logic")
