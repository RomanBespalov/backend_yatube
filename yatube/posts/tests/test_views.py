from http import HTTPStatus

import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.paginator import Page
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Group, Post, User, Follow
from posts.tests import constants as cs
from posts.forms import PostForm

POSTS_PER_PAGE = 10
POSTS_SECOND_PAGE = 1

AUTHOR_USERNAME = 'TestAuthor'
USER_USERNAME = 'TestUser'
GROUP_TITLE = 'Тестовая группа'
GROUP_SLUG = 'test-slug'
GROUP_DESCRIPTION = 'Тестовое описание'
POST_TEXT = 'Тестовый текст'

PAG_INDEX_URL = reverse('posts:index')
PAG_GROUP_LIST_URL = reverse('posts:group_list', args=[GROUP_SLUG])
PAG_PROFILE_URL = reverse('posts:profile', args=[AUTHOR_USERNAME])

POST_TEXT_OLD = 'First check'
POST_TEXT_NEW = 'Second check'
POST_USER = 'author_2'


class PostsViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username=AUTHOR_USERNAME)
        cls.post = Post.objects.create(
            author=cls.author,
            text=POST_TEXT,
        )
        cls.group = Group.objects.create(
            title=GROUP_TITLE,
            slug=GROUP_SLUG,
            description=GROUP_DESCRIPTION,
        )

    def setUp(self):
        self.user = User.objects.create_user(username=USER_USERNAME)
        self.author_client = Client()
        self.author_client.force_login(self.author)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            cs.INDEX_TEMPLATE: reverse(cs.INDEX_URL),
            cs.GROUP_TEMPLATE: (
                reverse(cs.GROUP_URL, kwargs={'slug': self.group.slug})
            ),
            cs.PROFILE_TEMPLATE: (
                reverse(cs.PROFILE_URL, kwargs={'username': self.author})
            ),
            cs.POST_DETAIL_TEMPLATE: (
                reverse(cs.POST_DETAIL_URL, kwargs={'post_id': self.post.id})
            ),
            cs.POST_CREATE_TEMPLATE: reverse(cs.POST_CREATE_URL),
            cs.POST_EDIT_TEMPLATE: (
                reverse(cs.POST_EDIT_URL, kwargs={'post_id': self.post.id})
            ),
        }

        for template, reverse_name in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.author_client.get(reverse_name)
                self.assertTemplateUsed(response, template)


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username=AUTHOR_USERNAME)
        cls.post = Post.objects.create(
            author=cls.author,
            text=POST_TEXT,
        )
        cls.group = Group.objects.create(
            title=GROUP_TITLE,
            slug=GROUP_SLUG,
            description=GROUP_DESCRIPTION,
        )

    def setUp(self):
        self.user = User.objects.create_user(username=USER_USERNAME)
        self.author_client = Client()
        self.author_client.force_login(self.user)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_post_create_page_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.author_client.get(reverse(cs.POST_CREATE_URL))
        self.assertIsInstance(response.context.get('form'), PostForm)

    def test_post_detail_pages_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = (self.author_client.get(
            reverse(cs.POST_DETAIL_URL, kwargs={'post_id': self.post.id}))
        )
        self.assertEqual(response.context.get('post').text, self.post.text)
        self.assertEqual(
            response.context.get('post').author, self.post.author
        )
        self.assertEqual(
            response.context.get('post').group, self.post.group
        )


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username=AUTHOR_USERNAME)
        cls.group = Group.objects.create(
            title=GROUP_TITLE,
            slug=GROUP_SLUG,
            description=GROUP_DESCRIPTION,
        )
        Post.objects.bulk_create([
            Post(
                text=f'{POST_TEXT} {i}', author=cls.author, group=cls.group
            ) for i in range(POSTS_PER_PAGE + POSTS_SECOND_PAGE)
        ])

    def setUp(self):
        self.user = User.objects.create_user(username=USER_USERNAME)
        self.author_client = Client()
        self.author_client.force_login(self.user)

    def test_paginator(self):
        '''Проверка работы Пагинатора'''
        mount_of_posts_on_the_first_page = POSTS_PER_PAGE
        mount_of_posts_on_the_second_page = POSTS_SECOND_PAGE

        pages = (
            (1, mount_of_posts_on_the_first_page),
            (2, mount_of_posts_on_the_second_page),
        )

        urls_expected_post_number = (
            PAG_INDEX_URL,
            PAG_GROUP_LIST_URL,
            PAG_PROFILE_URL,
        )

        for url in urls_expected_post_number:
            for page, mount in pages:
                with self.subTest(url=url, page=page):
                    response = self.author_client.get(url, {'page': page})
                    page_obj = response.context.get('page_obj')
                    self.assertEqual(response.status_code, HTTPStatus.OK)
                    self.assertIsNotNone(page_obj)
                    self.assertIsInstance(page_obj, Page)
                    self.assertEqual(len(page_obj.object_list), mount)


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PictureTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username=POST_USER)
        cls.post = Post.objects.create(
            author=cls.author,
            text=POST_TEXT,
        )
        cls.group = Group.objects.create(
            title=GROUP_TITLE,
            slug=GROUP_SLUG,
            description=GROUP_DESCRIPTION,
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.author)

    def test_create_picture_post(self):
        """Валидная форма создает пост в Post.
        После этого идет проверка, что картинка существует на страницах."""
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
            'text': POST_TEXT_OLD,
            'group': self.group.id,
            'image': uploaded,
        }
        self.author_client.post(
            reverse(cs.POST_CREATE_URL),
            data=form_data,
            follow=True
        )
        post = Post.objects.get(pk=2)
        self.assertEqual(post.image, 'posts/small.gif')
        cache.clear()
        response_1 = self.author_client.get(reverse(cs.INDEX_URL))
        first_object = response_1.context['page_obj'].object_list[0].image
        self.assertEqual(first_object, 'posts/small.gif')

        response_2 = self.author_client.get(
            reverse(cs.PROFILE_URL, kwargs={'username': self.author})
        )
        second_object = response_2.context['page_obj'].object_list[0].image
        self.assertEqual(second_object, 'posts/small.gif')

        response_3 = self.author_client.get(
            reverse(cs.GROUP_URL, kwargs={'slug': self.group.slug})
        )
        third_object = response_3.context['page_obj'].object_list[0].image
        self.assertEqual(third_object, 'posts/small.gif')

        response_4 = self.author_client.get(
            reverse(cs.POST_DETAIL_URL, kwargs={'post_id': 2})
        )
        fourth_object = response_4.context.get('post').image
        self.assertEqual(fourth_object, 'posts/small.gif')


class ProfileFollowTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username=AUTHOR_USERNAME)
        cls.post = Post.objects.create(
            author=cls.author,
            text=POST_TEXT,
        )
        cls.group = Group.objects.create(
            title=GROUP_TITLE,
            slug=GROUP_SLUG,
            description=GROUP_DESCRIPTION,
        )

    def setUp(self):
        self.user = User.objects.create_user(username=USER_USERNAME)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_authorized_client_profile_follow_unfollow(self):
        """Авторизованный пользователь может подписываться
        на других пользователей и удалять их из подписок.
        Новая запись пользователя появляется в ленте тех,
        кто на него подписан и не появляется в ленте тех, кто не подписан."""
        response = self.authorized_client.get(
            reverse('posts:profile_follow', kwargs={'username': self.author})
        )
        self.assertRedirects(response, reverse('posts:follow_index'))
        subscriptions = Follow.objects.filter(user=self.user)
        author = [subscription.author for subscription in subscriptions]
        self.assertEqual(author, [self.author])
        response_1 = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertEqual(
            response_1.context.get('page_obj').object_list[0].text, POST_TEXT
        )

        follow = Follow.objects.get(user=self.user, author=self.author)
        follow.delete()
        assert follow not in Follow.objects.filter(user=self.user)
        response_2 = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertNotIn(
            POST_TEXT, response_2.context.get('page_obj').object_list
        )
