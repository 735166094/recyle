// pages/points/index/index.js 
const settings = require('../../../config/settings.js');

Page({
  data: {
    userPoints: {
      total_points: 0,
      today_earned: 0,
      today_consumed: 0,
      month_earned: 0,
      month_consumed: 0,
    },
    pointsCards: [{
      id: '',
      title: '',
      value: '',
      unit: '',
      trend: '',
      trendType: ''
    }],
    quickActions: [{
        id: 'checkin',
        name: '每日签到',
        icon: 'calendar',
        points: 1,
        status: 'pending',
        path: '/pages/points/pointscheckin/pointscheckin',
        desc: '连续签到奖励更多'
      },
      {
        id: 'transport',
        name: '绿色出行',
        icon: 'leaf',
        points: 1,
        status: 'pending',
        path: '/pages/points/greenlife/greenlife?type=transport',
        desc: '记录绿色出行'
      },
      {
        id: 'food',
        name: '光盘行动',
        icon: 'food',
        points: 1,
        status: 'pending',
        path: '/pages/points/greenlife/greenlife?type=food',
        desc: '用餐光盘行动'
      },
      {
        id: 'walk',
        name: '低碳行走',
        icon: 'walk',
        points: 10,
        status: 'pending',
        path: '/pages/points/greenlife/greenlife?type=walk',
        desc: '记录每日步数'
      }
    ],
    recentTransactions: [],
    loading: true,
    refreshing: false,
    animationData: {},
    greenStats: {
      transport_days: 0,
      food_days: 0,
      walk_steps: 0,
      learning_count: 0
    }
  },

  onLoad() {
    this.checkLogin();
  },

  onShow() {
    this.loadData();
  },

  onPullDownRefresh() {
    this.setData({
      refreshing: true
    });
    this.loadData().finally(() => {
      wx.stopPullDownRefresh();
      this.setData({
        refreshing: false
      });
    });
  },

  checkLogin() {
    const app = getApp();
    if (!app.globalData.isLoggedIn) {
      wx.showModal({
        title: '提示',
        content: '请先登录',
        success: (res) => {
          if (res.confirm) {
            wx.navigateTo({
              url: '/pages/user/login/login'
            });
          } else {
            wx.navigateBack();
          }
        }
      });
      return false;
    }
    return true;
  },

  async loadData() {
    if (!this.checkLogin()) return;

    try {
      this.setData({
        loading: true
      });
      const app = getApp();

      const getApiUrl = (endpoint) => {
        if (endpoint.startsWith('http')) {
          return endpoint;
        }

        const baseUrl = settings.baseUrl.replace(/\/$/, '');
        const cleanEndpoint = endpoint.startsWith('/') ? endpoint : '/' + endpoint;
        return baseUrl + cleanEndpoint;
      };

      const summaryRes = await new Promise((resolve, reject) => {
        wx.request({
          url: getApiUrl(settings.pointsSummary),
          method: 'GET',
          header: {
            'Authorization': app.globalData.token ? `Bearer ${app.globalData.token}` : '',
            'Content-Type': 'application/json'
          },
          success: (res) => {
            resolve(res);
          },
          fail: (err) => {
            console.error('积分汇总请求失败:', err);
            reject(err);
          }
        });
      });

      if (!summaryRes || !summaryRes.data) {
        console.error('积分汇总返回数据为空');
        wx.showToast({
          title: '获取积分数据失败',
          icon: 'none'
        });
        return;
      }

      if (summaryRes.data.code === 200 && summaryRes.data.data) {
        this.processSummaryData(summaryRes.data.data);
      } else {
        if (summaryRes.data.total_points !== undefined) {
          this.processSummaryData(summaryRes.data);
        } else {
          wx.showToast({
            title: '数据格式错误',
            icon: 'none'
          });
        }
      }
      // 2. 获取今日任务状态
      try {
        const today = new Date().toISOString().split('T')[0];
        const tasksRes = await new Promise((resolve, reject) => {
          wx.request({
            url: getApiUrl(settings.pointsRecords),
            method: 'GET',
            data: {
              date_from: today,
              date_to: today
            },
            header: {
              'Authorization': app.globalData.token ? `Bearer ${app.globalData.token}` : '',
              'Content-Type': 'application/json'
            },
            success: resolve,
            fail: reject
          });
        });

        if (tasksRes.statusCode === 200) {
          let taskData = [];

          console.log('今日任务状态原始数据:', tasksRes.data);

          // 解析新的数据结构
          if (tasksRes.data && tasksRes.data.results) {
            const results = tasksRes.data.results;

            if (results.code === 200) {
              // 从 results.data 中获取记录
              if (results.data && Array.isArray(results.data)) {
                taskData = results.data;
              }
            }
          }

          console.log('解析后的今日任务数据:', taskData);
          this.processTaskStatus(taskData);
        }
      } catch (error) {
        console.error('获取任务状态失败:', error);
      }

      // 3. 获取最近记录
      try {
        const recordsRes = await new Promise((resolve, reject) => {
          wx.request({
            url: getApiUrl(settings.pointsRecords),
            method: 'GET',
            data: {
              page_size: 5
            },
            header: {
              'Authorization': app.globalData.token ? `Bearer ${app.globalData.token}` : '',
              'Content-Type': 'application/json'
            },
            success: resolve,
            fail: reject
          });
        });

        if (recordsRes.statusCode === 200) {
          let recordData = [];

          // 新的数据结构解析
          console.log('最近记录原始数据:', recordsRes.data);

          if (recordsRes.data && recordsRes.data.results) {
            const results = recordsRes.data.results;

            if (results.code === 200) {
              // 从 results.data 中获取记录
              if (results.data && Array.isArray(results.data)) {
                recordData = results.data;
              }
            } else {
              // 如果 results 不是预期的结构，尝试直接获取
              if (Array.isArray(results)) {
                recordData = results;
              }
            }
          }

          console.log('解析后的记录数据:', recordData);
          this.processRecentRecords(recordData);
        }
      } catch (error) {
        console.error('获取最近记录失败:', error);
      }

      // 4. 获取绿色生活统计
      try {
        const greenRes = await new Promise((resolve, reject) => {
          wx.request({
            url: getApiUrl(settings.greenLifeStats),
            method: 'GET',
            header: {
              'Authorization': app.globalData.token ? `Bearer ${app.globalData.token}` : '',
              'Content-Type': 'application/json'
            },
            success: resolve,
            fail: reject
          });
        });

        if (greenRes.statusCode === 200 && greenRes.data.code === 200 && greenRes.data.data) {
          this.setData({
            greenStats: greenRes.data.data
          });
        }
      } catch (error) {
        console.error('获取绿色生活统计失败:', error);
      }

      this.setData({
        loading: false
      });

    } catch (error) {
      console.error('加载数据失败:', error);
      wx.showToast({
        title: '加载失败，请检查网络',
        icon: 'none'
      });
      this.setData({
        loading: false
      });
    }
  },

  processSummaryData(summaryData) {

    const safeData = summaryData || {};
    const totalPoints = safeData.total_points !== undefined ? safeData.total_points : 0;
    const todayEarned = safeData.today_earned !== undefined ? safeData.today_earned : 0;

    const calculateTrend = (value) => {
      if (value > 0) {
        return `+${Math.min(20, Math.floor(value / 10) + 1)}%`;
      }
      return '+0%';
    };

    const pointsCards = [{
        id: 'total_points',
        title: '总积分',
        value: totalPoints,
        unit: '分',
        trend: calculateTrend(totalPoints),
        trendType: totalPoints > 0 ? 'up' : 'neutral'
      },
      {
        id: 'today_earned',
        title: '今日获得',
        value: todayEarned,
        unit: '分',
        trend: calculateTrend(todayEarned),
        trendType: todayEarned > 0 ? 'up' : 'neutral'
      }
    ];

    this.setData({
      userPoints: {
        total_points: totalPoints,
        today_earned: todayEarned,
        today_consumed: safeData.today_consumed || 0,
        month_earned: safeData.month_earned || 0,
        month_consumed: safeData.month_consumed || 0,
      },
      pointsCards: pointsCards
    });
  },


  processTaskStatus(records) {
    console.log('处理任务状态记录:', records);

    const taskStatus = {};

    // 检查签到
    const signRecord = records.find(r => r.points_type === 'sign');
    taskStatus.checkin = signRecord ? 'completed' : 'pending';

    // 检查绿色生活
    records.forEach(record => {
      if (record.green_type) {
        taskStatus[record.green_type] = 'completed';
      }
    });

    const updatedActions = this.data.quickActions.map(action => {
      const status = taskStatus[action.id] || 'pending';
      return {
        ...action,
        status: status,
        points: status === 'completed' ? 0 : action.points
      };
    });

    this.setData({
      quickActions: updatedActions
    });
  },

  processRecentRecords(records) {
    console.log('处理最近记录:', records);

    const recentTransactions = records.slice(0, 5).map(record => {
      let title = '';
      let icon = 'other';

      // 根据新数据结构解析，只使用已定义的图标类型
      if (record.points_type === 'sign') {
        title = '每日签到';
        icon = 'calendar';
      } else if (record.green_type === 'transport') {
        title = '绿色出行';
        icon = 'leaf';
      } else if (record.green_type === 'food') {
        title = '光盘行动';
        icon = 'food';
      } else if (record.green_type === 'walk') {
        title = '低碳行走';
        icon = 'walk';
      } else if (record.green_type === 'learning') {
        title = '低碳学习';
        icon = 'leaf'; // 使用已有的leaf图标
      } else if (record.points_type === 'consume') {
        title = '积分兑换';
        icon = 'gift';
      } else if (record.points_type === 'system_bonus') {
        title = '系统奖励';
        icon = 'gift'; // 使用gift图标代替
      } else if (record.points_type === 'task') {
        title = '任务奖励';
        icon = 'leaf'; // 使用leaf图标代替
      } else if (record.points_type === 'purchase') {
        title = '购物奖励';
        icon = 'gift'; // 使用gift图标代替
      } else if (record.points_type === 'recycle') {
        title = '回收奖励';
        icon = 'leaf'; // 使用leaf图标代替
      } else {
        title = record.points_type_display || record.description || '积分变动';
        icon = 'other';
      }

      return {
        id: record.id,
        type: record.points_change > 0 ? 'earn' : 'spend',
        title: title,
        amount: record.points_change,
        time: this.formatTime(record.created_at),
        icon: icon,
        status: 'success',
        // 保存原始数据用于调试
        rawData: record
      };
    });

    console.log('处理后的交易记录:', recentTransactions);

    this.setData({
      recentTransactions: recentTransactions
    });
  },

  formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前';
    if (date.toDateString() === now.toDateString()) {
      return date.getHours().toString().padStart(2, '0') + ':' +
        date.getMinutes().toString().padStart(2, '0');
    }

    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    if (date.toDateString() === yesterday.toDateString()) return '昨天';

    if (date.getFullYear() === now.getFullYear()) {
      return `${date.getMonth() + 1}-${date.getDate()}`;
    }

    return `${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}`;
  },

  onActionTap(e) {
    const {
      path,
      status
    } = e.currentTarget.dataset;

    if (status === 'completed') {
      wx.showToast({
        title: '今日已完成',
        icon: 'none',
        duration: 1500
      });
      return;
    }

    wx.navigateTo({
      url: path
    });
  },

  viewAllRecords() {
    wx.navigateTo({
      url: '/pages/points/pointsrecord/pointsrecord'
    });
  },

  viewRules() {
    wx.navigateTo({
      url: '/pages/points/pointsrules/pointsrules'
    });
  },

  exchangePoints() {
    wx.switchTab({
      url: '/pages/mall/index/index',
      fail: () => {
        wx.showToast({
          title: '请稍后再试',
          icon: 'none'
        });
      }
    });
  },

});