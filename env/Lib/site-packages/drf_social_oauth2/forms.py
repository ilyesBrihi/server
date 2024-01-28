from django.forms import Form, CharField


class MultiFactorAuthForm(Form):
    code_value_1 = CharField(max_length=1, empty_value=False, required=True)
    code_value_2 = CharField(max_length=1, empty_value=False, required=True)
    code_value_3 = CharField(max_length=1, empty_value=False, required=True)
    code_value_4 = CharField(max_length=1, empty_value=False, required=True)
    code_value_5 = CharField(max_length=1, empty_value=False, required=True)
    code_value_6 = CharField(max_length=1, empty_value=False, required=True)
