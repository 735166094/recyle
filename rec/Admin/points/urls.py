# points/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # 积分规则
    path('rules/', views.PointsRulesView.as_view(), name='points_rules'),

    # 积分汇总
    path('summary/', views.PointsSummaryView.as_view(), name='points_summary'),

    # 签到
    path('sign/', views.DailySignView.as_view(), name='daily_sign'),

    # 绿色生活
    path('green_life/', views.GreenLifeView.as_view(), name='green_life'),
    path('green_life/stats/', views.GreenLifeStatsView.as_view(), name='green_life_stats'),

    # 积分记录
    path('records/', views.PointsRecordsView.as_view(), name='points_records'),

    # 积分兑换
    path('exchange/', views.ExchangePointsView.as_view(), name='exchange_points'),

    # 月度汇总
    path('monthly_summary/', views.MonthlySummaryView.as_view(), name='monthly_summary'),

    # 用户积分状态
    path('status/', views.UserPointsStatusView.as_view(), name='user_points_status'),

    # 积分排行榜
    path('ranking/', views.PointsRankingView.as_view(), name='points_ranking'),

    # 管理员接口
    path('admin/batch_award/', views.batch_award_points, name='batch_award_points'),
]
