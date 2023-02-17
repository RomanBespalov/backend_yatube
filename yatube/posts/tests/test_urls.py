from http import HTTPStatus

from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post, User
from posts.tests import constants as cs


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.post = Post.objects.create(
            author=cls.author,
            text='Test post',
        )
        cls.group = Group.objects.create(
            title='Test group',
            slug='slug1',
            description='Test description',
        )

        cls.guest_client = Client()
        cls.user = User.objects.create_user(username='HasNoName')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.author_client = Client()
        cls.author_client.force_login(cls.author)

        cls.public_urls = (
            (cs.INDEX_URL, None, cs.INDEX_TEMPLATE, HTTPStatus.OK),
            (cs.GROUP_URL, {'slug': cls.group.slug},
             cs.GROUP_TEMPLATE, HTTPStatus.OK),
            (cs.PROFILE_URL, {'username': cls.author},
             cs.PROFILE_TEMPLATE, HTTPStatus.OK),
            (cs.POST_DETAIL_URL, {'post_id': cls.post.id},
             cs.POST_DETAIL_TEMPLATE, HTTPStatus.OK),
        )

        cls.private_urls = (
            (cs.POST_CREATE_URL, None,
             cs.POST_CREATE_TEMPLATE, HTTPStatus.OK),
            (cs.POST_EDIT_URL, {'post_id': cls.post.id},
             cs.POST_EDIT_TEMPLATE, HTTPStatus.OK),
        )

    def setUp(self):
        cache.clear()

    def test_url_templates(self):
        """Шаблоны соответствуют URL."""
        for url, params, template, _ in self.public_urls:
            with self.subTest(url=url):
                response = self.guest_client.get(reverse(url, kwargs=params))
                with self.subTest(url=url):
                    self.assertTemplateUsed(response, template)

        for url, params, template, _ in self.private_urls:
            with self.subTest(url=url):
                response = self.author_client.get(reverse(url, kwargs=params))
                with self.subTest(url=url):
                    self.assertTemplateUsed(response, template)

    def test_url_access(self):
        """Страницы доступны пользователям."""
        for url, params, _, expected_status in self.public_urls:
            response = self.guest_client.get(
                reverse(url, kwargs=params)
            )
            with self.subTest(url=url):
                self.assertEqual(
                    response.status_code, expected_status
                )

        for url, params, _, expected_status in self.private_urls:
            response = self.author_client.get(
                reverse(url, kwargs=params)
            )
            with self.subTest(url=url):
                self.assertEqual(
                    response.status_code, expected_status
                )

    def test_unexisting_page_redirect_anonymous(self):
        """Несуществующая страница возвращает ошибку 404 всем пользователям."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_page_404_error_call_for_template(self):
        """Несуществующая страница возвращает ошибку 404 всем пользователям."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertTemplateUsed(response, 'core/404.html')

    def test_post_create_redirect_anonymous(self):
        """Страница /create/ перенаправляет анонимного пользователя."""
        response = self.guest_client.get(
            reverse(cs.POST_CREATE_URL), follow=True
        )
        self.assertRedirects(response, ('/auth/login/?next=/create/'))

    def test_post_edit_redirect_not_author(self):
        """Страница /posts/<int:post_id>/edit/ перенаправляет не автора."""
        response = self.authorized_client.get(
            reverse(
                cs.POST_EDIT_URL, kwargs={'post_id': self.post.id}
            ), follow=True
        )
        self.assertRedirects(
            response, reverse(
                cs.POST_DETAIL_URL, kwargs={'post_id': self.post.id}
            )
        )

    def test_check_work_cache(self):
        """Проверка работы кэша на главной странице."""
        response_1 = self.guest_client.get(reverse(cs.INDEX_URL))
        Post.objects.create(
            author=self.author,
            text='Test post',
        )
        response_2 = self.guest_client.get(reverse(cs.INDEX_URL))
        self.assertEqual(response_1.content, response_2.content)
        cache.clear()
        response_3 = self.guest_client.get(reverse(cs.INDEX_URL))
        self.assertNotEqual(response_1.content, response_3.content)
