from django import forms

from .models import (
    ActivityBlock,
    Child,
    Goal,
    HomeProgram,
    OptionPoint,
    Proforma,
    SessionPlan,
)


class ChildIntakeForm(forms.ModelForm):
    interests_text = forms.CharField(
        required=False,
        label="Interests",
        help_text="Comma-separated, e.g. \"dinosaurs, space, drawing\"",
        widget=forms.TextInput(attrs={"placeholder": "dinosaurs, space, drawing"}),
    )
    proformas = forms.ModelMultipleChoiceField(
        queryset=Proforma.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Diagnoses noted (if any)",
    )

    class Meta:
        model = Child
        fields = [
            "initial_or_name", "age_years", "age_months", "default_environment",
            "current_presentation", "masking_note", "family_cultural_context",
        ]
        widgets = {
            "current_presentation": forms.Textarea(attrs={"rows": 4}),
            "masking_note": forms.Textarea(attrs={"rows": 2}),
            "family_cultural_context": forms.Textarea(attrs={"rows": 2}),
        }

    def save(self, commit=True):
        child = super().save(commit=commit)
        if commit:
            self._save_interests(child)
            child.proformas.set(self.cleaned_data["proformas"])
        return child

    def _save_interests(self, child):
        from .models import Interest

        names = [n.strip() for n in self.cleaned_data["interests_text"].split(",") if n.strip()]
        interests = [Interest.objects.get_or_create(name=n)[0] for n in names]
        child.interests.set(interests)


class GoalIntakeForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ["domain", "raw_goal_text"]
        widgets = {
            "raw_goal_text": forms.Textarea(attrs={"rows": 3, "placeholder": "The goal in your own words"}),
        }


class GoalRefineForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ["interim_goal_text", "outcome_goal_text"]
        widgets = {
            "interim_goal_text": forms.Textarea(attrs={"rows": 3}),
            "outcome_goal_text": forms.Textarea(attrs={"rows": 3}),
        }


class OptionPointForm(forms.ModelForm):
    options_text = forms.CharField(
        label="Options (one per line)",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Option A\nOption B"}),
    )

    class Meta:
        model = OptionPoint
        fields = ["question_text", "selected_option", "rationale_note"]
        widgets = {
            "question_text": forms.Textarea(attrs={"rows": 2}),
            "rationale_note": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["options_text"].initial = "\n".join(self.instance.options_json)

    def clean_options_text(self):
        options = [line.strip() for line in self.cleaned_data["options_text"].splitlines() if line.strip()]
        if not options:
            raise forms.ValidationError("Enter at least one option.")
        return options

    def save(self, commit=True):
        option_point = super().save(commit=False)
        option_point.options_json = self.cleaned_data["options_text"]
        if commit:
            option_point.save()
        return option_point


class SessionPlanSetupForm(forms.ModelForm):
    class Meta:
        model = SessionPlan
        fields = ["session_length_minutes", "environment"]


class ActivityBlockForm(forms.ModelForm):
    class Meta:
        model = ActivityBlock
        fields = [
            "block_type", "order", "duration_minutes", "title",
            "activity_description", "clinical_reasoning", "resources",
            "grade_up_note", "grade_down_note",
        ]
        widgets = {
            "activity_description": forms.Textarea(attrs={"rows": 4}),
            "clinical_reasoning": forms.Textarea(attrs={"rows": 3}),
            "grade_up_note": forms.Textarea(attrs={"rows": 2}),
            "grade_down_note": forms.Textarea(attrs={"rows": 2}),
            "resources": forms.SelectMultiple(attrs={"size": 10}),
        }

    def __init__(self, *args, domain=None, **kwargs):
        super().__init__(*args, **kwargs)
        if domain is not None:
            self.fields["resources"].queryset = domain.resources.order_by("name")


class HomeProgramForm(forms.ModelForm):
    class Meta:
        model = HomeProgram
        fields = [
            "goal_plain_language", "why_this_helps", "activity_description",
            "home_resources", "frequency", "grade_up_tip_plain",
            "grade_down_tip_plain", "safety_note",
        ]
        widgets = {
            "goal_plain_language": forms.Textarea(attrs={"rows": 2}),
            "why_this_helps": forms.Textarea(attrs={"rows": 2}),
            "activity_description": forms.Textarea(attrs={"rows": 4}),
            "grade_up_tip_plain": forms.Textarea(attrs={"rows": 2}),
            "grade_down_tip_plain": forms.Textarea(attrs={"rows": 2}),
            "safety_note": forms.Textarea(attrs={"rows": 2}),
            "home_resources": forms.SelectMultiple(attrs={"size": 10}),
        }
