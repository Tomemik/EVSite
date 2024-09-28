from django.urls import path

from . import views

urlpatterns = [
    path("teams/", views.AllTeamsView.as_view(), name='teams'),
    path("teams/<str:name>/", views.TeamDetailView.as_view(), name='team'),
    path("tanks/", views.AllTanksView.as_view(), name='tanks'),
    path("tanks/<str:name>/", views.TankDetailView.as_view(), name='tank'),
    path("manufacturers/", views.ManufacturerListView.as_view(), name='manufacturers'),
    path("manufacturers/<int:pk>/", views.ManufacturerDetailView.as_view(), name='manufacturer'),
    path("boxes/", views.TankBoxView.as_view(), name='box'),
    path('matches/', views.AllMatchesViewSlim.as_view(), name='matches'),
    path('matches/detailed/', views.AllMatchesView.as_view(), name='matches-detailed'),
    path('matches/archived/', views.AllMatchesView.as_view(), name='matches-archived'),
    path('matches/<int:pk>/', views.MatchView.as_view(), name='match-details'),
    path('matches/<int:pk>/results/', views.MatchResultsView.as_view(), name='match-results'),
    path('matches/<int:pk>/calc/', views.CalcTestView.as_view(), name='match-calc'),
    path("transactions/buy_tanks/", views.PurchaseTankView.as_view(), name='buy-tanks'),
    path("transactions/sell_tanks/", views.SellTankView.as_view(), name='sell-tanks'),
    path("transactions/view_upgrades/", views.AllUpgradesView.as_view(), name='upgrade-test'),
    path("transactions/upgrade_tank/", views.UpgradeTankView.as_view(), name='upgrade-tank'),
]