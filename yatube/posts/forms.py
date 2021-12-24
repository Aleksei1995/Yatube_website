from django import forms
from django.utils.safestring import mark_safe

from .models import Post, Group, Comment


class PostForm(forms.ModelForm):
    text = forms.CharField(label='Текст поста',
                           max_length=200, widget=forms.Textarea,
                           help_text=mark_safe
                           ("Пожалуйста, введите полный текст поста."))
    group = forms.ModelChoiceField(label='Группа',
                                   queryset=Group.objects.all(),
                                   required=False,
                                   help_text=mark_safe
                                   ("Пожалуйста, выберите группу."))

    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        help_texts = {'text': 'My help_text',
                      'group': 'My help_text for group'}


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
