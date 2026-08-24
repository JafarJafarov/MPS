from django import forms


class CapacityImportForm(forms.Form):
    excel_file = forms.FileField(
        label="Ekip / Capacity Excel faylı",
        help_text="Yalnız .xlsx formatında fayl yükləyin."
    )

    def clean_excel_file(self):
        excel_file = self.cleaned_data["excel_file"]

        if not excel_file.name.lower().endswith(".xlsx"):
            raise forms.ValidationError(
                "Yalnız .xlsx formatında fayl qəbul edilir."
            )

        return excel_file
