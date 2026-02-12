from django.contrib import admin
from .models import FichaAtendimento


@admin.register(FichaAtendimento)
class FichaAtendimentoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "paciente", "status", "prioridade", "criado_em", "chamado_em", "finalizado_em")
    list_filter = ("status", "prioridade")
    search_fields = ("codigo", "paciente__nome", "paciente__cpf")
    ordering = ("-criado_em",)
