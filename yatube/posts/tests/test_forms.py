import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from posts.models import Group, Post, Comment
from posts.forms import PostForm, CommentForm

User = get_user_model()


class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        settings.MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
        super().setUpClass()

        cls.author = User.objects.create_user(username='author')

        cls.small_gif_1 = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )

        cls.small_gif_new = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )

        cls.uploaded_1 = SimpleUploadedFile(
            name='small_1.gif',
            content=cls.small_gif_1,
            content_type='image/gif'
        )

        cls.uploaded_new = SimpleUploadedFile(
            name='small_new.gif',
            content=cls.small_gif_new,
            content_type='image/gif'
        )

        cls.group_first = Group.objects.create(
            title='Тестовая группа 1',
            slug='test-slug-first',
            description='Тестовое описание'
        )
        cls.group_second = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug-second',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            text='text_post',
            author=cls.author,
            group=cls.group_first
        )

        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.author)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        group_field = self.group_first.id
        form_data = {
            'text': self.post.text,
            'group': group_field,
            'image': self.uploaded_1
        }
        response = self.author_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        self.assertRedirects(response, reverse('posts:profile',
                                               args=[self.author.username]))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text=self.post.text,
                group=self.group_first.id,
                image='posts/small_1.gif'
            ).exists()
        )

    def test_edit_post(self):
        """Проверка формы редактирования поста и изменение
        его в базе данных."""
        group_field_second = self.group_second.id
        form_data = {
            'text': self.post.text,
            'group': group_field_second,
            'image': self.uploaded_new
        }
        response = self.author_client.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.pk}
            ),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.pk}
            )
        )
        self.assertTrue(
            Post.objects.filter(
                group=self.group_second.pk,
                text=self.post.text,
                image='posts/small_new.gif'
            ).exists()
        )
        self.assertFalse(
            Post.objects.filter(
                group=self.group_first.pk,
                text=self.post.text,
                image='posts/small_1.gif'
            ).exists()
        )


class CommentFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.author = User.objects.create_user(username='author')

        cls.post = Post.objects.create(
            text='text_post',
            author=cls.author,
        )

        cls.comment = Comment.objects.create(
            text='text_comment',
            post=cls.post,
            author=cls.author,
        )

        cls.form = CommentForm()

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)
        self.guest_client = Client()

    def test_create_comment(self):
        """Валидная форма создает запись в Comment."""
        comments_count = Comment.objects.count()
        form_data = {
            'text': self.comment,
        }
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': self.post.pk}
            ),
            data=form_data,
            follow=True
        )

        self.assertRedirects(response, reverse('posts:post_detail',
                                               args=[self.post.pk]))
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(
            Comment.objects.filter(
                text=self.comment,
            ).exists()
        )

    def test_anonymous_cant_create_comment(self):
        comments_count = Comment.objects.count()
        form_data = {
            'text': self.comment,
        }
        self.guest_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': self.post.pk}
            ),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count)
