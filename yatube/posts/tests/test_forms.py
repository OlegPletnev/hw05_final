import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.forms import PostForm
from posts.models import Post, Group, Comment

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()

LOGIN = reverse('users:login')
CREATE = reverse('posts:post_create')


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост 0',
            group=cls.group,
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostCreateFormTests.user)

    def test_create_post(self):
        """Валидная форма создает запись в БД."""
        # Подсчитаем количество записей в Task
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый пост 1',
            'author': self.user,
            'group': self.group.id,
            'image': uploaded,
        }

        response = self.authorized_client.post(
            CREATE,
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        # Проверяем, сработал ли редирект
        self.assertRedirects(response, reverse(
            'posts:profile',
            kwargs={'username': PostCreateFormTests.user.username}))
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), posts_count + 1)
        # Проверяем,
        # что создалась запись при отправке поста с картинкой через форму
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый пост 1',
                group=PostCreateFormTests.group.id,
                image='posts/small.gif',
            ).exists()
        )
        # проверяют, что при выводе поста с картинкой изображение передаётся
        # в словаре context на следующие urls:
        urls = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': 'test_slug'}),
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}),
            reverse('posts:profile', kwargs={'username': 'Author'}),
        ]
        for url in urls:
            response = self.authorized_client.get(url)
            self.assertContains(response, '<img')

    def test_edit_post(self):
        """Валидная форма изменяет пост в БД."""
        post_id = PostCreateFormTests.post.id
        form_data = {
            'text': 'Редакция поста с новым текстом',
            'group': PostCreateFormTests.group.id,
            'author': PostCreateFormTests.user.id,
        }

        response = self.authorized_client.post(
            reverse('posts:post_edit', args=(post_id,)),
            data=form_data,
            follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(response,
                             reverse('posts:post_detail', args=(post_id,)))
        obj = Post.objects.get(id=post_id)
        self.assertEqual(obj.text, form_data['text'])
        self.assertEqual(obj.author.id, form_data['author'])
        self.assertEqual(obj.group.id, form_data['group'])

    def test_guest_client_cant_create_post(self):
        """Гость не может опубликовать пост
        его редиректит на страницу логина"""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый пост гостя',
            'group': PostCreateFormTests.group.id,
        }
        response = self.client.post(
            CREATE,
            data=form_data,
            follow=True
        )

        self.assertEqual(Post.objects.count(), posts_count)
        self.assertRedirects(response, LOGIN + '?next=' + CREATE,
                             status_code=302, target_status_code=200)

    def test_create_comment(self):
        """Проверка формы создания нового комментария."""
        url_post = reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}
        )
        url_comment = reverse(
            'posts:add_comment', kwargs={'post_id': self.post.pk}
        )
        comments_count = Comment.objects.filter(post=self.post.pk).count()
        form_data = {'text': 'test_comment'}

        response = self.authorized_client.post(
            url_comment,
            data=form_data,
            follow=True
        )
        comments = (Post.objects.filter(id=self.post.pk)
                    .values_list('comments', flat=True))
        # После успешного создания комментария авторизованным пользователем
        # проверяем редирект и увеличение кол-ва постов на странице
        self.assertRedirects(response, url_post)
        self.assertEqual(comments.count(), comments_count + 1)
        self.assertTrue(
            Comment.objects.filter(
                post=self.post.pk,
                author=self.user.pk,
                text=form_data['text']
            ).exists()
        )
        # Пробуем создать комментарий неавторизованным пользователем
        response = self.client.post(
            url_comment,
            data=form_data,
            follow=True
        )
        # Комментарий не добавлен - текущее их количество не изменилось
        self.assertEqual(comments.count(), comments_count + 1)
        # Пользователь отправлен на страницу логина
        self.assertRedirects(response, LOGIN + '?next=' + url_comment,
                             status_code=302, target_status_code=200)
