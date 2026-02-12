from django import forms


INPUT_STYLE = "w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"



class RecepcaoGerarSenhaForm(forms.Form):
    nome = forms.CharField(
        label="Nome completo",
        max_length=255,
        widget=forms.TextInput(attrs={"class": INPUT_STYLE})
    )

    cpf = forms.CharField(
        label="CPF",
        max_length=14,
        widget=forms.TextInput(attrs={"class": INPUT_STYLE})
    )

    telefone = forms.CharField(
        label="Telefone",
        required=False,
        widget=forms.TextInput(attrs={"class": INPUT_STYLE})
    )

    nome_mae = forms.CharField(
        label="Nome da mãe",
        required=False,
        widget=forms.TextInput(attrs={"class": INPUT_STYLE})
    )

    data_nascimento = forms.DateField(
        label="Data de nascimento",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": INPUT_STYLE})
    )

    def clean_cpf(self):
        cpf = self.cleaned_data["cpf"]
        digits = "".join([c for c in cpf if c.isdigit()])
        if len(digits) != 11:
            raise forms.ValidationError("CPF inválido.")
        return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"
