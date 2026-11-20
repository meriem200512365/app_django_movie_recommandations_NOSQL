from django.contrib import admin
from .models import Movie, Rating, Review, Watchlist, SyncLog, Genre, Tag
from .models import SyncLog


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'year', 'duration', 'poster_tag')
    search_fields = ('title', 'description')
    list_filter = ('year', 'genres')
    filter_horizontal = ('genres', 'tags')

    def poster_tag(self, obj):
        if obj.poster:
            return f"<img src='{obj.poster.url}' style='height:60px'/>"
        return ''
    poster_tag.allow_tags = True
    poster_tag.short_description = 'Poster'


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'score', 'created_at')
    list_filter = ('score',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'created_at')


@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'added_at')


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ('started_at', 'finished_at', 'status', 'triggered_by', 'duration_seconds')
    list_filter = ('status',)
    readonly_fields = ('started_at', 'finished_at', 'status', 'message', 'triggered_by', 'duration_seconds')
    search_fields = ('message',)


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
