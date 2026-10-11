from django import forms
from .models import Recipe


class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ['name', 'ingredients', 'cooking_time', 'difficulty', 'description']
        widgets = {
            'ingredients': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Через запятую'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if len(name) < 2:
            raise forms.ValidationError('Название должно содержать минимум 2 символа.')
        if len(name) > 200:
            raise forms.ValidationError('Название слишком длинное.')
        return name

    def clean_ingredients(self):
        ing = self.cleaned_data['ingredients'].strip()
        if len(ing) < 3:
            raise forms.ValidationError('Перечислите хотя бы один ингредиент.')
        return ing

    def clean_cooking_time(self):
        t = self.cleaned_data['cooking_time']
        if t <= 0:
            raise forms.ValidationError('Время должно быть больше нуля.')
        if t > 1440:
            raise forms.ValidationError('Время не может превышать 1440 минут (сутки).')
        return t