from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page

from .models import Group, Post, Follow
from .forms import PostForm, CommentForm

MAX_POSTS = 10


@cache_page(20)
def index(request):
    template = 'posts/index.html'
    posts = Post.objects.all()
    page_obj = paginator(request, posts)
    title = 'Последние обновления на сайте'
    context = {
        'posts': posts,
        'page_obj': page_obj,
        'title': title,
    }
    return render(request, template, context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    page_obj = paginator(request, posts)
    context = {
        'group': group,
        'posts': posts,
        'page_obj': page_obj,
    }
    template = 'posts/group_list.html'
    return render(request, template, context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    post_count = posts.count()
    following = False
    user = request.user
    if user.is_authenticated:
        if Follow.objects.filter(
            user=request.user,
            author=author,
        ).exists():
            following = True
    page_obj = paginator(request, posts)
    context = {
        'post_count': post_count,
        'posts': posts,
        'page_obj': page_obj,
        'author': author,
        'following': following,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    author = post.author
    post_count = Post.objects.filter(author=author).count()
    group = post.group
    form = CommentForm(request.POST)
    comments = post.comments.all()
    context = {
        'post': post,
        'post_count': post_count,
        'group': group,
        'form': form,
        'comments': comments,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if request.method == "POST":
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('posts:profile', request.user)

    return render(request, 'posts/create_post.html', {'form': form})


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = PostForm(request.POST or None,
                    files=request.FILES or None,
                    instance=post)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id)
    if request.method == "POST":
        if form.is_valid():
            post = form.save()
            form.save()
            return redirect('posts:post_detail', post_id)
    return render(request, 'posts/create_post.html', {'form': form})


def paginator(request, posts):
    paginator = Paginator(posts, MAX_POSTS)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    follow = Follow.objects.filter(user=request.user)
    following_author = User.objects.filter(following__in=follow)
    posts = Post.objects.filter(author__in=following_author)
    post_count = posts.count()
    page_obj = paginator(request, posts)
    context = {
        'page_obj': page_obj,
        'post_count': post_count,
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    count_followers = Follow.objects.filter(author=author).count()
    if request.user != author and count_followers != 1:
        Follow.objects.create(
            user=request.user,
            author=author,
        )
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(
        user=request.user,
        author=author,
    ).delete()
    return redirect('posts:profile', username=username)
