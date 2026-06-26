// pages/points/pointscheckin/pointscheckin.js
const app = getApp();
const api = require('../../../config/settings');

Page({
  data: {
    // 签到状态
    signStatus: {
      today_checked: false,
      can_sign: true,
      points_earned: 0,
      continuous_days: 0,
      continuous_days: 0,
      today_points: 1,
      extra_points: 0,
      next_reward: 1,
      message: '',
      checked_time: null
    },
    calendar: [],
    rules: [{
        day: 1,
        points: 1,
        bonus: false
      },
      {
        day: 2,
        points: 1,
        bonus: false
      },
      {
        day: 3,
        points: 2,
        bonus: false
      },
      {
        day: 4,
        points: 2,
        bonus: false
      },
      {
        day: 5,
        points: 2,
        bonus: false
      },
      {
        day: 6,
        points: 3,
        bonus: false
      },
      {
        day: 7,
        points: 3,
        bonus: true
      }
    ],

    totalPoints: 0,
    todayEarnedPoints: 0,

    // 状态控制
    loading: false,
    signing: false,
    showPointsPopup: false,
    earnedPoints: 0,

    animationData: {}
  },

  onLoad() {
    this.initPage();
  },

  onShow() {
    this.loadSignStatus();
  },

  onPullDownRefresh() {
    this.initPage().then(() => {
      wx.stopPullDownRefresh();
    });
  },

  async initPage() {
    this.setData({
      loading: true
    });
    await Promise.all([
      this.loadSignStatus(),
      this.loadCalendar(),
      this.loadTotalPoints()
    ]);
    this.initAnimation();
    this.setData({
      loading: false
    });
  },

  initAnimation() {
    const animation = wx.createAnimation({
      duration: 1200,
      timingFunction: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)'
    });

    animation.opacity(1).translateY(0).step();
    this.setData({
      animationData: animation.export()
    });
  },

  async loadSignStatus() {
    try {
      const app = getApp();
      const today = new Date().toISOString().split('T')[0];
      const user = app.globalData.userInfo;

      const idempotencyToken = `sign_${user.id}_${today}`;
      const localSign = wx.getStorageSync(idempotencyToken);

      if (localSign && localSign.signed) {
        this.setData({
          signStatus: {
            ...this.data.signStatus,
            today_checked: true,
            can_sign: false,
            points_earned: localSign.points || 0,
            message: '今日已签到'
          },
          todayEarnedPoints: localSign.points || 0
        });
        return;
      }

      const response = await new Promise((resolve, reject) => {
        wx.request({
          url: api.pointsSign,
          method: 'GET',
          header: {
            'Authorization': app.globalData.token ? `Bearer ${app.globalData.token}` : '',
            'Content-Type': 'application/json'
          },
          success: resolve,
          fail: reject
        });
      });

      if (response.statusCode === 200 && response.data.code === 200) {
        const statusData = response.data.data;

        if (statusData.today_checked) {
          wx.setStorageSync(idempotencyToken, {
            signed: true,
            timestamp: new Date().getTime(),
            points: statusData.points_earned || 0
          });
        }

        // 计算今日获得积分
        let todayEarned = 0;
        if (statusData.today_checked) {
          todayEarned = statusData.points_earned || 0;
        } else {
          const basePoints = statusData.today_points || 10;
          const extraPoints = statusData.extra_points || 0;
          todayEarned = basePoints + extraPoints;
        }

        this.setData({
          signStatus: {
            ...this.data.signStatus,
            ...statusData,
            continuous_days: statusData.continuous_days || 0
          },
          todayEarnedPoints: todayEarned
        });
      }
    } catch (error) {
      console.error('加载状态失败:', error);
    }
  },

  async loadTotalPoints() {
    try {
      const app = getApp();
      const response = await new Promise((resolve, reject) => {
        wx.request({
          url: api.pointsSummary,
          method: 'GET',
          header: {
            'Authorization': app.globalData.token ? `Bearer ${app.globalData.token}` : '',
            'Content-Type': 'application/json'
          },
          success: resolve,
          fail: reject
        });
      });

      if (response.statusCode === 200 && response.data.code === 200) {
        const summaryData = response.data.data;

        this.setData({
          totalPoints: summaryData.total_points || 0,
          // 从积分汇总接口获取连续签到天数
          'signStatus.continuous_days': summaryData.continuous_days || 0
        });
      }
    } catch (error) {
      console.error('获取总积分失败:', error);
    }
  },

  async loadCalendar() {
    try {
      const today = new Date();
      const year = today.getFullYear();
      const month = today.getMonth();

      const firstDay = new Date(year, month, 1);
      const lastDay = new Date(year, month + 1, 0);
      const daysInMonth = lastDay.getDate();
      const firstDayOfWeek = firstDay.getDay();

      const calendar = [];

      for (let i = 0; i < firstDayOfWeek; i++) {
        calendar.push({
          day: null,
          checked: false
        });
      }

      // 填充日期
      for (let i = 1; i <= daysInMonth; i++) {
        calendar.push({
          day: i,
          checked: false,
          today: i === today.getDate()
        });
      }

      this.setData({
        calendar
      });

      // 标记已签到的日期
      await this.markCheckedDates();

    } catch (error) {
      console.error('加载日历失败:', error);
    }
  },

  async markCheckedDates() {
    try {
      const app = getApp();
      const today = new Date();
      const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);

      // 获取本月所有签到记录
      const response = await new Promise((resolve, reject) => {
        wx.request({
          url: api.pointsRecords,
          method: 'GET',
          data: {
            points_type: 'sign',
            date_from: firstDay.toISOString().split('T')[0],
            date_to: today.toISOString().split('T')[0]
          },
          header: {
            'Authorization': app.globalData.token ? `Bearer ${app.globalData.token}` : '',
            'Content-Type': 'application/json'
          },
          success: resolve,
          fail: reject
        });
      });

      if (response.statusCode === 200 && response.data.code === 200) {
        const records = response.data.data?.results || response.data.data?.data || [];

        // 提取签到日期
        const signedDates = new Set();
        records.forEach(record => {
          const date = new Date(record.created_at);
          if (date.getMonth() === today.getMonth()) {
            signedDates.add(date.getDate());
          }
        });

        // 更新日历
        const calendar = this.data.calendar.map(item => {
          if (item.day && signedDates.has(item.day)) {
            return {
              ...item,
              checked: true
            };
          }
          return item;
        });

        this.setData({
          calendar
        });
      }
    } catch (error) {
      console.error('标记签到日期失败:', error);
    }
  },

  updateTodayInCalendar() {
    const today = new Date().getDate();
    const calendar = this.data.calendar.map(item => {
      if (item.day === today) {
        return {
          ...item,
          checked: true
        };
      }
      return item;
    });

    this.setData({
      calendar
    });
  },

  async checkIn() {
    const today = new Date().toISOString().split('T')[0];

    if (this.data.signStatus.today_checked) {
      wx.showToast({
        title: '今天已经签到过了',
        icon: 'none',
        duration: 2000
      });
      return;
    }

    // 2. 添加防重提交
    if (this.data.signing) {
      wx.showToast({
        title: '签到进行中...',
        icon: 'none'
      });
      return;
    }

    // 3. 生成幂等性令牌
    const user = getApp().globalData.userInfo;
    const idempotencyToken = `sign_${user.id}_${today}`;
    const storedToken = wx.getStorageSync(idempotencyToken);

    if (storedToken) {
      wx.showToast({
        title: '今天已经签到过了（本地记录）',
        icon: 'none',
        duration: 2000
      });
      return;
    }

    this.setData({
      signing: true
    });

    try {
      const app = getApp();
      const response = await new Promise((resolve, reject) => {
        wx.request({
          url: api.pointsSign,
          method: 'POST',
          header: {
            'Authorization': app.globalData.token ? `Bearer ${app.globalData.token}` : '',
            'Content-Type': 'application/json'
          },
          success: resolve,
          fail: reject
        });
      });

      if (response.statusCode === 200) {
        const data = response.data;

        if (data.code === 200) {
          // 成功：存储幂等性令牌（24小时过期）
          wx.setStorageSync(idempotencyToken, {
            signed: true,
            timestamp: new Date().getTime(),
            points: data.data.points || 10
          });

          // 更新状态
          this.setData({
            signStatus: {
              ...this.data.signStatus,
              today_checked: true,
              can_sign: false,
              points_earned: data.data.points || 10,
              message: '今日已签到',
              checked_time: new Date().toISOString()
            }
          });

          // 显示成功提示
          wx.showToast({
            title: '签到成功',
            icon: 'success',
            duration: 2000
          });

          // 更新日历
          this.updateTodayInCalendar();

        } else if (data.code === 400 && data.data?.already_signed) {
          // 服务器说已签到，更新本地状态
          wx.setStorageSync(idempotencyToken, {
            signed: true,
            timestamp: new Date().getTime(),
            points: data.data.points || 0
          });

          this.setData({
            signStatus: {
              ...this.data.signStatus,
              today_checked: true,
              can_sign: false,
              message: '今日已签到'
            }
          });

          wx.showToast({
            title: data.message || '今天已经签到过了',
            icon: 'none'
          });
        }
      } else if (response.statusCode === 400) {
        // 处理重复提交
        this.handleDuplicateSign();
      }
    } catch (error) {
      console.error('签到失败:', error);
      wx.showToast({
        title: '网络错误，请稍后重试',
        icon: 'none'
      });
    } finally {
      this.setData({
        signing: false
      });
    }
  },

  handleDuplicateSign() {
    const today = new Date().toISOString().split('T')[0];
    const user = getApp().globalData.userInfo;
    const idempotencyToken = `sign_${user.id}_${today}`;

    wx.setStorageSync(idempotencyToken, {
      signed: true,
      timestamp: new Date().getTime()
    });

    this.setData({
      signStatus: {
        ...this.data.signStatus,
        today_checked: true,
        can_sign: false,
        message: '今日已签到'
      }
    });

    wx.showToast({
      title: '今天已经签到过了',
      icon: 'none'
    });
  },

  closePointsPopup() {
    this.setData({
      showPointsPopup: false
    });
  },

  viewRules() {
    wx.navigateTo({
      url: '/pages/points/pointsrules/pointsrules'
    });
  },

  viewRecords() {
    wx.navigateTo({
      url: '/pages/points/pointsrecord/pointsrecord'
    });
  },

  formatTime(timeStr) {
    if (!timeStr) return '';

    try {
      const date = new Date(timeStr);
      return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
    } catch (e) {
      return timeStr;
    }
  }
});