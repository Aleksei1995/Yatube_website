import shutil
import tempfile
import time

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.core.cache import cache

from posts.models import Group, Post, Follow
from ..views import MAX_POSTS
from http import HTTPStatus

User = get_user_model()


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        settings.MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

        cls.user = User.objects.create_user(username='user_name')

        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

        cls.post = Post.objects.create(
            text='Тестовая группа',
            author=cls.user,
        )

        # Создано для тестов "Дополнительная проверка при создании поста"
        time.sleep(0.01)

        cls.new_group = Group.objects.create(
            title='Новая тестовая группа',
            slug='test',
            description='Тестовое описание',
        )

        cls.new_post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.new_group
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.get(id=1)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': 'test-slug'}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': self.user.username}):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': 1}):
                'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': 1}):
                'posts/create_post.html'
        }

        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон title сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        post = PostPagesTests.post
        title = response.context['title']
        first_object = response.context['page_obj'][0]
        post_text_0 = first_object.text
        post_image = first_object.image
        self.assertEqual(title, 'Последние обновления на сайте')
        self.assertEqual(post_text_0, self.new_post.text)
        self.assertEqual(post_image, post.image)

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:group_list',
                                              kwargs={'slug': 'test'}))
        group = response.context.get('group').slug
        post = PostPagesTests.post
        post_count = len(response.context['page_obj'])
        first_object = response.context['page_obj'][0]
        post_text_0 = first_object.text
        post_image = first_object.image
        self.assertEqual(group, 'test')
        self.assertEqual(post_text_0, self.new_post.text)
        self.assertEqual(post_image, post.image)
        self.assertEqual(post_count, 1)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:profile',
                                              kwargs={'username':
                                                      self.user.username}))
        post = PostPagesTests.post
        author = response.context.get('user').id
        post_count = response.context['post_count']
        first_object = response.context['page_obj'][0]
        post_text_0 = first_object.text
        post_image = first_object.image
        self.assertEqual(author, 1)
        self.assertEqual(post_count, 2)
        self.assertEqual(post_text_0, self.new_post.text)
        self.assertEqual(post_image, post.image)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_detail',
                                              kwargs={'post_id': '1'}))
        post = PostPagesTests.post
        posts = response.context.get('post').id
        author = response.context['user']
        post_count = response.context['post_count']
        text = response.context['post'].text
        post_image = response.context['post'].image
        self.assertEqual(posts, 1)
        self.assertEqual(author, User.objects.get(id=1))
        self.assertEqual(post_count, 2)
        self.assertEqual(text, self.post.text)
        self.assertEqual(post_image, post.image)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_edit',
                                              kwargs={'post_id': '1'}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_create_post_page_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cache.clear()

        cls.user = User.objects.create_user(username='user_name')

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

        for i in range(13):
            cls.post = Post.objects.create(
                text='Тестовый пост',
                author=cls.user,
                group=cls.group
            )

        cls.templates = [
            reverse('posts:index'),
            reverse('posts:group_list', args=[cls.group.slug]),
            reverse('posts:profile', args=[cls.user.username])
        ]

    def test_first_page_contains_ten_records(self):
        # Проверка: количество постов на первой странице равно 10.
        for i in PaginatorViewsTest.templates:
            response = self.client.get(i)
            self.assertEqual(len(response.context['page_obj']), MAX_POSTS)

    def test_second_page_contains_three_records(self):
        # Проверка: на второй странице должно быть три поста.
        for i in PaginatorViewsTest.templates:
            response = self.client.get((i) + '?page=2')
            self.assertEqual(len(response.context['page_obj']), 3)


class CacheViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.author = User.objects.create_user(username='test_user')

        cls.group = Group.objects.create(
            title='test_group',
            slug='test-slug',
            description='test_description'
        )
        cls.post = Post.objects.create(
            text='test_post',
            group=cls.group,
            author=cls.author
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)
        cache.clear()

    def test_cache_index(self):
        """Проверка кэша для index."""
        response = self.authorized_client.get(reverse('posts:index'))
        Post.objects.all().delete()
        self.assertContains(response, self.post.text)
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertNotContains(response, self.post.text)

    def test_cache(self):
        """Проверка, что до сброса кэша страница та же, что до изменения"""
        # Кажется, что не понял задание, прошу пояснить
        response = self.authorized_client.get(reverse('posts:index'))
        content = response.content
        Post.objects.create(
            text='test_cash',
            group=self.group,
            author=self.author
        )
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response.content, content)
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(response.content, content)


class FollowViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create_user(username='test_user')

        cls.author = User.objects.create_user(username='test_author')

        for i in range(13):
            cls.post = Post.objects.create(
                text='post_text',
                author=cls.author,
            )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_authorized_client_can_follow(self):
        # Проверка, что авторизованный пользователь может
        # подписываться на других пользователей.
        self.assertFalse(Follow.objects.filter(user=self.user,
                                               author=self.author,).exists())
        response = self.authorized_client.get(reverse('posts:profile_follow',
                                              kwargs={'username':
                                                      self.author.username}))
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertTrue(Follow.objects.filter(user=self.user,
                                              author=self.author,).exists())

    def test_authorized_client_can_unfollow(self):
        # Проверка, что авторизованный пользователь может
        # отписываться от других пользователей.
        Follow.objects.create(user=self.user, author=self.author)
        self.assertTrue(Follow.objects.filter(user=self.user,
                                              author=self.author,).exists())
        response = self.authorized_client.get(reverse('posts:profile_unfollow',
                                              kwargs={'username':
                                                      self.author.username}))
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertFalse(Follow.objects.filter(user=self.user,
                                               author=self.author,).exists())

    def test_follow_index_follower_follow(self):
        # Проверка, что записи пользователя появляются в ленте тех,
        # кто на него подписан.
        self.authorized_client.get(reverse('posts:profile_follow',
                                           kwargs={'username':
                                                   self.author.username}))
        response = self.authorized_client.get(reverse('posts:follow_index'))
        post_count = response.context['post_count']
        first_object = response.context['page_obj'][0]
        post_text = first_object.text
        self.assertEqual(post_count, 13)
        self.assertEqual(post_text, self.post.text)

    def test_follow_index_follower_unfollow(self):
        # Проверка, что записи пользователя не появляются в ленте тех,
        # кто на него не подписан.
        self.authorized_client.get(reverse('posts:profile_unfollow',
                                           kwargs={'username':
                                                   self.author.username}))
        response = self.authorized_client.get(reverse('posts:follow_index'))
        post_count = response.context['post_count']
        self.assertEqual(post_count, 0)
