from django import forms
from django.contrib import messages
from django.shortcuts import redirect, render

from apps.equipos.redes import REDES, RedesSocialesMixin
from apps.usuarios.forms import StyledFormMixin
from apps.usuarios.permissions import superadmin_required

from .models import RedesDeBuho


class RedesDeBuhoForm(RedesSocialesMixin, StyledFormMixin, forms.ModelForm):
    class Meta:
        model = RedesDeBuho
        fields = list(RedesSocialesMixin.CAMPOS_DE_REDES)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._preparar_redes()
        for red in REDES:
            self.fields[red.campo].widget.attrs['placeholder'] = (
                red.ejemplo.replace('tu_equipo', 'buhosport'))


@superadmin_required
def editar(request):
    redes = RedesDeBuho.la_unica()
    if request.method == 'POST':
        form = RedesDeBuhoForm(request.POST, instance=redes)
        if form.is_valid():
            form.save()
            messages.success(request, 'Se guardaron las redes sociales de BUHO.')
            return redirect('redes-buho')
    else:
        form = RedesDeBuhoForm(instance=redes)
    return render(request, 'informacion/redes_buho.html', {'form': form})
