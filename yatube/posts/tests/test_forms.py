import shutil
import tempfile

from http import HTTPStatus

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.forms import PostForm
from posts.models import Comment, Group, Post, User
from posts.tests import constants as cs

POST_TEXT_OLD = 'First check'
POST_TEXT_NEW = 'Second check'
POST_USER = 'author'
POST_TEXT = 'Test post'
GROUP_TITLE = 'Test group'
GROUP_SLUG = 'slug1'
GROUP_DESCRIPTION = 'Test description'

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
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
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.author_client = Client()
        self.author_client.force_login(self.author)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_create_post(self):
        """Валидная форма создает пост в Post."""
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
            'text': POST_TEXT_OLD,
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.author_client.post(
            reverse(cs.POST_CREATE_URL),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, reverse(
                cs.PROFILE_URL, kwargs={'username': self.post.author.username}
            )
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.text, POST_TEXT_OLD)
        self.assertEqual(first_object.group, self.group)
        self.assertEqual(first_object.author, self.author)
        self.assertEqual(first_object.image, 'posts/small.gif')

    def test_edit_post(self):
        """Валидная форма редактирует пост в Post."""
        form_data = {
            'text': POST_TEXT_NEW,
            'group': self.group.id,
        }
        response = self.author_client.post(
            reverse(cs.POST_EDIT_URL, kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        update_object = response.context['post']
        self.assertEqual(update_object.text, POST_TEXT_NEW)
        self.assertEqual(update_object.group, self.group)
        self.assertEqual(update_object.author, self.author)

    def test_make_comment(self):
        '''Комментировать посты может только авторизованный пользователь,
        После успешной отправки комментарий появляется на странице поста'''
        form_data = {
            'text': 'Новый комментарий'
        }
        self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertTrue(Comment.objects.filter(
            text='Новый комментарий',
        ).exists())

        form_data_2 = {
            'text': 'Комментарий которого нет'
        }
        self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data_2,
            follow=True,
        )
        self.assertFalse(Comment.objects.filter(
            text='Комментарий которого нет'
        ).exists())
