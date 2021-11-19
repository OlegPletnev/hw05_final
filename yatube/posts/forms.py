from django.forms import ModelForm

from .models import Post, Comment


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ['group', 'text', 'image']
        help_texts = {
            'text': 'Заполните поле красивой умной фразой...',
            'group': 'Выберите из списка (необязательно)'
        }


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
