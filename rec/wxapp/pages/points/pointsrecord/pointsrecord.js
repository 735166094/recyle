// pages/points/pointsrecord/pointsrecord.js 
import api from '../../../config/settings'
Page({
  data: {
    records: [],
    loading: true,
    hasMore: true,
    page: 1,
    pageSize: 20,
    error: false,

    filterType: 'all',
    filterOptions: [{
        value: 'all',
        label: '全部'
      },
      {
        value: 'earn',
        label: '获得'
      },
      {
        value: 'spend',
        label: '消费'
      }
    ],

    // 统计信息
    stats: {
      totalEarn: 0,
      totalSpend: 0,
      balance: 0
    },

    animationData: {}
  },

  onLoad() {
    this.loadRecords();
    this.initAnimation();
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

  async loadRecords() {
    if (this.data.loading && this.data.records.length > 0) return;

    this.setData({
      loading: true,
      error: false
    });

    try {
      const app = getApp();

      const params = {
        page: this.data.page,
        page_size: this.data.pageSize
      };

      if (this.data.filterType !== 'all') {
        if (this.data.filterType === 'earn') {
          params.points_change__gt = 0;
        } else if (this.data.filterType === 'spend') {
          params.points_change__lt = 0;
        }
      }

      const response = await new Promise((resolve, reject) => {
        wx.request({
          url: api.pointsRecords,
          method: 'GET',
          data: params,
          header: {
            'Authorization': app.globalData.token ? `Bearer ${app.globalData.token}` : '',
            'Content-Type': 'application/json'
          },
          success: resolve,
          fail: reject
        });
      });

      if (response.statusCode === 200) {
        const responseData = response.data;

        let records = [];
        let recordsData = {};

        if (Array.isArray(responseData)) {
          records = responseData;
        } else if (responseData.code === 200) {
          recordsData = responseData.data || {};

          if (recordsData.results && Array.isArray(recordsData.results)) {
            records = recordsData.results;
          } else if (Array.isArray(recordsData)) {
            records = recordsData;
          } else if (responseData.results && responseData.results.code === 200) {
            records = responseData.results.data || [];
          }
        } else if (responseData.results) {
          if (responseData.results.code === 200) {
            records = responseData.results.data || [];
          } else {
            records = responseData.results;
          }
        }

        const processedRecords = records.map(record => ({
          id: record.id,
          type: this.getRecordType(record),
          typeName: this.getRecordTypeName(record),
          points: record.points_change > 0 ? `+${record.points_change}` : `${record.points_change}`,
          desc: record.description || this.getRecordDesc(record),
          time: this.formatTime(record.created_at),
          status: 'success',
          rawData: record
        }));

        this.setData({
          records: this.data.page === 1 ? processedRecords : this.data.records.concat(processedRecords),
          hasMore: records.length === this.data.pageSize,
          loading: false,
          page: this.data.page + 1
        });

        this.updateStats(recordsData);

      } else {
        const errorMessage = response.data ?
          (response.data.message || response.data.detail || '请求失败') :
          '请求失败';

        throw new Error(errorMessage);
      }

    } catch (error) {
      console.error('加载记录失败:', error);
      this.setData({
        loading: false,
        error: true
      });

      wx.showToast({
        title: error.message || '加载失败',
        icon: 'none',
        duration: 2000
      });
    }
  },

  getRecordType(record) {
    const typeMap = {
      'sign': 'checkin',
      'task': 'activity',
      'purchase': 'exchange',
      'recycle': 'recycle',
      'consume': 'exchange',
      'system_bonus': 'recycle'
    };
    return typeMap[record.points_type] || 'other';
  },

  getRecordTypeName(record) {
    const nameMap = {
      'sign': '签到',
      'task': '任务',
      'purchase': '购物',
      'recycle': '回收',
      'consume': '兑换',
      'system_bonus': '系统奖励',
      'transport': '绿色出行',
      'food': '光盘行动',
      'walk': '低碳行走',
      'learning': '低碳学习'
    };

    if (record.green_type) {
      return nameMap[record.green_type] || '绿色生活';
    }

    return nameMap[record.points_type] || '积分变动';
  },

  getRecordDesc(record) {
    if (record.description) {
      return record.description;
    }

    const descMap = {
      'sign': '每日签到',
      'task': '任务奖励',
      'purchase': '购物奖励',
      'recycle': '回收奖励',
      'consume': '积分兑换',
      'system_bonus': '系统奖励'
    };

    if (record.green_type) {
      const greenDescMap = {
        'transport': '绿色出行',
        'food': '光盘行动',
        'walk': '低碳行走',
        'learning': '低碳学习'
      };
      return greenDescMap[record.green_type] || '绿色生活';
    }

    return descMap[record.points_type] || '积分变动';
  },

  formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) {
      return '刚刚';
    }

    if (diff < 3600000) {
      return Math.floor(diff / 60000) + '分钟前';
    }

    if (date.toDateString() === now.toDateString()) {
      return date.getHours().toString().padStart(2, '0') + ':' +
        date.getMinutes().toString().padStart(2, '0');
    }

    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    if (date.toDateString() === yesterday.toDateString()) {
      return '昨天 ' + date.getHours().toString().padStart(2, '0') + ':' +
        date.getMinutes().toString().padStart(2, '0');
    }

    if (date.getFullYear() === now.getFullYear()) {
      return `${date.getMonth() + 1}月${date.getDate()}日`;
    }

    return `${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}`;
  },

  updateStats(recordsData) {
    if (recordsData && (recordsData.total_earned !== undefined || recordsData.total_consumed !== undefined)) {
      this.setData({
        stats: {
          totalEarn: recordsData.total_earned || 0,
          totalSpend: Math.abs(recordsData.total_consumed || 0),
          balance: recordsData.balance || 0
        }
      });
      return;
    }

    const stats = {
      totalEarn: 0,
      totalSpend: 0,
      balance: 0
    };

    this.data.records.forEach(record => {
      const points = record.rawData ? record.rawData.points_change :
        (record.points.startsWith('+') ? parseInt(record.points.replace('+', '')) : parseInt(record.points));

      if (points > 0) {
        stats.totalEarn += points;
      } else {
        stats.totalSpend += Math.abs(points);
      }
    });

    stats.balance = stats.totalEarn - stats.totalSpend;

    this.setData({
      stats
    });
  },

  onFilterChange(e) {
    const filterType = e.currentTarget.dataset.type;
    this.setData({
      filterType,
      page: 1,
      hasMore: true,
      records: []
    });
    this.loadRecords();
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.loadRecords();
    }
  },

  onPullDownRefresh() {
    this.setData({
      page: 1,
      hasMore: true,
      records: []
    });

    this.loadRecords().finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  retryLoad() {
    this.loadRecords();
  }
});