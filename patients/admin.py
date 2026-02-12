from django.contrib import admin
from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("nome", "cpf", "telefone", "data_nascimento", "criado_em")
    search_fields = ("nome", "cpf")
    ordering = ("-criado_em",)
