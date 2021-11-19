from django import forms
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, Client
from django.urls import reverse

from yatube.settings import POSTS_PER_PAGE
from ..models import Group, Post, Follow

User = get_user_model()

SLUG = 'test_slug'
SLUG2 = 'test_slug_2'
USER = 'Author'

INDEX = reverse('posts:index')
CREATE = reverse('posts:post_create')
GROUP = reverse('posts:group_list', kwargs={'slug': SLUG})
PROFILE = reverse('posts:profile', kwargs={'username': USER})
AUTHOR = reverse('about:author')
TECH = reverse('about:tech')
FOLLOW_INDEX = reverse('posts:follow_index')
FOLLOW = reverse('posts:profile_follow', kwargs={'username': USER})
UNFOLLOW = reverse('posts:profile_unfollow', kwargs={'username': USER})

ALL_POSTS = 13


class PostViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=USER)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug=SLUG,
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Текст 1',
            group=cls.group
        )
        cls.EDIT = f'/posts/{cls.post.id}/edit/'
        cls.POST = reverse(
            'posts:post_detail', kwargs={'post_id': cls.post.id}
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostViewsTests.user)
        self.user2 = User.objects.create(username='Follower')
        self.authorized_client2 = Client()
        self.authorized_client2.force_login(self.user2)

    def test_pages_uses_correct_template(self):
        """ Задание 1: тесты, проверяющие,
        что во view-функциях используются правильные html-шаблоны.
        """
        templates_pages_names = {
            INDEX: 'posts/index.html',
            GROUP: 'posts/group_list.html',
            PROFILE: 'posts/profile.html',
            self.POST: 'posts/post_detail.html',
            self.EDIT: 'posts/create_post.html',
            CREATE: 'posts/create_post.html',
        }
        # Проверяем, что при обращении к name вызывается нужный HTML-шаблон
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    # ================== Задание 2: проверка контекста ======================
    def checking_for_correct_context(self, obj):
        self.assertEqual(obj.id, self.post.id)
        self.assertEqual(obj.text, self.post.text)
        self.assertEqual(obj.author, self.post.author)
        self.assertEqual(obj.pub_date, self.post.pub_date)

    def test_index_pages_show_correct_context(self):
        """Контекст главной страницы."""
        response = self.authorized_client.get(INDEX)
        first_object = response.context['page_obj'][0]
        self.checking_for_correct_context(first_object)

    def test_group_pages_show_correct_context(self):
        """Контекст списка постов одной группы."""
        response = self.authorized_client.get(GROUP)
        first_object = response.context['page_obj'][0]
        self.checking_for_correct_context(first_object)

    def test_profile_pages_show_correct_context(self):
        """Контекст списка постов одного автора."""
        response = self.authorized_client.get(PROFILE)
        first_object = response.context['page_obj'][0]
        self.checking_for_correct_context(first_object)

    def test_detail_pages_show_correct_context(self):
        """Контекст шаблона post_detail."""
        response = (self.authorized_client.
                    get(self.POST))
        self.checking_for_correct_context(response.context.get('post'))

    def test_create_post_show_correct_context(self):
        """Контекст формы создания и редактирования поста."""
        response = self.authorized_client.get(CREATE)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    # ===================== Задание 3 =====================================
    def test_pages_for_new_post(self):
        cache.clear()
        """
        Проверяем, что при создании поста с группой, этот пост появляется
        - на главной странице сайта,
        - на странице выбранной группы,
        - в профайле пользователя.
        """
        self.group_2 = Group.objects.create(
            title='Тестовая группа 2',
            slug=SLUG2,
            description='Тестовое описание 2',
        )
        self.post_2 = Post.objects.create(
            author=PostViewsTests.user,
            text='Текст 2',
            group=self.group_2
        )
        verify_urls = (
            INDEX,
            reverse('posts:group_list', kwargs={'slug': SLUG2}),
            PROFILE,
        )
        for url in verify_urls:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertContains(response, self.post_2.text)

        # Провеяем, что этот пост не попал в другую группу (меняем слаг)
        response = self.authorized_client.get(GROUP)
        self.assertNotIn(
            self.post_2, response.context.get('page_obj').object_list
        )

    def test_cache_index(self):
        """
        Проверка хранения и очищения кэша для index.
        """
        response_0 = self.authorized_client.get(INDEX)
        posts_0 = response_0.content
        Post.objects.first().delete()

        response_1 = self.authorized_client.get(INDEX)
        posts_1 = response_1.content
        self.assertEqual(
            posts_0,
            posts_1,
            'Кэширование не работает или отключено'
        )
        cache.clear()
        response_1 = self.authorized_client.get(INDEX)
        posts_1 = response_1.content
        self.assertNotEqual(
            posts_0, posts_1, 'Некэшированная страница не обновляется'
        )


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=USER)
        posts = [Post(author=cls.user, text=f'Пост №{i}') for i in
                 range(ALL_POSTS)]
        Post.objects.bulk_create(posts)

    def test_first_page_contains_ten_records(self):
        response = self.client.get(INDEX)
        self.assertEqual(
            len(response.context.get('page_obj').object_list),
            POSTS_PER_PAGE
        )

    def test_second_page_contains_three_records(self):
        response = self.client.get(INDEX + '?page=2')
        self.assertEqual(
            len(response.context['page_obj']),
            ALL_POSTS - POSTS_PER_PAGE
        )


class FollowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.follower = User.objects.create_user(username='Подписчик')
        cls.following_1 = User.objects.create_user(username=USER)
        cls.follow = Follow.objects.create(author=cls.following_1,
                                           user=cls.follower)
        cls.post = Post.objects.create(
            author=cls.following_1,
            text='Какой-то текст',
        )
        cls.follower_2 = User.objects.create_user(username='Подписчик 2')

    def setUp(self):
        self.guest_client = Client()
        self.follower_1 = Client()
        self.follower_1.force_login(FollowTests.follower)
        self.authorized_client_2 = Client()
        self.authorized_client_2.force_login(FollowTests.follower_2)

    def test_auth_user_follow(self):
        """
        Авторизованный пользователь может подписываться
        на других пользователей.
        """
        self.follower_1.get(FOLLOW)
        follow_exist = Follow.objects.filter(user=self.follower,
                                             author=self.following_1).exists()
        self.assertTrue(follow_exist)

    def test_auth_user_unfollow(self):
        """
        Авторизованный пользователь может удалять
        других пользователей из подписки.
        """
        self.follower_1.get(FOLLOW)
        self.follower_1.get(UNFOLLOW)
        follow_exist = Follow.objects.filter(user=self.follower,
                                             author=self.following_1).exists()
        self.assertFalse(follow_exist)

    def test_follow_index(self):
        """
        Новая запись пользователя появляется в ленте тех,
        кто на него подписан и не появляется в ленте тех,
        кто не подписан на него
        """
        self.follower_1.get(FOLLOW)
        response = self.follower_1.get(FOLLOW_INDEX)
        self.assertEqual(len(response.context['page_obj']), 1)

        response = self.authorized_client_2.get(FOLLOW_INDEX)
        self.assertEqual(len(response.context['page_obj']), 0)

        FollowTests.post = Post.objects.create(
            author=FollowTests.following_1,
            text='Другой какой-то текст',
        )

        response = self.follower_1.get(FOLLOW_INDEX)
        self.assertEqual(len(response.context['page_obj']), 2)

        response = self.authorized_client_2.get(FOLLOW_INDEX)
        self.assertEqual(len(response.context['page_obj']), 0)
