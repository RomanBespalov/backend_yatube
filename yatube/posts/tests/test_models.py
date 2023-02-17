from django.test import TestCase

from posts.models import Group, Post, User


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        post = PostModelTest.post
        group = PostModelTest.group
        field_strings = {
            post.text[:15]: str(post),
            group.title: str(group),
        }
        for field, expected_value in field_strings.items():
            with self.subTest(field=field):
                self.assertEqual(field, expected_value)

    def test_models_have_correct_verbose_name_and_help_text(self):
        """Проверяем, что у моделей корректно
        работает verbose_name и help_text."""
        post = PostModelTest.post
        fields_verboses = {
            'text': 'текст',
            'group': 'название группы',
        }
        for field, expected_value in fields_verboses.items():
            with self.subTest(field=field):
                self.assertEqual(
                    post._meta.get_field(field).verbose_name, expected_value
                )

        fields_help = {
            'text': 'Укажите текст поста',
            'group': 'Укажите группу',
        }
        for field, expected_value in fields_help.items():
            with self.subTest(field=field):
                self.assertEqual(
                    post._meta.get_field(field).help_text, expected_value
                )
