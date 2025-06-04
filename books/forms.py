from django import forms
from .models import Book, Review, Cover
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div, HTML
from crispy_forms.bootstrap import TabHolder, Tab, FormActions
from django.utils import timezone

class BookForm(forms.ModelForm):
    published_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local'},
            format='%Y-%m-%dT%H:%M'
        ),
        input_formats=['%Y-%m-%dT%H:%M']
    )
    discount_start = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local'},
            format='%Y-%m-%dT%H:%M'
        ),
        input_formats=['%Y-%m-%dT%H:%M']
    )
    discount_end = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local'},
            format='%Y-%m-%dT%H:%M'
        ),
        input_formats=['%Y-%m-%dT%H:%M']
    )

    class Meta:
        model = Book
        fields = [
            'title', 'author', 'description', 'price', 'status',
            'has_discount', 'discount_percent', 'discount_start', 'discount_end',
            'ebook_file', 'published_at'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = True
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        
        # Устанавливаем начальные значения для полей даты
        if self.instance and self.instance.pk:
            if self.instance.published_at:
                self.initial['published_at'] = self.instance.published_at.strftime('%Y-%m-%dT%H:%M')
            if self.instance.discount_start:
                self.initial['discount_start'] = self.instance.discount_start.strftime('%Y-%m-%dT%H:%M')
            if self.instance.discount_end:
                self.initial['discount_end'] = self.instance.discount_end.strftime('%Y-%m-%dT%H:%M')
        
        self.helper.layout = Layout(
            TabHolder(
                Tab('Основная информация',
                    'title',
                    'author',
                    'description',
                    'price',
                    'status',
                    'published_at',
                ),
                Tab('Скидки',
                    'has_discount',
                    'discount_percent',
                    'discount_start',
                    'discount_end',
                ),
                Tab('Файлы',
                    'ebook_file',
                ),
            ),
            FormActions(
                Submit('submit', 'Сохранить', css_class='btn btn-primary'),
                HTML('<a href="{% url "admin:books_book_changelist" %}" class="btn btn-secondary">Отмена</a>'),
            )
        )

class CoverForm(forms.ModelForm):
    class Meta:
        model = Cover
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={'accept': 'image/*'})
        }

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 4}),
        } 