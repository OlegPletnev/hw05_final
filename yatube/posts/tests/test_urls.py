from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()

INDEX = reverse('posts:index')
CREATE = reverse('posts:post_create')
FOLLOW_INDEX = reverse('posts:follow_index')
SLUG = 'test_slug'
USER1 = 'Author'
USER2 = 'HasNoName'
GROUP = reverse('posts:group_list', kwargs={'slug': SLUG})
PROFILE = reverse('posts:profile', kwargs={'username': USER2})
FOLLOW = reverse('posts:profile_follow', kwargs={'username': USER1})
UNFOLLOW = reverse('posts:profile_unfollow', kwargs={'username': USER1})
AUTHOR = reverse('about:author')
TECH = reverse('about:tech')
LOGIN = reverse('users:login')


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=USER1)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug=SLUG,
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая группа',
        )

        cls.EDIT = f'/posts/{cls.post.id}/edit/'
        cls.POST = reverse(
            'posts:post_detail', kwargs={'post_id': cls.post.id}
        )
        cls.COMMENT = reverse(
            'posts:add_comment', kwargs={'post_id': cls.post.id}
        )

    def setUp(self):
        self.guest_client = Client()
        self.user_simple = User.objects.create_user(username=USER2)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_simple)
        self.client_author = Client()
        self.client_author.force_login(PostURLTests.user)

    def test_urls_uses_correct_template(self):
        templates_url_names = {
            INDEX: 'posts/index.html',
            GROUP: 'posts/group_list.html',
            PROFILE: 'posts/profile.html',
            self.POST: 'posts/post_detail.html',
            self.EDIT: 'posts/create_post.html',
            CREATE: 'posts/create_post.html',
            FOLLOW_INDEX: 'posts/follow.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(adress=address):
                response = self.client_author.get(address)
                self.assertTemplateUsed(response, template)

    def test_about_url_exists_at_desired_location(self):
        url_names = [INDEX, GROUP, PROFILE, self.POST, FOLLOW_INDEX]
        for address in url_names:
            with self.subTest(adress=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unexisting_page(self):
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_getability_edit_post(self):
        response = self.client_author.get(self.EDIT)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_getability_create_post(self):
        response = self.authorized_client.get(CREATE)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_redirect_guest_from_edit_post(self):
        response = self.guest_client.get(self.EDIT, follow=True)
        self.assertRedirects(
            response, f'{LOGIN}?next={self.EDIT}'
        )

    def test_redirect_authorized_client_from_edit_post(self):
        response = self.authorized_client.get(
            self.EDIT, follow=True
        )
        self.assertRedirects(response, self.POST)

    def test_redirect_guest_from_create_post(self):
        response = self.guest_client.get(CREATE)
        self.assertRedirects(response, f'{LOGIN}?next={CREATE}')


class StaticURLTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_static_urls(self):
        static_urls = [INDEX, AUTHOR, TECH]
        for address in static_urls:
            with self.subTest(adress=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)
