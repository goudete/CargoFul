from django import forms
from .models import order
from crispy_forms.helper import FormHelper
from datetime import datetime
from django.contrib.admin.widgets import AdminDateWidget


class Order_Form(forms.ModelForm):
    class Meta:
        model = order
        fields = [
            'pickup_date',
            'pickup_time',
            'truck_type',
            'price',
            'contents',
            'instructions'
            ]
        widgets = {
            'pickup_date': forms.DateInput(attrs={'id':'datepicker'}),
            'pickup_time': forms.TimeInput(attrs = {'id': 'timepicker'}),
            'contents': forms.Textarea(attrs={'cols': 5, 'rows': 5}),
            'instructions': forms.Textarea(attrs={'cols': 5, 'rows': 5})
        }
    def __init__(self, *args, **kwargs):
        super(Order_Form, self).__init__(*args, **kwargs)
        self.fields['price'].widget.attrs['min'] = 0
