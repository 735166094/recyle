// pages/points/pointsrules/pointsrules.js
const settings = require('../../../config/settings.js');

Page({
  data: {
    rules: {
      earnRules: [],
      useRules: [],
      expireRules: []
    },
    expandedSections: {
      earn: true,
      use: false,
      expire: false
    },
    loading: false,
    loadingFailed: false,
    animationData: {}
  },

  onLoad() {
    this.loadRulesData();
    this.initAnimation();
  },

  // 页面显示时重新加载
  onShow() {
    if (!this.data.rules ||
      !this.data.rules.earnRules ||
      this.data.rules.earnRules.length === 0) {
      this.loadRulesData();
    }
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

  async loadRulesData() {
    this.setData({
      loading: true
    });

    try {
      const app = getApp();

      // 检查登录状态
      if (!app.globalData.token) {
        wx.showToast({
          title: '请先登录',
          icon: 'none'
        });
        // 跳转到登录页面
        setTimeout(() => {
          wx.navigateTo({
            url: '/pages/user/login/login'
          });
        }, 1500);
        return;
      }

      // 使用Promise包装wx.request
      const response = await new Promise((resolve, reject) => {
        wx.request({
          url: settings.pointsRules,
          method: 'GET',
          header: {
            'Authorization': app.globalData.token ? `Bearer ${app.globalData.token}` : '',
            'Content-Type': 'application/json'
          },
          success: resolve,
          fail: reject
        });
      });

      console.log('API响应数据:', response); // 调试日志

      if (response.statusCode === 200) {
        const data = response.data;

        if (data.code === 200 && data.data) {
          console.log('规则数据:', data.data); // 调试日志
          this.processRulesData(data.data);
        } else {
          // 处理后端返回的错误
          wx.showToast({
            title: data.message || '获取数据失败',
            icon: 'none'
          });
          // 设置默认规则
          this.setDefaultRules();
        }
      } else if (response.statusCode === 401) {
        // 未授权，需要重新登录
        wx.showToast({
          title: '登录已过期，请重新登录',
          icon: 'none'
        });
        wx.navigateTo({
          url: '/pages/user/login/login'
        });
      } else {
        throw new Error(`请求失败，状态码：${response.statusCode}`);
      }

    } catch (error) {
      console.error('加载规则数据失败:', error);
      wx.showToast({
        title: '网络错误，请重试',
        icon: 'none'
      });
      // 设置默认规则作为后备
      this.setDefaultRules();
    } finally {
      this.setData({
        loading: false
      });
    }
  },

  setDefaultRules() {
    console.log('使用默认规则数据');

    const defaultEarnRules = this.getDefaultEarnRules();
    const defaultUseRules = this.getDefaultUseRules();
    const defaultExpireRules = [{
        id: 1,
        title: '积分有效期',
        desc: '积分自获得之日起有效期为12个月',
        important: true,
        icon: 'clock'
      },
      {
        id: 2,
        title: '过期规则',
        desc: '过期积分将自动清零，不可恢复',
        important: true,
        icon: 'warning'
      }
    ];

    this.setData({
      rules: {
        earnRules: defaultEarnRules,
        useRules: defaultUseRules,
        expireRules: defaultExpireRules
      }
    });
  },

  // 处理规则数据
  processRulesData(rulesData) {
    if (!rulesData || !Array.isArray(rulesData)) {
      console.warn('规则数据格式错误:', rulesData);
      this.setDefaultRules();
      return;
    }

    const earnRules = [];
    const useRules = [];
    const expireRules = [];

    rulesData.forEach(rule => {
      if (!rule || typeof rule !== 'object') return;

      const ruleItem = {
        id: rule.id || rule.rule_id,
        type: rule.rule_name || '未命名规则',
        points: rule.points_value !== undefined ? rule.points_value : '不定',
        frequency: this.getFrequencyText(rule),
        desc: rule.description || '暂无描述',
        icon: this.getRuleIcon(rule.rule_type, rule.green_type),
        status: rule.is_active ? 'active' : 'inactive',
        rawData: rule // 保存原始数据
      };

      // 分类规则
      switch (rule.rule_type) {
        case 'sign':
        case 'task':
        case 'purchase':
        case 'recycle':
        case 'system_bonus':
          earnRules.push(ruleItem);
          break;
        case 'consume':
          useRules.push({
            ...ruleItem,
            title: rule.rule_name || '消费规则',
            condition: `消耗积分: ${rule.points_value || 0}`,
            icon: 'exchange'
          });
          break;
        default:
          // 其他类型归入获得积分
          if (rule.points_value > 0) {
            earnRules.push(ruleItem);
          }
      }
    });

    // 添加默认的过期规则
    expireRules.push({
      id: 1,
      title: '积分有效期',
      desc: '积分自获得之日起有效期为12个月',
      important: true,
      icon: 'clock'
    }, {
      id: 2,
      title: '过期规则',
      desc: '过期积分将自动清零，不可恢复',
      important: true,
      icon: 'warning'
    });

    this.setData({
      rules: {
        earnRules: earnRules.length > 0 ? earnRules : this.getDefaultEarnRules(),
        useRules: useRules.length > 0 ? useRules : this.getDefaultUseRules(),
        expireRules
      }
    });

    console.log('处理后的规则数据:', this.data.rules); // 调试日志
  },

  processRulesData(rulesData) {
    const earnRules = [];
    const useRules = [];
    const expireRules = [];

    rulesData.forEach(rule => {
      const ruleItem = {
        id: rule.id,
        type: rule.rule_name,
        points: rule.points_value || '不定',
        frequency: this.getFrequencyText(rule),
        desc: rule.description,
        icon: this.getRuleIcon(rule.rule_type, rule.green_type),
        status: rule.is_active ? 'active' : 'inactive'
      };

      switch (rule.rule_type) {
        case 'sign':
        case 'task':
        case 'purchase':
        case 'recycle':
        case 'system_bonus':
          earnRules.push(ruleItem);
          break;
        case 'consume':
          useRules.push({
            ...ruleItem,
            title: rule.rule_name,
            condition: `消耗积分: ${rule.points_value || 0}`,
            icon: 'exchange'
          });
          break;
      }
    });

    // 添加过期规则
    expireRules.push({
      id: 1,
      title: '积分有效期',
      desc: '积分自获得之日起有效期为12个月',
      important: true,
      icon: 'clock'
    }, {
      id: 2,
      title: '过期规则',
      desc: '过期积分将自动清零，不可恢复',
      important: true,
      icon: 'warning'
    });

    this.setData({
      rules: {
        earnRules,
        useRules,
        expireRules
      }
    });
  },

  // 获取频率文本
  getFrequencyText(rule) {
    if (!rule) return '不限次数';

    if (rule.daily_limit > 0) {
      return `每天${rule.daily_limit}次`;
    } else if (rule.monthly_limit > 0) {
      return `每月${rule.monthly_limit}次`;
    } else if (rule.points_limit > 0) {
      return `上限${rule.points_limit}分`;
    }
    return '不限次数';
  },

  // 获取规则图标
  getRuleIcon(ruleType, greenType) {
    const iconMap = {
      'sign': 'calendar',
      'task': 'leaf',
      'purchase': 'shopping',
      'recycle': 'recycle',
      'consume': 'exchange',
      'system_bonus': 'gift',
      'transport': 'transport',
      'food': 'food',
      'walk': 'walk',
      'learning': 'learning'
    };

    return greenType ? greenType : (iconMap[ruleType] || 'other');
  },

  // 切换section展开状态
  toggleSection(e) {
    const section = e.currentTarget.dataset.section;
    this.setData({
      [`expandedSections.${section}`]: !this.data.expandedSections[section]
    });
  },

  navigateToCheckin() {
    wx.navigateTo({
      url: '/pages/points/pointscheckin/pointscheckin'
    });
  },

  navigateToTasks() {
    wx.switchTab({
      url: '/pages/points/index/index'
    });
  },

  contactCustomerService() {
    wx.makePhoneCall({
      phoneNumber: '18356998052'
    });
  },

  onShareAppMessage() {
    return {
      title: '积分规则',
      path: '/pages/points/pointsrules/pointsrules'
    };
  },

  // 添加下拉刷新
  onPullDownRefresh() {
    console.log('下拉刷新规则数据');
    this.loadRulesData().then(() => {
      wx.stopPullDownRefresh();
    }).catch(() => {
      wx.stopPullDownRefresh();
    });
  },
});