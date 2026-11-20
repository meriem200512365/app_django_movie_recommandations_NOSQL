from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

app_name = 'movies'

urlpatterns = [
    path('', views.home, name='home'),
    path('movies/', views.movie_list, name='list'),
    path('login/', views.custom_login, name='login'),
    path('logout/', LogoutView.as_view(next_page='movies:list'), name='logout'),
    path('accounts/register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    # avoid conflicting with Django admin's `admin/` prefix
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('recommendations/', views.recommendations, name='recommendations'),
    path('recommendations/smart/', views.recommendations_dashboard, name='recommendations_dashboard'),
    path('recommendations/content/', views.content_recommendations, name='recommendations_content'),
    path('recommendations/collaborative/', views.collaborative_recommendations, name='recommendations_collaborative'),
    path('recommendations/graph/', views.graph_recommendations, name='recommendations_graph'),
    # Synchronization is handled automatically in the backend (signals). No frontend routes.
    path('movie/<int:pk>/', views.movie_detail, name='detail'),
    path('movie/create/', views.movie_create, name='create'),
    path('movie/<int:pk>/edit/', views.movie_update, name='update'),
    path('movie/<int:pk>/delete/', views.movie_delete, name='delete'),
    path('movie/<int:pk>/watchlist/add/', views.add_to_watchlist, name='watchlist_add'),
    path('movie/<int:pk>/watchlist/remove/', views.remove_from_watchlist, name='watchlist_remove'),
    path('watchlist/', views.watchlist_view, name='watchlist'),
    path('movie/<int:pk>/review/add/', views.add_review, name='add_review'),
    path('movie/<int:pk>/rate/', views.add_rating, name='add_rating'),
]
