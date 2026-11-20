from django import forms
from .models import Movie, Review, Rating


class MovieForm(forms.ModelForm):
    class Meta:
        model = Movie
        fields = ['title', 'year', 'duration', 'poster', 'description', 'genres', 'tags']
        widgets = {
            'description': forms.Textarea(attrs={'rows':4}),
            'genres': forms.SelectMultiple(attrs={'size':6}),
            'tags': forms.SelectMultiple(attrs={'size':6}),
        }


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['content']


class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['score']
        widgets = {
            'score': forms.NumberInput(attrs={'min': 1, 'max': 10})
        }
