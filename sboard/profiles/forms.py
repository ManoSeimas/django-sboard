from django import forms

from sboard.forms import BaseNodeForm


class ProfileForm(BaseNodeForm):
    first_name = forms.CharField()
    last_name = forms.CharField()
    dob = forms.DateField()
    home_page = forms.URLField()

    def get_initial_values(self):
        initial = dict(self.node._doc)
        return initial

    def clean_dob(self):
        dob = self.cleaned_data.get('dob')
        if dob:
            dob = dob.isoformat()
        return dob
