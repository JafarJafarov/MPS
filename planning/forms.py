from django import forms

from .models import WeeklyPlan


class SAPImportForm(forms.Form):
    excel_file = forms.FileField(
        label="SAP / IW37N Excel faylı",
        help_text="Yalnız .xlsx formatında Excel faylı yükləyin."
    )

    def clean_excel_file(self):
        excel_file = self.cleaned_data["excel_file"]

        if not excel_file.name.lower().endswith(".xlsx"):
            raise forms.ValidationError(
                "Yalnız .xlsx formatında Excel faylı qəbul edilir."
            )

        return excel_file


class WeeklyPlanForm(forms.ModelForm):

    class Meta:
        model = WeeklyPlan

        fields = [
            "name",
            "year",
            "week_number",
            "start_date",
            "end_date",
            "status",
        ]

        labels = {
            "name": "Proqramın adı",
            "year": "İl",
            "week_number": "Həftə nömrəsi",
            "start_date": "Başlama tarixi",
            "end_date": "Bitmə tarixi",
            "status": "Status",
        }

        widgets = {
            "start_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "end_date": forms.DateInput(
                attrs={"type": "date"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        year = cleaned_data.get("year")
        week_number = cleaned_data.get("week_number")
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if week_number:
            if week_number < 1 or week_number > 53:
                self.add_error(
                    "week_number",
                    "Həftə nömrəsi 1–53 arasında olmalıdır."
                )

        if start_date and end_date:
            if end_date < start_date:
                self.add_error(
                    "end_date",
                    "Bitmə tarixi başlama tarixindən əvvəl ola bilməz."
                )

        if year and week_number:
            exists = WeeklyPlan.objects.filter(
                year=year,
                week_number=week_number
            ).exists()

            if exists:
                self.add_error(
                    "week_number",
                    f"W{week_number}-{year} artıq sistemdə mövcuddur."
                )

        return cleaned_data


class ITKImportForm(forms.Form):

    weekly_plan = forms.ModelChoiceField(
        queryset=WeeklyPlan.objects.all(),
        label="Proqram həftəsi",
        empty_label="Həftəni seçin"
    )

    excel_file = forms.FileField(
        label="İTK Excel faylı",
        help_text="Yalnız .xlsx formatında fayl yükləyin."
    )

    def clean_excel_file(self):
        excel_file = self.cleaned_data["excel_file"]

        if not excel_file.name.lower().endswith(".xlsx"):
            raise forms.ValidationError(
                "Yalnız .xlsx formatında Excel faylı qəbul edilir."
            )

        return excel_file